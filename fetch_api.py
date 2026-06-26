import requests
import ast
import logging
import re
import time
from datetime import datetime
from dateutil import parser
import pytz

from services.google_sheets import GoogleSheetsService
from config import API_TOKEN, API_URL, SHEET_NAME


logger = logging.getLogger(__name__)


class FetchAPI:
    def __init__(self, token, api_url, spreadsheet_name, worksheet_name="Survey"):
        self.token = token
        self.api_url = api_url.rstrip('/')
        self.spreadsheet_name = spreadsheet_name
        self.worksheet_name = worksheet_name


    # =========================
    # TOKEN VALIDATION
    # =========================
    def validate_token(self):
        if not self.token or not self.api_url:
            logger.error("API_TOKEN atau API_URL belum diset")
            return False

        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(
                f"{self.api_url.replace('/sales-agent-surveys','')}/validate",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False


    # =========================
    # GET EXISTING DATA
    # =========================
    def get_existing_records(self):
        try:
            sheet = GoogleSheetsService().sheet.spreadsheet.worksheet(self.worksheet_name)
            values = sheet.get_all_values()
            if len(values) <= 1:
                return []
            header = values[0]
            return [dict(zip(header, row)) for row in values[1:]]
        except Exception as e:
            logger.error(f"Error reading sheet: {e}")
            return []


    def get_latest_id_from_sheet(self):
        records = self.get_existing_records()
        if not records:
            return 0
        try:
            return int(records[-1].get("ID", 0))
        except Exception:
            return 0


    # =========================
    # FETCH DATA
    # =========================
    def fetch_survey_data(self, witel_id=2, per_page=50):
        if not self.validate_token():
            return []

        last_id = self.get_latest_id_from_sheet()
        logger.info(f"Latest ID in sheet: {last_id}")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

        page = 1
        all_records = []

        while True:
            try:
                response = requests.get(
                    self.api_url,
                    headers=headers,
                    params={
                        "witel_id": witel_id,
                        "page": page,
                        "per_page": per_page
                    },
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                records = data.get("data", [])
                new_records = [r for r in records if int(r.get("id", 0)) > last_id]

                all_records.extend(new_records)

                last_url = data.get("links", {}).get("last")
                if not last_url or not new_records:
                    break

                page += 1
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"Fetch error page {page}: {e}")
                break

        logger.info(f"Fetched {len(all_records)} new records")
        return all_records


    # =========================
    # PARSING DATA
    # =========================
    def parse_survey_data(self, records):
        rows = []

        question_map = {
            'Nama usaha?': 'Nama Usaha',
            'Jenis usaha (ekosistem)?': 'Jenis Usaha',
            'Alamat usaha?': 'Alamat Usaha',
            'Nama PIC yang ditemui?': 'PIC',
            'Status PIC yang ditemui? (Owner / Karyawan)': 'Status PIC',
            'Nomor HP PIC yang ditemui?': 'HP/WA',
            'Layanan yang digunakan saat ini? (Indibiz / Kompetitor / Belum Berlangganan)?': 'Internet Existing',
            'Harga layanan Solusi yang digunakan saat ini?': 'Biaya Internet Existing',
            'Biaya Maksimal untuk Internet (anggaran yang disediakan)?': 'Alokasi',
            'Hasil visit?': 'Voice of Customer'
        }

        for rec in records:
            try:
                questions = self.safe_parse(rec.get("questions", []))
                sales = self.safe_parse(rec.get("sales_agent", {}))

                created_at = parser.isoparse(rec["created_at"]).astimezone(
                    pytz.timezone("Asia/Jakarta")
                ).strftime("%Y-%m-%d %H:%M:%S")

                row = {
                    "ID": rec.get("id"),
                    "Created At": created_at,
                    "SA ID": sales.get("id"),
                    "SA Name": sales.get("name"),
                    "City": rec.get("city"),
                    "Longitude": rec.get("longitude"),
                    "Latitude": rec.get("latitude"),
                    "ODP Name": rec.get("odp_name"),
                    "STO": rec.get("sto"),
                }

                for q in questions:
                    if q["question"] in question_map:
                        row[question_map[q["question"]]] = q.get("answer", "")

                rows.append(row)

            except Exception as e:
                logger.error(f"Parse error ID {rec.get('id')}: {e}")

        return rows


    def safe_parse(self, data):
        if isinstance(data, (list, dict)):
            return data
        try:
            return ast.literal_eval(data)
        except Exception:
            return []


    # =========================
    # SAVE TO SHEET
    # =========================
    def save_to_sheet(self, rows):
        if not rows:
            return

        sheet = GoogleSheetsService().sheet.spreadsheet.worksheet(self.worksheet_name)
        header = sheet.row_values(1)
        values = [[row.get(col, "") for col in header] for row in rows]
        sheet.append_rows(values)
        logger.info(f"Saved {len(rows)} rows to sheet")


    # =========================
    # MAIN RUNNER
    # =========================
    def run(self):
        logger.info("Running fetch cycle...")
        records = self.fetch_survey_data()
        if not records:
            logger.info("No new data")
            return

        rows = self.parse_survey_data(records)
        self.save_to_sheet(rows)
        logger.info("Fetch cycle completed")


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    fetcher = FetchAPI(
        token=API_TOKEN,
        api_url=API_URL,
        spreadsheet_name=SHEET_NAME,
        worksheet_name="Sheet1"
    )
    fetcher.run()
