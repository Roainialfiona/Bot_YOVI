import pandas as pd
from datetime import datetime
from services.google_sheets import GoogleSheetsService
from config import SHEET_NAME


class OGPHandlers:
    def __init__(self):
        self.gs = GoogleSheetsService()
        self.WORKSHEET = "REPORT PSB"

        self.bulan_map = {
            "januari": 1,
            "februari": 2,
            "maret": 3,
            "april": 4,
            "mei": 5,
            "juni": 6,
            "juli": 7,
            "agustus": 8,
            "september": 9,
            "oktober": 10,
            "november": 11,
            "desember": 12,
        }

    # =========================
    # LOAD DATAFRAME
    # =========================
    def get_df(self):
        data = self.gs.get_sheet_data_by_name(SHEET_NAME, self.WORKSHEET)
        if not data or len(data) < 3:
            return pd.DataFrame()

        header = data[1]
        rows = data[2:]

        df = pd.DataFrame(rows, columns=header)
        df.columns = df.columns.astype(str).str.strip().str.upper()
        return df

    # =========================
    # SAFE COLUMN (HANDLE HEADER DOBEL)
    # =========================
    def _safe_col(self, df, col_name):
        col = df.loc[:, col_name]
        if isinstance(col, pd.DataFrame):
            return col.iloc[:, 0]
        return col

    def _safe_value(self, df, idx, col_name):
        col = df.loc[:, col_name]
        if isinstance(col, pd.DataFrame):
            return col.iloc[idx, 0]
        return col.iloc[idx]

    # =========================
    # HANDLER /OGP
    # =========================
    async def ogp_handler(self, event):
        """
        /ogp
        /ogp februari
        /ogp februari 2026

        Filter:
        - DATEL = BATU
        - STATUS RESUME ≠ Completed (PS)
        - DATA PS kosong
        - BULAN & TAHUN dari TANGGAL ORDER
        """

        # =========================
        # PARSE ARGUMENT
        # =========================
        args = event.text.split()[1:]
        bulan = None
        tahun = datetime.now().year

        for arg in args:
            a = arg.lower()
            if a in self.bulan_map:
                bulan = self.bulan_map[a]
            elif a.isdigit():
                tahun = int(a)

        df = self.get_df()
        if df.empty:
            await event.reply("❌ Data PSB kosong.")
            return

        # =========================
        # AMBIL KOLOM WAJIB
        # =========================
        try:
            datel_col = self._safe_col(df, "DATEL")

            status_col = (
                self._safe_col(df, "STATUS RESUME")
                if "STATUS RESUME" in df.columns
                else self._safe_col(df, "STATUS_RESUME")
            )

            data_ps_col = self._safe_col(df, "DATA PS")

            cust_col = (
                self._safe_col(df, "CUSTOMER_NAME")
                if "CUSTOMER_NAME" in df.columns
                else self._safe_col(df, "CUSTNAME")
            )

            order_col = self._safe_col(df, "ORDER_ID")
            sto_col = self._safe_col(df, "STO")

            tanggal_order_col = self._safe_col(df, "TGL ORDER")

        except Exception as e:
            await event.reply(
                "❌ Struktur kolom sheet tidak sesuai.\n\n"
                f"Kolom terbaca:\n{', '.join(df.columns)}\n\n"
                f"Error: {e}"
            )
            return

        # =========================
        # NORMALISASI
        # =========================
        datel_norm = datel_col.astype(str).str.strip().str.upper()
        status_norm = (
            status_col
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(r"\s+", " ", regex=True)
        )
        data_ps_norm = data_ps_col.astype(str).str.strip()

        tanggal_order = pd.to_datetime(tanggal_order_col, errors="coerce")

        # =========================
        # FILTER OGP
        # =========================
        mask = (
            (datel_norm == "BATU") &
            (~status_norm.isin(["completed (ps)", "cancel completed"])) &
            (
                data_ps_col.isna() |
                (data_ps_norm == "") |
                (data_ps_norm.str.lower() == "nan")
            )
        )

        hasil = df.loc[mask].copy()
        hasil["TGL ORDER"] = tanggal_order

        # =========================
        # FILTER BULAN & TAHUN
        # =========================
        if bulan:
            hasil = hasil[
                (hasil["TGL ORDER"].dt.month == bulan) &
                (hasil["TGL ORDER"].dt.year == tahun)
            ]

        if hasil.empty:
            await event.reply("❌ Tidak ada data OGP sesuai filter.")
            return

        # =========================
        # OUTPUT TELEGRAM
        # =========================
        judul = "📌 **OGP BATU**"
        if bulan:
            judul += f" — {bulan}/{tahun}"
        judul += f"\n📊 Total: **{len(hasil)} data**\n\n"

        messages = []
        current_msg = judul
        MAX_LEN = 3500

        for idx in hasil.index:
            block = (
                f"🆔 ORDER ID   : '{self._safe_value(df, idx, 'ORDER_ID')}'\n"
                f"👤 NAMA       : {cust_col.loc[idx]}\n"
                f"🏢 STO        : {sto_col.loc[idx]}\n"
                f"👤 SA         : {self._safe_value(df, idx, 'KODE SA')}\n"
                f"👤 NAMA SA    : {self._safe_value(df, idx, 'NAMA SA')}\n"
                f"📄 STATUS     : {status_col.loc[idx]}\n"
                f"🗓️ TGL ORDER  : {hasil.loc[idx, 'TGL ORDER'].date()}\n"
                f"📝 KETERANGAN : {self._safe_value(df, idx, 'NOTE KET')}\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
            )

            if len(current_msg) + len(block) > MAX_LEN:
                messages.append(current_msg)
                current_msg = block
            else:
                current_msg += block

        if current_msg.strip():
            messages.append(current_msg)

        for msg in messages:
            await event.reply(msg, parse_mode="md")
