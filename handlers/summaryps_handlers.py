import pandas as pd
from telethon import Button
from services.google_sheets import GoogleSheetsService
from config import SHEET_NAME
from datetime import datetime


class SummaryPSHandlers:

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
    
    def _safe_val(self, df, idx, col):
        if col not in df.columns:
            return "-"
            
        c = df.loc[:, col]

        if isinstance(c, pd.DataFrame):
            return c.iloc[idx, 0]

        return c.iloc[idx]

    # ===============================
    # MAIN HANDLER
    # ===============================
    async def summaryps_handler(self, event):

        args = event.text.split()[1:]

        keyword = None
        bulan = None
        tahun = datetime.now().year
        tanggal = None

        for arg in args:

            a = arg.lower().strip()

            if a in self.bulan_map:
                bulan = self.bulan_map[a]

            elif "/" in a:
                tanggal = a

            elif a.isdigit():
                tahun = int(a)

            else:
                keyword = a

        df = self.get_df()

        if df.empty:
            await event.reply("❌ Data PS tidak tersedia.")
            return

        datel_col = self._safe_col(df, "DATEL")
        kode_sa_col = self._safe_col(df, "KODE SA")
        nama_sa_col = self._safe_col(df, "NAMA SA")
        tgl_order_col = self._safe_col(df, "DATA PS")
        status_col = self._safe_col(df, "DETAIL KET")

        df["_DATEL"] = datel_col.astype(str).str.strip().str.upper()
        df["_KODE_SA"] = kode_sa_col.astype(str).str.strip().str.upper()
        df["_NAMA_SA"] = nama_sa_col.astype(str).str.strip().str.upper()
        df["_STATUS"] = status_col.astype(str).str.strip().str.upper()
        df["_TGL_ORDER"] = pd.to_datetime(tgl_order_col, errors="coerce")

        hasil = df[
            (df["_DATEL"] == "BATU") &
            (df["_STATUS"].isin(["PS", "PS HI"]))
        ]

        # ===============================
        # MODE SA SAJA
        # ===============================
        if keyword and not bulan and not tanggal:

            sa_data = hasil[
                hasil["_KODE_SA"].str.contains(keyword, case=False, na=False) |
                hasil["_NAMA_SA"].str.contains(keyword, case=False, na=False)
            ]

            if sa_data.empty:
                await event.reply("❌ SA tidak ditemukan.")
                return

            grouped = (
                sa_data
                .groupby(["_KODE_SA", "_NAMA_SA"])
                .size()
                .reset_index(name="TOTAL")
                .sort_values("TOTAL", ascending=False)
            )

            msg = "📊 **SUMMARY PS SA**\n\n"

            for _, row in grouped.iterrows():

                msg += (
                    f"👤 {row['_NAMA_SA']}\n"
                    f"🆔 {row['_KODE_SA']}\n"
                    f"✅ PS : {row['TOTAL']}\n"
                    "━━━━━━━━━━━━━━━\n"
                )

            await event.reply(msg)

            return

        # ===============================
        # MODE SA + BULAN
        # ===============================
        if keyword and bulan:

            sa_data = hasil[
                (hasil["_TGL_ORDER"].dt.month == bulan) &
                (hasil["_TGL_ORDER"].dt.year == tahun) &
                (
                    hasil["_KODE_SA"].str.contains(keyword, case=False, na=False) |
                    hasil["_NAMA_SA"].str.contains(keyword, case=False, na=False)
                )
            ]

            if sa_data.empty:
                await event.reply("❌ Data SA tidak ditemukan.")
                return

            sa_nama = sa_data["_NAMA_SA"].iloc[0]

            msg = (
                f"📊 **REKAP PS SA**\n\n"
                f"Nama SA : {sa_nama}\n"
                f"Bulan   : {bulan}/{tahun}\n"
                f"Total PS: {len(sa_data)}"
            )

            buttons = [
                Button.inline(
                    "📋 Lihat Detail",
                    data=f"detail_pssa|{keyword}|{bulan}|{tahun}"
                )
            ]

            await event.reply(msg, buttons=buttons)

            return

        # ===============================
        # MODE SA + TANGGAL
        # ===============================
        if keyword and tanggal:

            hasil = hasil[
                hasil["_TGL_ORDER"].dt.strftime("%d/%m/%Y") == tanggal
            ]

            hasil = hasil[
                hasil["_KODE_SA"].str.contains(keyword, case=False, na=False) |
                hasil["_NAMA_SA"].str.contains(keyword, case=False, na=False)
            ]

            if hasil.empty:
                await event.reply("❌ Data tidak ditemukan.")
                return

            sa_nama = hasil["_NAMA_SA"].iloc[0]

            msg = (
                f"📌 **PS BATU — {tanggal}**\n"
                f"Nama SA : {sa_nama}\n"
                f"📊 Total PS : {len(hasil)}\n\n"
            )

            for idx in hasil.index:

                msg += (
                    "━━━━━━━━━━━━━━━━━━━\n"
                    f"📍 DATEL       : {self._safe_val(df, idx, 'DATEL')}\n"
                    f"📌 STATUS      : Completed (PS)\n"
                    f"🕒 TANGGAL     : {self._safe_val(df, idx, 'LAST_UPDATED_DATE')}\n"
                    f"🆔 ORDER       : {self._safe_val(df, idx, 'ORDER_ID')}\n"
                    f"💡 NO INTERNET : {self._safe_val(df, idx, 'SPEEDY')}\n"
                    f"👤 NAMA        : {self._safe_val(df, idx, 'CUSTOMER_NAME')}\n"
                    f"🏢 STO         : {self._safe_val(df, idx, 'STO')}\n"
                    "━━━━━━━━━━━━━━━━━━━\n\n"
                )

            await event.reply(msg)
            return

        # ===============================
        # MODE SUMMARY
        # ===============================
        if bulan:

            hasil = hasil[
                (hasil["_TGL_ORDER"].dt.month == bulan) &
                (hasil["_TGL_ORDER"].dt.year == tahun)
            ]

        grouped = (
            hasil
            .groupby(["_KODE_SA", "_NAMA_SA"])
            .size()
            .reset_index(name="TOTAL")
            .sort_values("TOTAL", ascending=False)
        )

        grand_total = len(hasil)

        msg = (
            "📊 **SUMMARY PS — DATEL BATU**\n\n"
            f"📌 Total SA : {len(grouped)}\n"
            f"📦 Total PS : {grand_total}\n\n"
        )

        for _, row in grouped.iterrows():

            block = (
                f"👤 {row['_NAMA_SA']}\n"
                f"🆔 {row['_KODE_SA']}\n"
                f"✅ PS : {row['TOTAL']}\n"
                "━━━━━━━━━━━━━━━\n"
            )

            if len(msg) + len(block) > 3500:
                await event.reply(msg)
                msg = ""

            msg += block

        if msg.strip():
            await event.reply(msg)

    # ===============================
    # DETAIL BUTTON
    # ===============================
    async def show_detail_pssa(self, event, keyword, bulan, tahun):

        df = self.get_df()

        datel_col = self._safe_col(df, "DATEL")
        kode_sa_col = self._safe_col(df, "KODE SA")
        nama_sa_col = self._safe_col(df, "NAMA SA")
        tgl_order_col = self._safe_col(df, "DATA PS")
        status_col = self._safe_col(df, "DETAIL KET")

        df["_DATEL"] = datel_col.astype(str).str.strip().str.upper()
        df["_KODE_SA"] = kode_sa_col.astype(str).str.strip().str.upper()
        df["_NAMA_SA"] = nama_sa_col.astype(str).str.strip().str.upper()
        df["_STATUS"] = status_col.astype(str).str.strip().str.upper()
        df["_TGL_ORDER"] = pd.to_datetime(tgl_order_col, errors="coerce")

        hasil = df[
            (df["_DATEL"] == "BATU") &
            (df["_STATUS"].isin(["PS", "PS HI"])) &
            (df["_TGL_ORDER"].dt.month == bulan) &
            (df["_TGL_ORDER"].dt.year == tahun) &
            (
                df["_KODE_SA"].str.contains(keyword, case=False, na=False) |
                df["_NAMA_SA"].str.contains(keyword, case=False, na=False)
            )
        ]

        if hasil.empty:
            await event.respond("❌ Detail tidak ditemukan.")
            return

        msg = (
            f"📌 **PS BATU — {bulan}/{tahun}**\n"
            f"Nama SA : {hasil['_NAMA_SA'].iloc[0]}\n"
            f"📊 Total PS : {len(hasil)}\n\n"
        )

        for idx in hasil.index:

            block = (
                "━━━━━━━━━━━━━━━━━━━\n"
                f"📍 DATEL       : {self._safe_val(df, idx, 'DATEL')}\n"
                f"📌 STATUS      : Completed (PS)\n"
                f"🕒 TANGGAL     : {self._safe_val(df, idx, 'DATA PS')}\n"
                f"🆔 ORDER       : {self._safe_val(df, idx, 'ORDER_ID')}\n"
                f"💡 NO INTERNET : {self._safe_val(df, idx, 'SPEEDY')}\n"
                f"👤 NAMA        : {self._safe_val(df, idx, 'CUSTOMER_NAME')}\n"
                f"🏢 STO         : {self._safe_val(df, idx, 'STO')}\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
            )

            if len(msg) + len(block) > 3500:
                await event.respond(msg)
                msg = ""

            msg += block

        if msg:
            await event.respond(msg)