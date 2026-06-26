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

        # Cache CBASE
        self._cache_df = None
        self._cache_time = 0
        self._cache_interval = 600  # 10 menit

        # Cache ROLE
        self._roles_cache = None
        self._roles_cache_time = 0
        self._roles_cache_interval = 300  # 5 menit

    # ==============================
    # LOAD DATA CBASE (CACHE)
    # ==============================
    def get_cbase_dataframe(self):
        now = time.time()

        if (
            self._cache_df is not None and
            (now - self._cache_time < self._cache_interval)
        ):
            return self._cache_df

        try:
            data = self.google_sheets_service.get_sheet_data_by_name(
                self.spreadsheet_name, "History PSB"
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
    # LOAD USER ROLES (CACHE)
    # ==============================
    def get_user_roles(self):
        now = time.time()

        if (
            self._roles_cache is not None and
            (now - self._roles_cache_time < self._roles_cache_interval)
        ):
            return self._roles_cache

        try:
            data = self.google_sheets_service.get_sheet_data_by_name(
                self.spreadsheet_name, "Credentials"
            )

            if not data or len(data) < 2:
                logger.warning("Sheet Credentials kosong atau tidak valid")
                return {}

            headers = data[0]
            rows = data[1:]
            df = pd.DataFrame(rows, columns=headers)

            roles = {}
            for _, row in df.iterrows():
                try:
                    # skip kalau kosong
                    if not row["Telegram ID"]:
                        continue

                    user_id = int(row["Telegram ID"])
                    role = str(row["Role"]).strip().lower()

                    # skip kalau role kosong
                    if not role or role == "nan":
                        continue

                    roles[user_id] = role

                except Exception:
                    continue

            self._roles_cache = roles
            self._roles_cache_time = now

            logger.info(f"Credentials loaded: {len(roles)} users")
            return roles

        except Exception as e:
            logger.error(f"Gagal load Roles: {e}")
            return {}

    # ==============================
    # PERMISSION SYSTEM (SIMPLE)
    # ==============================
    def has_cbase_access(self, user_id, roles_dict):
        role = roles_dict.get(user_id)
        return role == "admin"  # hanya admin boleh

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
    # FORMAT OUTPUT
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

        user_id = event.sender_id

        # 🔐 LOAD ROLES
        roles = self.get_user_roles()

        # ambil role user (untuk logging)
        role = roles.get(user_id, "unknown")

        # 🔐 CEK AKSES (HANYA ADMIN)
        if not self.has_cbase_access(user_id, roles):
            await event.reply("❌ Kamu tidak punya akses ke command ini.")
            logger.warning(f"[CBASE DENIED] user_id={user_id}, role={role}")
            return

        text = event.text.strip()

        # Validasi input
        if len(text.split(" ", 1)) < 2:
            await event.reply(
                "Silakan gunakan format:\n<b>/cbase NAMA CUSTOMER</b>",
                parse_mode="html"
            )
            return

        customer_name = text.split(" ", 1)[1].strip()

        # Load data
        df = self.get_cbase_dataframe()
        if df is None or df.empty:
            await event.reply("❌ Data CBASE tidak ditemukan.")
            return

        # Cari data
        matches = self.search_customer(df, customer_name)
        if matches is None or matches.empty:
            await event.reply(
                f"❌ Data CBASE untuk <b>{customer_name}</b> tidak ditemukan.",
                parse_mode="html"
            )
            return

        # Kirim hasil
        for _, row in matches.iterrows():
            msg = self.format_result(row)
            await event.reply(msg, parse_mode="html")