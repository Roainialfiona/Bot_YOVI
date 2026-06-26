import pandas as pd
from services.google_sheets import GoogleSheetsService
from config import SHEET_NAME


class PSHandlers:
    def __init__(self):
        self.gs = GoogleSheetsService()
        self.WORKSHEET = "REPORT PSB"

    # =========================
    # LOAD DATA
    # =========================
    def get_df(self):
        data = self.gs.get_sheet_data_by_name(SHEET_NAME, self.WORKSHEET)

        if not data or len(data) < 2:
            return pd.DataFrame()

        header = data[1]
        rows = data[2:]

        df = pd.DataFrame(rows, columns=header)
        df.columns = df.columns.astype(str).str.strip().str.upper()

        return df

    # =========================
    # SAFE COLUMN
    # =========================
    def _safe_col(self, df, col):

        if col not in df.columns:
            return None

        c = df.loc[:, col]

        if isinstance(c, pd.DataFrame):
            return c.iloc[:, 0]

        return c

    # =========================
    # SAFE VALUE
    # =========================
    def _safe_val(self, df, idx, col):

        if col not in df.columns:
            return "-"

        c = df.loc[:, col]

        if isinstance(c, pd.DataFrame):
            return c.iloc[idx, 0]

        return c.iloc[idx]

    # =========================
    # HANDLER /PS
    # =========================
    async def ps_handler(self, event, tanggal):

        df = self.get_df()

        if df.empty:
            await event.reply("❌ Data PSB kosong.")
            return

        datel_col = self._safe_col(df, "DATEL")
        date_col = self._safe_col(df, "DATA PS")

        # =========================
        # DETECT STATUS COLUMN
        # =========================
        if "DETAIL KET" in df.columns:
            status_col = self._safe_col(df, "DETAIL KET")
            status_name = "DETAIL KET"

        elif "DETAIL KET" in df.columns:
            status_col = self._safe_col(df, "DETAIL KET")
            status_name = "DETAIL KET"

        else:
            status_col = self._safe_col(df, "DETAIL KET")
            status_name = "DETAIL KET"

        if datel_col is None or date_col is None or status_col is None:
            await event.reply("❌ Kolom wajib tidak ditemukan di Google Sheet.")
            return

        # =========================
        # NORMALISASI DATA
        # =========================
        datel = datel_col.astype(str).str.upper().str.strip()
        status = status_col.astype(str).str.upper().str.strip()

        date_norm = pd.to_datetime(date_col, errors="coerce").dt.strftime("%d/%m/%Y")

        # =========================
        # FILTER DATA
        # =========================
        mask = (
            (datel == "BATU") &
            (status.str.contains("PS", na=False)) &
            (date_norm == tanggal)
        )

        hasil = df.loc[mask]

        if hasil.empty:
            await event.reply("❌ Tidak ada data PS.")
            return

        # =========================
        # OUTPUT
        # =========================
        msg = (
            f"📌 **PS BATU — {tanggal}**\n"
            f"📊 Total Data : {len(hasil)}\n\n"
        )

        for idx in hasil.index:

            msg += (
                "━━━━━━━━━━━━━━━━━━━\n"
                f"📍 DATEL       : {self._safe_val(df, idx, 'DATEL')}\n"
                f"📌 STATUS      : {self._safe_val(df, idx, status_name)}\n"
                f"🕒 TANGGAL     : {self._safe_val(df, idx, 'LAST_UPDATED_DATE')}\n"
                f"🆔 ORDER       : {self._safe_val(df, idx, 'ORDER_ID')}\n"
                f"💡 NO INTERNET : {self._safe_val(df, idx, 'SPEEDY')}\n"
                f"👤 NAMA        : {self._safe_val(df, idx, 'CUSTOMER_NAME')}\n"
                f"🏢 STO         : {self._safe_val(df, idx, 'STO')}\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
            )

        await event.reply(msg)