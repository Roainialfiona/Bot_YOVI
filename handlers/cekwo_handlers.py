import pandas as pd
from services.google_sheets import GoogleSheetsService
from config import SHEET_NAME


class CekWOHandlers:
    def __init__(self):
        self.gs = GoogleSheetsService()
        self.WORKSHEET = "REPORT PSB"
        self.MAX_LEN = 3500  # batas aman Telegram

    def get_df(self):
        data = self.gs.get_sheet_data_by_name(SHEET_NAME, self.WORKSHEET)
        if not data or len(data) < 3:
            return pd.DataFrame()

        header = data[1]
        rows = data[2:]

        df = pd.DataFrame(rows, columns=header)
        df.columns = df.columns.astype(str).str.strip().str.upper()
        return df

    def _safe_col(self, df, col_name):
        if col_name not in df.columns:
            return None
        col = df.loc[:, col_name]
        if isinstance(col, pd.DataFrame):
            return col.iloc[:, 0]
        return col

    def _safe_value(self, df, idx, col_name):
        if col_name not in df.columns:
            return "-"
        col = df.loc[:, col_name]
        if isinstance(col, pd.DataFrame):
            return col.iloc[idx, 0]
        return col.iloc[idx]

    async def _send_long_message(self, event, text):
        buffer = ""
        for line in text.split("\n"):
            if len(buffer) + len(line) + 1 > self.MAX_LEN:
                await event.reply(buffer, parse_mode="md")
                buffer = ""
            buffer += line + "\n"

        if buffer.strip():
            await event.reply(buffer, parse_mode="md")

    async def cekwo_handler(self, event, keyword):

        df = self.get_df()
        if df.empty:
            await event.reply("❌ Data PSB kosong.")
            return

        # =========================
        # 🔥 TAMBAHAN: FILTER DATEL BATU
        # =========================
        datel_col = self._safe_col(df, "DATEL")
        if datel_col is not None:
            df = df[
                datel_col.astype(str)
                .str.upper()
                .str.strip() == "BATU"
            ]

        # 🔥 penting biar index gak error
        df = df.reset_index(drop=True)

        # =========================
        # AMBIL KOLOM
        # =========================
        order_col = self._safe_col(df, "ORDER_ID")

        cust_col = None
        cust_name = None
        for c in ["CUSTOMER_NAME", "CUSTNAME"]:
            if c in df.columns:
                cust_col = self._safe_col(df, c)
                cust_name = c
                break

        internet_col = "SPEEDY" if "SPEEDY" in df.columns else None

        if order_col is None or cust_col is None:
            await event.reply(
                "❌ Struktur kolom sheet tidak sesuai.\n\n"
                f"Kolom terbaca:\n{', '.join(df.columns)}"
            )
            return

        keyword = str(keyword).strip()

        # =========================
        # SEARCH
        # =========================
        if keyword.isdigit():
            hasil = df[order_col.astype(str).str.strip() == keyword]
        else:
            cust_norm = (
                cust_col.astype(str)
                .str.lower()
                .str.replace(r"[^a-z0-9 ]", "", regex=True)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )
            hasil = df[cust_norm.str.contains(keyword.lower(), na=False)]

        if hasil.empty:
            await event.reply("❌ Data tidak ditemukan.")
            return

        # 🔥 FIX: reset index hasil
        hasil = hasil.reset_index(drop=True)

        # =========================
        # OUTPUT
        # =========================
        judul = (
            f"📌 **HASIL CEK WO – {keyword.upper()}**\n"
            f"📊 Ditemukan: **{len(hasil)} data**\n\n"
        )

        msg = judul

        # 🔥 FIX: pakai hasil, bukan df
        for i in range(len(hasil)):
            status = str(self._safe_value(hasil, i, "STATUS RESUME")).upper()

            block = (
                "━━━━━━━━━━━━━━━━━━\n"
                f"🆔 ORDER : `{self._safe_value(hasil, i, 'ORDER_ID')}`\n"
                f"👤 NAMA  : {self._safe_value(hasil, i, cust_name)}\n"
            )

            if "COMPLETED" in status and internet_col:
                speedy = self._safe_value(hasil, i, internet_col)
                if speedy not in ["-", "", None]:
                    block += f"🌐 INTERNET : {speedy}\n"

            block += (
                f"🏷️ STO        : {self._safe_value(hasil, i, 'STO')}\n"
                f"👤 SA         : {self._safe_value(hasil, i, 'KODE SA')}\n"
                f"👤 NAMA SA    : {self._safe_value(hasil, i, 'NAMA SA')}\n"
                f"🕒 TANGGAL     : {self._safe_value(hasil, i, 'LAST_UPDATED_DATE')}\n"
                f"🏢 AGENSI     : {self._safe_value(hasil, i, 'AGENSI')}\n"
                f"📌 STATUS     : {self._safe_value(hasil, i, 'DETAIL KET')}\n"
                f"📝 KET        : {self._safe_value(hasil, i, 'NOTE KET')}\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
            )

            if len(msg) + len(block) > self.MAX_LEN:
                await event.reply(msg, parse_mode="md")
                msg = block
            else:
                msg += block

        if msg.strip():
            await event.reply(msg, parse_mode="md")