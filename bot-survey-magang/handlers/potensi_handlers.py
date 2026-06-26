import logging
import re

from telethon import events, Button
from services.potensi_service import PotensiService
from utils.location import extract_coords_from_gmaps_link

logger = logging.getLogger(__name__)

# PotensiHandlers class to handle potensi-related operations
class PotensiHandlers:
    def __init__(self, client):
        self.client = client
        self.potensi_service = PotensiService()
        self.user_potensi_state = {}  # user_id: kategori

    # Method to format potensi results for display
    async def process_potensi_search(self, event, kategori, user_lat, user_lon):
        try:
            await event.reply(
                f"🔎 Mencari 10 potensi terdekat untuk kategori: {kategori}..."
            )
            
            df = self.potensi_service.get_potensi_dataframe(kategori)

            if df is None or df.empty:
                await event.reply(
                    f"❌ Data potensi untuk kategori '{kategori}' tidak ditemukan."
                )
                return
            
            nearest = self.potensi_service.find_nearest(
                df,
                user_lat,
                user_lon,
                n=10
            )
            
            if nearest.empty:
                await event.reply(
                    f"❌ Tidak ada data potensi '{kategori}' di sekitar lokasi Anda."
                )
                return
            
            # Cek kolom koordinat yang tersedia
            lat_col = None
            lon_col = None
            
            possible_lat_cols = ["lat", "latitude", "Lat", "Latitude"]
            possible_lon_cols = ["long", "longitude", "lon", "Long", "Longitude", "Lon"]
            
            for col in possible_lat_cols:
                if col in nearest.columns:
                    lat_col = col
                    break
                    
            for col in possible_lon_cols:
                if col in nearest.columns:
                    lon_col = col
                    break

            # Cek kolom nama
            possible_nama_cols = [
                'Nama',
                'nama',
                'NAMA',
                'Nama Instansi',
                'Nama Satuan Pendidikan',
                'Nama Hotel',
                'Nama KDMP',
                'Nama SPPG',
                'Nama Wisata',
                'Nama Faskes'
            ]

            nama_col = next(
                (col for col in possible_nama_cols if col in nearest.columns),
                None
            )

            # Cek kolom gmaps
            possible_gmaps_cols = [
                'Gmaps',
                'gmaps',
                'Google Maps',
                'Maps'
            ]

            gmaps_col = next(
                (col for col in possible_gmaps_cols if col in nearest.columns),
                None
            )

            # Cek kolom status
            stat_col = None

            possible_stat_cols = [
                'STAT',
                'Stat',
                'stat',
                'Status',
                'STATUS'
            ]

            for col in possible_stat_cols:
                if col in nearest.columns:
                    stat_col = col
                    break

            msg = f"📍 **10 Potensi Terdekat - {kategori}**\n\n"

            for i, (_, row) in enumerate(nearest.iterrows(), 1):

                nama = row.get(nama_col, '-') if nama_col else '-'
                lat = row.get(lat_col, 0) if lat_col else 0
                lon = row.get(lon_col, 0) if lon_col else 0
                dist = row.get('distance_m', 0)

                # Ambil status
                stat = ""

                if stat_col:
                    stat = str(row.get(stat_col, "")).strip().upper()

                # Emoji status
                if stat == "WIN":
                    stat_emoji = "🟢"
                elif stat == "LOSE":
                    stat_emoji = "🔴"
                elif stat == "UNKNOWN":
                    stat_emoji = "⚪"
                else:
                    stat_emoji = "⚫"
                    stat = "NULL"

                # Convert lat/lon
                try:
                    lat_float = float(str(lat)) if lat else 0.0
                    lon_float = float(str(lon)) if lon else 0.0
                except (ValueError, TypeError):
                    lat_float = 0.0
                    lon_float = 0.0

                # Ambil link gmaps dari sheet
                maps_link = None

                if gmaps_col:
                    maps_link = str(row.get(gmaps_col, "")).strip()

                # Validasi link gmaps
                invalid_gmaps = [
                    "",
                    "-",
                    "N/A",
                    "NONE",
                    "NULL",
                    "NAN"
                ]

                if (
                    not maps_link
                    or maps_link.upper() in invalid_gmaps
                    or "google.com" not in maps_link
                    and "goo.gl" not in maps_link
                    and "maps.app.goo.gl" not in maps_link
                ):
                    maps_link = (
                        f"https://www.google.com/maps?q="
                        f"{lat_float},{lon_float}"
                    )

                # Format jarak
                if dist < 1000:
                    distance_str = f"{dist:.0f} m"
                else:
                    distance_str = f"{dist/1000:.1f} km"

                msg += (
                    f"{i}. **{nama}**\n"
                    f"   {stat_emoji} {stat} | {distance_str}\n"
                    f"   📍 {lat_float:.6f}, {lon_float:.6f}\n"
                    f"   🗺️ [Lihat di Maps]({maps_link})\n\n"
                )
            
            await event.reply(msg, parse_mode='markdown')
            
        except Exception as e:
            logger.error(f"Error in process_potensi_search: {e}")
            await event.reply(f"❌ Terjadi error saat mencari potensi: {e}")

    # Extract koordinat dari text
    def extract_coords_from_text(self, text: str):
        match = re.search(
            r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)",
            text
        )

        if match:
            return float(match.group(1)), float(match.group(2))

        return None, None

    # Command handler for /potensi
    async def potensi_command_handler(self, event):
        """Handle /potensi command"""

        if event.is_private:

            categories = {
                "Semua": "Semua",
                "Manufaktur": "Manufaktur",
                "Pergudangan": "Pergudangan",
                "Cafe/Restaurant": "Cafe/Restaurant",
                "Distributor": "Distributor",
                "Finance": "New_Finance",
                "Education": "New_Education",
                "Hotel": "New_Hotel",
                "KDMP": "New_KDMP",
                "SPPG": "New_SPPG",
                "Wisata": "New_Wisata",
                "Faskes": "New_Faskes"
            }

            # Satu tombol per baris (reply keyboard)
            buttons = [[Button.text(cat)] for cat in categories.keys()]

            await event.reply(
                "🏷️ **Pilih Kategori Potensi:**\n\n"
                "Setelah memilih kategori, silakan kirim salah satu:\n"
                "📍 Share lokasi\n"
                "🔗 Link Google Maps\n"
                "📌 Koordinat (contoh: -7.98, 112.63)",
                buttons=buttons
            )

    # Method to handle Google Maps link with potensi state check
    async def handle_gmaps_link_with_potensi(self, event, user_id: str):
        """Handle Google Maps link with potensi state check"""

        if user_id in self.user_potensi_state:

            kategori = self.user_potensi_state[user_id]

            lat, lon = extract_coords_from_gmaps_link(
                event.text.strip()
            )

            if lat is not None and lon is not None:

                await self.process_potensi_search(
                    event,
                    kategori,
                    lat,
                    lon
                )

                self.user_potensi_state.pop(user_id, None)

                return True

            else:
                await event.reply(
                    "❌ Link Google Maps tidak valid "
                    "atau tidak mengandung koordinat."
                )

                return True

        return False

    # Handle koordinat text
    async def handle_coordinate_text_with_potensi(
        self,
        event,
        user_id: str
    ) -> bool:

        if self.user_potensi_state.get(user_id):

            lat, lon = self.extract_coords_from_text(
                event.text.strip()
            )

            if lat is not None and lon is not None:

                kategori = self.user_potensi_state[user_id]

                await self.process_potensi_search(
                    event,
                    kategori,
                    lat,
                    lon
                )

                self.user_potensi_state.pop(user_id, None)

                return True

        return False

    # Method to handle location sharing with potensi state check
    async def handle_location_share_with_potensi(
        self,
        event,
        user_id: str
    ):
        """Handle location share with potensi state check"""

        if user_id in self.user_potensi_state:

            kategori = self.user_potensi_state[user_id]

            user_lat = event.message.geo.lat
            user_lon = event.message.geo.long

            await self.process_potensi_search(
                event,
                kategori,
                user_lat,
                user_lon
            )

            self.user_potensi_state.pop(user_id, None)

            return True

        return False

    # Method to handle category selection for potensi
    async def handle_category_selection(self, event, user_id: str):
        """Handle category selection for potensi"""

        text = event.text.strip()

        categories = {
            "Semua": "Semua",
            "Manufaktur": "Manufaktur",
            "Pergudangan": "Pergudangan",
            "Cafe/Restaurant": "Cafe/Restaurant",
            "Distributor": "Distributor",
            "Finance": "New_Finance",
            "Education": "New_Education",
            "Hotel": "New_Hotel",
            "KDMP": "New_KDMP",
            "SPPG": "New_SPPG",
            "Wisata": "New_Wisata",
            "Faskes": "New_Faskes"
        }
        
        if text in categories:

            self.user_potensi_state[user_id] = categories[text]

            await event.reply(
                "📍 Silakan kirim salah satu:\n"
                "🔗 Link Google Maps\n"
                "📌 Koordinat (contoh: -7.98, 112.63)\n"
                "📍 Share lokasi"
            )

            return True

        return False