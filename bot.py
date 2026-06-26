import logging
from typing import Dict
from telethon import TelegramClient, events
from config import API_ID, API_HASH, BOT_TOKEN, setup_logging
from handlers.cekwo_handlers import CekWOHandlers
from handlers.data_handlers import DataHandlers
from handlers.location_handlers import LocationHandlers
from handlers.command_handlers import CommandHandlers
from handlers.odp_handlers import ODPHandlers
from handlers.ogp_handlers import OGPHandlers
from handlers.potensi_handlers import PotensiHandlers
from handlers.cbase_handlers import CBASEHandlers
from handlers.brosur_handlers import BrosurHandlers
from handlers.summaryps_handlers import SummaryPSHandlers
from handlers.ps_handlers import PSHandlers
from services.google_sheets import GoogleSheetsService
import time

# ================= SETUP LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================= INIT CLIENT =================
client = TelegramClient("bot", API_ID, API_HASH)  # type: ignore

# ================= INIT HANDLERS =================
data_handlers = DataHandlers()
location_handlers = LocationHandlers()
command_handlers = CommandHandlers()
odp_handlers = ODPHandlers()
potensi_handlers = PotensiHandlers(client)
cbase_handlers = CBASEHandlers(client)
brosur_handlers = BrosurHandlers()
summaryps_handlers = SummaryPSHandlers()
ps_handlers = PSHandlers()
cekwo_handler = CekWOHandlers()
ogp_handlers = OGPHandlers()

# ================= DATA STORAGE =================
pending_data: Dict[str, Dict] = {}
user_started: Dict[str, bool] = {}

# ================= WHITELIST CACHE =================
allowed_telegram_ids = set()
last_id_fetch_time = 0
ID_FETCH_INTERVAL = 60  # seconds


def fetch_allowed_telegram_ids():
    global allowed_telegram_ids, last_id_fetch_time
    now = time.time()

    if now - last_id_fetch_time < ID_FETCH_INTERVAL and allowed_telegram_ids:
        return allowed_telegram_ids

    try:
        gs = GoogleSheetsService()
        from config import SHEET_NAME

        data = gs.get_sheet_data_by_name(SHEET_NAME, "Credentials")
        if not data or len(data) <= 1:
            return allowed_telegram_ids

        headers = data[0]
        rows = data[1:]

        id_col = None
        for i, h in enumerate(headers):
            if h.strip().lower() in [
                "telegram id",
                "telegram_id",
                "id telegram",
                "id",
            ]:
                id_col = i
                break

        if id_col is not None:
            allowed_telegram_ids = {
                str(row[id_col]).strip() for row in rows if row[id_col]
            }
            last_id_fetch_time = now

    except Exception as e:
        logger.error(f"Gagal fetch Telegram ID: {e}")

    return allowed_telegram_ids


async def is_user_allowed(event):
    user_id = str(event.sender_id)
    if user_id not in fetch_allowed_telegram_ids():
        await event.reply(
            "❌ Anda tidak terdaftar sebagai user bot.\nSilakan hubungi admin."
        )
        return False
    return True


# ================= MAIN HANDLER =================
@client.on(events.NewMessage(incoming=True))
async def main_handler(event):
    try:
        if not event.is_private:
            return

        user_id = str(event.sender_id)
        text = (event.text or "").lower()

        # ⛔ MODE POTENSI (STOP TOTAL)
        if user_id in potensi_handlers.user_potensi_state:
            if await potensi_handlers.handle_category_selection(event, user_id):
                return

            if getattr(event.message, "geo", None):
                await potensi_handlers.handle_location_share_with_potensi(
                    event, user_id
                )
                return

            if any(
                x in text
                for x in ["maps.google.com", "goo.gl/maps", "maps.app.goo.gl"]
            ):
                await potensi_handlers.handle_gmaps_link_with_potensi(event, user_id)
                return

            return

        # COMMAND → biar router yg handle
        if event.text and event.text.startswith("/"):
            return

        # WHITELIST
        if not await is_user_allowed(event):
            return

        # WAJIB /START
        if user_id not in user_started:
            await event.reply(
                "⚠️ Silakan ketik /start terlebih dahulu sebelum mengirim data."
            )
            return

        # MODE ODP
        if user_id in odp_handlers.odp_user_state:
            return

        # FOTO
        if event.photo:
            if not event.text:
                await data_handlers.handle_photo_only(
                    event, user_id, pending_data
                )
            else:
                await data_handlers.handle_photo_with_caption(
                    event, user_id, pending_data
                )
            return

        # TEKS / LOKASI
        if text:
            if any(
                x in text
                for x in ["maps.google.com", "goo.gl/maps", "maps.app.goo.gl"]
            ):
                if await potensi_handlers.handle_gmaps_link_with_potensi(
                    event, user_id
                ):
                    return
                if await odp_handlers.handle_gmaps_link_with_odp(event, user_id):
                    return
                await location_handlers.handle_gmaps_link(
                    event, user_id, pending_data
                )
                return

            if await potensi_handlers.handle_category_selection(event, user_id):
                return

        if getattr(event.message, "geo", None):
            if await potensi_handlers.handle_location_share_with_potensi(
                event, user_id
            ):
                return
            if await odp_handlers.handle_location_share_with_odp(event, user_id):
                return
            await location_handlers.handle_location_share(
                event, user_id, pending_data
            )
            return

    except Exception as e:
        logger.error(f"Main handler error: {e}")
        try:
            await event.reply("❌ Terjadi kesalahan pada bot.")
        except:
            pass


