import logging
from typing import Dict
from handlers.data_handlers import DataHandlers

logger = logging.getLogger(__name__)


class CommandHandlers:
    def __init__(self):
        self.data_handlers = DataHandlers()

    # =========================
    # HELP HANDLER
    # =========================
    async def help_handler(self, event):
        if not event.is_private:
            return

        help_text = (
            "🆘 **BANTUAN BOT YOVI**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "🔎 **1. CEK WORK ORDER (WO)**\n"
            "Cek detail WO berdasarkan Order ID / Nama Customer\n\n"
            "Format:\n"
            "• /cekwo 123456789\n"
            "• /cekwo nama_customer\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "📊 **2. SUMMARY PS (REKAP SA)**\n"
            "Menampilkan rekap PS (Completed) per Sales Agent — Datel Batu\n\n"

            "Format:\n"
            "• /summaryps\n"
            "• /summaryps <nama/SA>\n"
            "• /summaryps <nama/SA> <bulan>\n"
            "• /summaryps <nama/SA> <bulan> <tahun>\n"
            "• /summaryps <nama/SA> <dd/mm/yyyy>\n\n"

            "Contoh:\n"
            "• /summaryps\n"
            "• /summaryps joko\n"
            "• /summaryps joko maret\n"
            "• /summaryps joko maret 2025\n"
            "• /summaryps joko 12/03/2025\n\n"

            "Keterangan:\n"
            "• Bisa filter berdasarkan nama atau kode SA\n"
            "• Bulan: januari - desember\n"
            "• Tahun default: tahun sekarang\n"
            "• Bisa klik tombol **Lihat Detail** untuk rincian\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "📅 **3. DATA PS HARIAN**\n"
            "Menampilkan daftar PS berdasarkan tanggal\n\n"
            "Format:\n"
            "• /ps 12/02/2026\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "📦 **4. DATA OGP**\n"
            "Menampilkan data WO OGP\n\n"
            "Format:\n"
            "• /ogp\n"
            "• /ogp februari\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "🗂 **5. DATA CBASE**\n"
            "Mencari 5 data berdasarkan Nama Customer\n\n"
            "Format:\n"
            "• /cbase nama_customer\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "📍 **6. ODP & POTENSI TERDEKAT**\n"
            "Cari lokasi terdekat (wajib kirim lokasi dulu)\n\n"
            "Format:\n"
            "• /odp\n"
            "• /potensi\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "📄 **7. BROSUR**\n"
            "Menampilkan pilihan brosur\n\n"
            "Format:\n"
            "• /brosur HSI\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "💡 **Tips:**\n"
            "- Tidak sensitif huruf besar/kecil\n"
            "- Gunakan spasi setelah command\n"
            "- Nama SA bisa sebagian (tidak harus lengkap)\n"
            "- Pastikan data tersedia di Google Sheet\n"
        )

        await event.reply(help_text, parse_mode="md")

    # =========================
    # START HANDLER
    # =========================
    async def start_handler(self, event, user_started: Dict, pending_data: Dict):
        if not event.is_private:
            return

        user_id = str(event.sender_id)
        self.data_handlers.cleanup_pending_data(user_id, pending_data)

        await event.reply(
            "🤖 **Selamat datang di Bot YOVI!**\n\n"
            "Bot ini membantu pencarian data PSB, WO, CBASE, dan informasi lainnya.\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "📌 **COMMAND UTAMA:**\n\n"

            "🔎 /cekwo <keyword>\n"
            "Cek detail Work Order berdasarkan ORDER ID atau Nama Customer.\n\n"

            "📊 /summaryps [SA/bulan/tanggal]\n"
            "Rekap PS per SA (support filter SA, bulan, tahun & tanggal).\n\n"

            "📅 /ps <dd/mm/yyyy> \n"
            "Menampilkan daftar PS berdasarkan tanggal.\n\n"

            "📦 /ogp [bulan]\n"
            "Menampilkan daftar WO OGP (bisa filter bulan).\n\n"

            "🗂 /cbase <nama> \n"
            "Mencari 5 data CBASE berdasarkan Nama Customer.\n\n"

            "📍 /odp atau /potensi \n"
            "Cari 5 ODP / Potensi terdekat (kirim lokasi terlebih dahulu).\n\n"

            "📄 /brosur\n"
            "Menampilkan pilihan brosur yang tersedia.\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "Ketik /help untuk panduan lengkap."
        , parse_mode="md")

        user_started[user_id] = True
