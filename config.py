import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

# ===============================
# ENV HELPER
# ===============================
def get_env_var(name, required=True):
    value = os.getenv(name)
    if required and not value:
        raise ValueError(f"{name} environment variable not set!")
    return value

# ===============================
# TELEGRAM
# ===============================
API_ID = int(get_env_var("API_ID"))
API_HASH = get_env_var("API_HASH")
BOT_TOKEN = get_env_var("BOT_TOKEN")

# ===============================
# GOOGLE SHEETS
# ===============================
SHEET_NAME = get_env_var("GOOGLE_SHEET_NAME")

GOOGLE_CREDS_JSON = get_env_var("GOOGLE_CREDS_JSON")
GOOGLE_CREDS_DICT = json.loads(GOOGLE_CREDS_JSON)

# ===============================
# FASTAPI
# ===============================
API_TOKEN = get_env_var("API_TOKEN", required=False)
API_URL = get_env_var("API_URL", required=False)

# ===============================
# SUPABASE CONFIG
# ===============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ===============================
# REQUIRED FIELDS (VALIDATION)
# ===============================
REQUIRED_FIELDS = {
    "nama_sa": "Nama SA/AR",
    "sto": "STO",
    "cluster": "Cluster",
    "usaha": "Nama Usaha",
    "pic": "Nama PIC",
    "hpwa": "Nomor HP/WA",
    "internet": "Internet Existing",
    "biaya": "Biaya Internet",
    "voc": "Voice of Customer"
}

# ===============================
# LOGGING
# ===============================
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