# ================= ROUTER =================
@client.on(events.NewMessage(incoming=True))
async def router(event):
    if not event.is_private:
        return

    user_id = str(event.sender_id)
    text = (event.text or "").strip()

    if user_id in potensi_handlers.user_potensi_state:
        return

    if not await is_user_allowed(event):
        return

    # COMMAND
    if text.startswith("/"):
        if text == "/start":
            user_started[user_id] = True
            await command_handlers.start_handler(event, user_started, pending_data)
            return

        if text == "/odp":
            user_started[user_id] = True
            await odp_handlers.odp_command_handler(event)
            return

        return

    # MODE ODP
    if user_id in odp_handlers.odp_user_state:
        if getattr(event.message, "geo", None):
            if await odp_handlers.handle_location_share_with_odp(event, user_id):
                return

        if "maps" in text:
            if await odp_handlers.handle_gmaps_link_with_odp(event, user_id):
                return

        if await odp_handlers.handle_coordinate_text_with_odp(event, user_id):
            return

        await event.reply(
            "❗ Format tidak dikenali.\n\n"
            "Gunakan:\n"
            "• Share lokasi\n"
            "• Link Google Maps\n"
            "• Koordinat\n\n"
            "Contoh:\n`-7.98, 112.63`",
            parse_mode="markdown",
        )
        return

    # NORMAL MODE
    if user_id not in user_started:
        await event.reply("⚠️ Silakan ketik /start terlebih dahulu!")
        return

# ================= COMMANDS =================

@client.on(events.NewMessage(pattern=r"^/help$", incoming=True))
async def help_handler(event):
    if await is_user_allowed(event):
        user_id = event.sender_id
        logger.info(f"⚡ Command /help used by {user_id}")
        await command_handlers.help_handler(event)


@client.on(events.NewMessage(pattern=r"^/potensi$", incoming=True))
async def potensi_handler(event):
    if await is_user_allowed(event):
        user_id = event.sender_id
        logger.info(f"⚡ Command /potensi used by {user_id}")
        await potensi_handlers.potensi_command_handler(event)


@client.on(events.NewMessage(pattern=r"^/cbase(\s+.+)?$", incoming=True))
async def cbase_handler(event):
    if await is_user_allowed(event):
        user_id = event.sender_id
        logger.info(f"⚡ Command /cbase used by {user_id}")
        await cbase_handlers.psb_command_handler(event)


@client.on(events.NewMessage(pattern=r"^/summaryps.*$", incoming=True))
async def summaryps_handler(event):
    if await is_user_allowed(event):
        user_id = event.sender_id
        logger.info(f"⚡ Command /summaryps used by {user_id}")
        await summaryps_handlers.summaryps_handler(event)


@client.on(events.NewMessage(pattern=r'^/brosur$'))
async def brosur_command(event):
    user_id = event.sender_id
    logger.info(f"⚡ Command /brosur used by {user_id}")
    await brosur_handlers.brosur_handler(event)


@client.on(events.NewMessage)
async def brosur_button_click(event):
    await brosur_handlers.brosur_button_handler(event)


@client.on(events.NewMessage(pattern=r"^/ps\s+\d{2}/\d{2}/\d{4}$", incoming=True))
async def ps_command(event):
    if await is_user_allowed(event):
        user_id = event.sender_id
        logger.info(f"⚡ Command /ps used by {user_id}")
        tanggal = event.text.split(" ", 1)[1]
        await ps_handlers.ps_handler(event, tanggal)


@client.on(events.NewMessage(pattern=r"^/cekwo\s+.+", incoming=True))
async def cekwo_command(event):
    if await is_user_allowed(event):
        user_id = event.sender_id
        logger.info(f"⚡ Command /cekwo used by {user_id}")
        keyword = event.text.split(" ", 1)[1]
        await cekwo_handler.cekwo_handler(event, keyword)


@client.on(events.NewMessage(pattern=r'^/ogp(\s|$)', incoming=True))
async def ogp_command(event):
    if not await is_user_allowed(event):
        return
    user_id = event.sender_id
    logger.info(f"⚡ Command /ogp used by {user_id}")
    await ogp_handlers.ogp_handler(event)

@client.on(events.CallbackQuery(pattern=b"detail_pssa"))
async def detail_pssa_handler(event):

    data = event.data.decode().split("|")

    keyword = data[1]
    bulan = int(data[2])
    tahun = int(data[3])

    await event.answer()

    await summaryps_handlers.show_detail_pssa(event, keyword, bulan, tahun)

# ================= RUN BOT =================
if __name__ == "__main__":
    logger.info("Bot is starting...")
    try:
        client.start(bot_token=BOT_TOKEN)
        logger.info("Bot is running...")
        client.run_until_disconnected()
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.exception(e)