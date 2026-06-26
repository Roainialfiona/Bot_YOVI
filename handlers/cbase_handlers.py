import logging
import time
import pandas as pd
from services.google_sheets import GoogleSheetsService
from config import SHEET_NAME

logger = logging.getLogger(__name__)

class CBASEHandlers:
    def __init__(self, client):
        self.client = client
        self.google_sheets_service = GoogleSheetsService()
        self.spreadsheet_name = SHEET_NAME
        self._cache_df = None
        self._cache_time = 0
        self._cache_interval = 600  # 10 menit

    # ==============================
    # LOAD DATA DARI GOOGLE SHEET
    # ==============================
    def get_cbase_dataframe(self):
        now = time.time()
        if self._cache_df is not None and (now - self._cache_time < self._cache_interval):
            return self._cache_df

        try:
            data = self.google_sheets_service.get_sheet_data_by_name(
                self.spreadsheet_name, "PSB"
            )

            if not data or len(data) < 2:
                logger.warning("Sheet PSB kosong atau tidak valid")
                return None

            headers = data[0]
            rows = data[1:]
            df = pd.DataFrame(rows, columns=headers)

            self._cache_df = df
            self._cache_time = now

            logger.info(f"CBASE loaded: {len(df)} rows")
            return df

        except Exception as e:
            logger.error(f"Gagal load data CBASE: {e}")
            return None

    # ==============================
    # SEARCH CUSTOMER
    # ==============================
    def search_customer(self, df, customer_name):
        if "CUSTOMER NAME" not in df.columns:
            return None

        return df[df["CUSTOMER NAME"].str.contains(
            customer_name, case=False, na=False
        )]

    # ==============================
    # FORMAT OUTPUT (BERSIH)
    # ==============================
    def format_result(self, row):
        fields = [
            ("CUSTOMER NAME", "👤"),
            ("STO", "🏢"),
            ("NOMOR INTERNET", "💡"),
            ("PROVIDER", "🌐"),
            ("ALAMAT", "📍"),
            ("PAKET", "📦"),
            ("CHANNEL", "📡"),
            ("TGL PS", "📅"),
        ]

        msg = (
            "<b>📄 Hasil Pencarian CBASE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
        )

        for field, emoji in fields:
            value = row.get(field, "-")
            if field == "CUSTOMER NAME":
                msg += f"{emoji} <b>{value}</b>\n"
            else:
                msg += f"{emoji} <b>{field.title()}</b>: {value}\n"

        msg += "━━━━━━━━━━━━━━━━━━━━━━"
        return msg

    # ==============================
    # COMMAND /cbase
    # ==============================
    async def psb_command_handler(self, event):
        if not event.is_private:
            return

        text = event.text.strip()

        if len(text.split(" ", 1)) < 2:
            await event.reply("Silakan gunakan format:\n<b>/cbase NAMA CUSTOMER</b>", parse_mode="html")
            return

        customer_name = text.split(" ", 1)[1].strip()

        df = self.get_cbase_dataframe()
        if df is None or df.empty:
            await event.reply("❌ Data CBASE tidak ditemukan.")
            return

        matches = self.search_customer(df, customer_name)
        if matches is None or matches.empty:
            await event.reply(f"❌ Data CBASE untuk <b>{customer_name}</b> tidak ditemukan.", parse_mode="html")
            return

        for _, row in matches.iterrows():
            msg = self.format_result(row)
            await event.reply(msg, parse_mode="html")
