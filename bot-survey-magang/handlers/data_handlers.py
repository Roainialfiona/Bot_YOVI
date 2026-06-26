import re
import os
import logging
from typing import Dict

from services.google_sheets import GoogleSheetsService

from utils.validation import (
    CAPTION_PATTERN,
    validate_caption_data,
    extract_markdown_link
)

from utils.location import (
    extract_coords_from_gmaps_link,
    process_coordinates
)

from utils.timezone_utils import format_timestamp

from config import REQUIRED_FIELDS


class DataHandlers:
    def __init__(self):
        self.sheets_service = GoogleSheetsService()

    def cleanup_pending_data(self, user_id: str, pending_data: dict):
        """Clean up pending data and temporary files for a user"""
        if user_id in pending_data:
            old_file_path = pending_data[user_id].get('file_path')
            if old_file_path and os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                    logger.info(f"Cleaned up temporary file: {old_file_path}")
                except Exception as e:
                    logger.error(f"Failed to remove temporary file: {e}")
            del pending_data[user_id]

    # ===============================
    # CAPTION REGEX (NAMED GROUPS)
    # ===============================
    CAPTION_PATTERN = re.compile(
        r"\*\*Nama SA\*\*:\s*(?P<nama_sa>.+)\n"
        r"\*\*STO\*\*:\s*(?P<sto>.+)\n"
        r"\*\*Cluster\*\*:\s*(?P<cluster>.+)\n"
        r"\*\*Usaha\*\*:\s*(?P<usaha>.+)\n"
        r"\*\*PIC\*\*:\s*(?P<pic>.+)\n"
        r"\*\*HPWA\*\*:\s*(?P<hpwa>.+)\n"
        r"\*\*Internet\*\*:\s*(?P<internet>.+)\n"
        r"\*\*Biaya\*\*:\s*(?P<biaya>.+)\n"
        r"\*\*VOC\*\*:\s*(?P<voc>.+?)"
        r"(?:\n\*\*Link GMaps\*\*:\s*(?P<link_gmaps>.+))?",
        re.DOTALL
    )

    # ===============================
    # MARKDOWN LINK EXTRACTOR
    # ===============================
    @staticmethod
    def extract_markdown_link(text: str) -> str:
        """
        Extract URL from markdown link: [text](url)
        """
        if not text:
            return ""
        match = re.search(r"\((https?://[^\s]+)\)", text)
        return match.group(1) if match else text.strip()

    # ===============================
    # PARSE CAPTION
    # ===============================
    @classmethod
    def parse_caption(cls, caption: str) -> dict:
        """
        Parse caption text into dictionary
        """
        match = cls.CAPTION_PATTERN.search(caption)
        if not match:
            return {}

        data = match.groupdict()

        # Normalize link gmaps
        if data.get("link_gmaps"):
            data["link_gmaps"] = cls.extract_markdown_link(data["link_gmaps"])

        return data

    # ===============================
    # CAPTION VALIDATOR
    # ===============================
    @staticmethod
    def validate_caption_data(row: dict):
        """
        Validate parsed caption data
        Returns:
            is_valid (bool)
            missing_fields (list)
            error_message (str)
        """
        missing_fields = []

        for field, label in REQUIRED_FIELDS.items():
            value = row.get(field)
            if not value or not value.strip():
                missing_fields.append(label)

        if missing_fields:
            error_message = (
                "❌ **Data belum lengkap!**\n\n"
                "Field yang masih kosong:\n• "
                + "\n• ".join(missing_fields)
                + "\n\nKetik /format untuk melihat format yang benar."
            )
            return False, missing_fields, error_message

        return True, [], ""
