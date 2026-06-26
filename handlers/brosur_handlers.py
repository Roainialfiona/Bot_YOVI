import re
from telethon import Button
from services.google_sheets import GoogleSheetsService
from config import SHEET_NAME


class BrosurHandlers:
    def __init__(self):
        self.gs = GoogleSheetsService()
        self.WORKSHEET = "BROSUR"

    # =========================
    # CONVERT GOOGLE DRIVE LINK
    # =========================
    def _drive_to_direct(self, link):
        if not link:
            return None

        match = re.search(r"/d/([^/]+)", link)
        if not match:
            return None

        file_id = match.group(1)
        return f"https://drive.google.com/uc?id={file_id}"

    # =========================
    # LOAD DATA DARI SHEET
    # =========================
    def load_brosur(self):
        data = self.gs.get_sheet_data_by_name(SHEET_NAME, self.WORKSHEET)
        if not data or len(data) < 2:
            return []

        header = [h.strip().upper() for h in data[0]]
        rows = data[1:]

        result = []
        for row in rows:
            item = dict(zip(header, row))

            kode = item.get("KODE")
            link = item.get("GDRIVE_LINK")

            if not kode or not link:
                continue

            result.append({
                "kode": kode.strip(),
                "nama": item.get("NAMA_BROSUR", "").strip(),
                "link": self._drive_to_direct(link)
            })

        return result

    # =========================
    # /brosur → TAMPIL BUTTON
    # =========================
    async def brosur_handler(self, event):
        brosur = self.load_brosur()
        if not brosur:
            await event.reply("❌ Data brosur kosong.")
            return

        kode_unik = sorted(set(b["kode"] for b in brosur))
        buttons = [[Button.text(k, resize=True)] for k in kode_unik]

        await event.reply(
            "📂 **Pilih kategori brosur:**",
            buttons=buttons,
            parse_mode="md"
        )

    # =========================
    # BUTTON CLICK → KIRIM GAMBAR
    # =========================
    async def brosur_button_handler(self, event):
        teks = event.text.strip().lower()
        brosur = self.load_brosur()

        filtered = [b for b in brosur if b["kode"].lower() == teks]
        if not filtered:
            return

        for b in filtered:
            if not b["link"]:
                continue

            caption = f"📄 **{b['nama']}**" if b["nama"] else "📄 Brosur"

            await event.reply(
                file=b["link"],
                message=caption,
                parse_mode="md"
            )
