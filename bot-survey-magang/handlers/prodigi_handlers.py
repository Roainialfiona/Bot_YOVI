import pandas as pd
from services.google_sheets import GoogleSheetsService
from config import SHEET_NAME
from datetime import datetime


class ProdigiHandlers:

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

        self.bulan_nama = {v: k.capitalize() for k, v in self.bulan_map.items()}

        self.ADDON_ORDER = ["OCA", "PIJAR", "OTHERS", "ANTAREZ", "NETMONK", "NO ADDON"]

    # ===============================
    # LOAD DATAFRAME
    # ===============================
    def get_df(self):

        data = self.gs.get_sheet_data_by_name(SHEET_NAME, self.WORKSHEET)

        if not data or len(data) < 3:
            return pd.DataFrame()

        header = data[1]
        rows = data[2:]

        df = pd.DataFrame(rows, columns=header)
        df.columns = df.columns.astype(str).str.strip().str.upper()

        return df

    # ===============================
    # SAFE COLUMN
    # ===============================
    def _safe_col(self, df, col):

        if col not in df.columns:
            return None

        c = df.loc[:, col]

        if isinstance(c, pd.DataFrame):
            return c.iloc[:, 0]

        return c

    # ===============================
    # MAIN HANDLER
    # ===============================
    async def prodigi_handler(self, event):
        """
        /prodigi              → rekap bulan ini
        /prodigi januari      → rekap Januari tahun ini
        /prodigi januari 2024 → rekap Januari 2024
        """

        args = event.text.split()[1:]

        bulan = datetime.now().month
        tahun = datetime.now().year

        for arg in args:
            a = arg.lower().strip()
            if a in self.bulan_map:
                bulan = self.bulan_map[a]
            elif a.isdigit() and len(a) == 4:
                tahun = int(a)

        df = self.get_df()

        if df.empty:
            await event.reply("❌ Data tidak tersedia.")
            return

        # Ambil kolom yang diperlukan
        detail_ket_col = self._safe_col(df, "DETAIL KET")   # Kolom P
        data_ps_col    = self._safe_col(df, "DATA PS")       # Kolom AB
        addon_col      = self._safe_col(df, "PRODIGI")         # Kolom D
        datel_col      = self._safe_col(df,"DATEL")            # Kolom H

        if detail_ket_col is None or data_ps_col is None or addon_col is None:
            await event.reply("❌ Kolom tidak ditemukan. Cek nama kolom di sheet.")
            return

        df["_DETAIL_KET"] = detail_ket_col.astype(str).str.strip().str.upper()
        df["_DATA_PS"]    = pd.to_datetime(data_ps_col, errors="coerce")
        df["_ADDON"]      = addon_col.astype(str).str.strip()
        df['_DATEL']      = datel_col.astype(str).str.strip().str.upper()

        # Normalisasi No Addon
        df["_ADDON"] = df["_ADDON"].replace({"": "No Addon", "nan": "No Addon"})

        # Filter PS atau PS HI + bulan & tahun
        hasil = df[
            (df["_DATEL"] == "BATU") &
            (df["_DETAIL_KET"].isin(["PS", "PS HI"])) &
            (df["_DATA_PS"].dt.month == bulan) &
            (df["_DATA_PS"].dt.year == tahun)
        ]

        grand_total = len(hasil)

        if grand_total == 0:
            await event.reply(
                f"📭 Tidak ada data PS untuk **{self.bulan_nama[bulan]} {tahun}**."
            )
            return

        # Hitung per ADDON
        summary = hasil.groupby("_ADDON").size().to_dict()

        # Susun pesan sesuai urutan
        lines = ""
        for addon in self.ADDON_ORDER:
            count = summary.get(addon, 0)
            lines += f"  • {addon:<12}: {count}\n"

        # Addon di luar daftar (jaga-jaga)
        extras = {k: v for k, v in summary.items() if k not in self.ADDON_ORDER}
        for addon, count in sorted(extras.items()):
            lines += f"  • {addon:<12}: {count}\n"

        msg = (
            f"**REKAP PRODUK DIGITAL**\n"
            f"{self.bulan_nama[bulan]} {tahun}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{lines}"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Total PS : {grand_total}**"
        )

        await event.reply(msg)