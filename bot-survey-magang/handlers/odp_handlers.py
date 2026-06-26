import logging
import re
import pandas as pd
from geopy.distance import geodesic

from utils.location import extract_coords_from_gmaps_link
from services.google_sheets import GoogleSheetsService
from config import SHEET_NAME

logger = logging.getLogger(__name__)


class ODPHandlers:
    def __init__(self):
        self.google_sheets_service = GoogleSheetsService()
        self.spreadsheet_name = SHEET_NAME
        self.odp_user_state = {}  # user_id: True jika menunggu input ODP

    # FORMAT OUTPUT
    def format_odp_result(self, nearest_5: pd.DataFrame) -> str:
        msg = "\n=== 5 ODP Terdekat ===\n"
        for i, row in enumerate(nearest_5.itertuples(index=False), start=1):
            odp = getattr(row, "ODP", "-")
            lat = float(getattr(row, "LATITUDE", 0))
            lon = float(getattr(row, "LONGITUDE", 0))
            dist_km = float(getattr(row, "DISTANCE_KM", 0))
            avai = getattr(row, "AVAI", "N/A")

            dist_meter = dist_km * 1000
            maps_link = f"https://www.google.com/maps?q={lat},{lon}"

            msg += (
                f"{i}. {odp} | {lat:.6f},{lon:.6f} | "
                f"{dist_meter:.2f} m | Port: {avai} | "
                f"[Maps]({maps_link})\n"
            )
        return msg

    # DATA SHEET
    def get_odp_dataframe(self) -> pd.DataFrame | None:
        try:
            data = self.google_sheets_service.get_sheet_data_by_name(
                self.spreadsheet_name, "ODP"
            )

            if not data or len(data) < 2:
                return None

            headers = data[0]
            rows = data[1:]
            return pd.DataFrame(rows, columns=headers)

        except Exception as e:
            logger.error(f"Gagal ambil sheet ODP: {e}")
            return None

    # PROSES UTAMA
    async def process_odp_nearest(self, event, user_id: str, lat: float, lon: float):
        user_maps = f"https://www.google.com/maps?q={lat},{lon}"

        await event.reply(
            f"📍 Lokasi Anda: {lat:.6f}, {lon:.6f}\n"
            f"🔗 [Lihat di Google Maps]({user_maps})\n\n"
            "🔍 Mencari 5 ODP terdekat...",
            parse_mode="markdown",
        )

        df = self.get_odp_dataframe()
        if df is None:
            await event.reply("❌ Data ODP tidak tersedia.")
            return

        required_cols = {"ODP", "LATITUDE", "LONGITUDE"}
        if not required_cols.issubset(df.columns):
            await event.reply("❌ Struktur kolom sheet ODP tidak valid.")
            return

        if "AVAI" not in df.columns:
            df["AVAI"] = "N/A"

        try:
            df["LATITUDE"] = df["LATITUDE"].astype(float)
            df["LONGITUDE"] = df["LONGITUDE"].astype(float)

            user_location = (lat, lon)
            df["DISTANCE_KM"] = df.apply(
                lambda r: geodesic(
                    user_location, (r["LATITUDE"], r["LONGITUDE"])
                ).km,
                axis=1,
            )

            nearest_5 = df.sort_values("DISTANCE_KM").head(5)
            msg = self.format_odp_result(nearest_5)
            await event.reply(msg, parse_mode="markdown")

        except Exception as e:
            await event.reply(f"❌ Error hitung jarak: {e}")

    # COMMAND /odp
    async def odp_command_handler(self, event):
        if not event.is_private:
            return

        user_id = str(event.sender_id)
        self.odp_user_state[user_id] = True

        await event.reply(
            "Silakan kirim salah satu:\n"
            "📍 Share lokasi\n"
            "🔗 Link Google Maps\n"
            "📌 Koordinat (contoh: -7.98, 112.63)"
        )

    # INPUT HANDLER
    async def handle_gmaps_link_with_odp(self, event, user_id: str) -> bool:
        lat, lon = extract_coords_from_gmaps_link(event.text.strip())
        if self.odp_user_state.get(user_id) and lat is not None and lon is not None:
            await self.process_odp_nearest(event, user_id, lat, lon)
            self.odp_user_state.pop(user_id, None)
            return True
        return False

    def extract_coords_from_text(self, text: str):
        match = re.search(r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", text)
        if match:
            return float(match.group(1)), float(match.group(2))
        return None, None

    async def handle_coordinate_text_with_odp(self, event, user_id: str) -> bool:
        if self.odp_user_state.get(user_id):
            lat, lon = self.extract_coords_from_text(event.text.strip())
            if lat is not None and lon is not None:
                await self.process_odp_nearest(event, user_id, lat, lon)
                self.odp_user_state.pop(user_id, None)
                return True
        return False

    async def handle_location_share_with_odp(self, event, user_id: str) -> bool:
        if self.odp_user_state.get(user_id) and event.message.geo:
            lat = event.message.geo.lat
            lon = event.message.geo.long
            await self.process_odp_nearest(event, user_id, lat, lon)
            self.odp_user_state.pop(user_id, None)
            return True
        return False
