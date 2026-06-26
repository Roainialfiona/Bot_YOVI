import gspread
import logging
from typing import Dict, List
from google.oauth2.service_account import Credentials
from config import SHEET_NAME, GOOGLE_CREDS_DICT

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    def __init__(self):
        self.sheet = None
        self._initialize_sheet()

    # ===============================
    # INIT GOOGLE SHEET (DEFAULT sheet1)
    # ===============================
    def _initialize_sheet(self):
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            creds = Credentials.from_service_account_info(
                GOOGLE_CREDS_DICT,
                scopes=scopes
            )

            gc = gspread.authorize(creds)
            spreadsheet = gc.open(SHEET_NAME)

            # Default pakai sheet pertama
            self.sheet = spreadsheet.sheet1

            logger.info("✅ Google Sheets service initialized")

        except Exception as e:
            logger.error(f"❌ Error initializing Google Sheets: {e}")
            raise

    # ===============================
    # GET DATA BY SHEET NAME (FIX ERROR)
    # ===============================
    def get_sheet_data_by_name(
        self,
        spreadsheet_name: str,
        worksheet_name: str
    ) -> List[List[str]]:
        """
        Ambil seluruh data dari worksheet tertentu
        (dipakai untuk whitelist Telegram ID)
        """
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            creds = Credentials.from_service_account_info(
                GOOGLE_CREDS_DICT,
                scopes=scopes
            )

            gc = gspread.authorize(creds)
            spreadsheet = gc.open(spreadsheet_name)
            worksheet = spreadsheet.worksheet(worksheet_name)

            data = worksheet.get_all_values()

            logger.info(f"✅ Data fetched from sheet '{worksheet_name}'")
            return data

        except Exception as e:
            logger.error(f"❌ Failed to get sheet data '{worksheet_name}': {e}")
            raise

    # ===============================
    # SAVE DATA VISIT
    # ===============================
    def save_to_spreadsheet(
        self,
        data: Dict[str, str],
        user_id: str,
        coords: str,
        file_link: str,
        gmaps_link: str = ""
    ) -> bool:
        try:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            no = len(self.sheet.get_all_values())

            row_data = [
                no,
                timestamp,
                user_id,
                data.get("nama_sa"),
                data.get("sto"),
                data.get("cluster"),
                data.get("usaha"),
                data.get("pic"),
                data.get("hpwa"),
                data.get("internet"),
                data.get("biaya"),
                data.get("voc"),
                coords,
                file_link,
                gmaps_link,
                "Default"
            ]

            self.sheet.append_row(row_data)
            logger.info(f"✅ Data saved for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save to spreadsheet: {e}")
            return False
