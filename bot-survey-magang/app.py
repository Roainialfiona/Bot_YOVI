import streamlit as st
import pandas as pd
import json
import os
import subprocess
import threading
import time, requests
import sys
from datetime import datetime
from utils.timezone_utils import get_current_time, format_timestamp
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from urllib.parse import quote

# Load environment variables
load_dotenv()

# Keep-alive function to ping the app periodically
def keep_alive(url):
    while True:
        try:
            requests.get(url)
        except Exception:
            pass
        time.sleep(1800)  # Ping every 30 minutes

# Start keep-alive thread (replace with your app's public URL)
threading.Thread(target=keep_alive, args=("https://yovi-bot.streamlit.app",), daemon=True).start()

# Page configuration
st.set_page_config(
    page_title="YOVI Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
/* ===== Global App Background ===== */
    .stApp {
        background: linear-gradient(135deg, #e0f2ff, #f5faff, #ffffff);
        color: #1f2937;
        font-family: "Inter", "Segoe UI", sans-serif;
    }

/* ===== Main Header ===== */
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 2.2rem;
            
        background: linear-gradient(90deg, #3b82f6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

/* ===== Card / Metric ===== */
    .metric-card {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 
            0 10px 30px rgba(0, 0, 0, 0.08),
            0 2px 8px rgba(0, 0, 0, 0.04);
        transition: 
            transform 0.25s ease,
            box-shadow 0.25s ease;
    }

/* Hover effect */
    .metric-card:hover {
        transform: translateY(-6px);
        box-shadow: 
            0 18px 45px rgba(0, 0, 0, 0.12),
            0 6px 14px rgba(0, 0, 0, 0.08);
    }

/* ===== Status Colors ===== */
    .success {
        color: #2ecc71;
        font-weight: 600;
    }

    .warning {
        color: #f1c40f;
        font-weight: 600;
    }

    .danger {
        color: #e74c3c;
        font-weight: 600;
    }

/* ===== Buttons (Streamlit) ===== */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #06b6d4);
        color: white;
        border: none;
        border-radius: 14px;
            
        padding: 0.65rem 1.4rem;
        font-weight: 600;
        transition: all 0.95s ease;
        
        box-shadow:
            0 6px 16px rgba(59, 130, 246, 0.35),
            inset 0 1px 0 rgba(255, 255, 255, 0.25);
        
        transition:
            transform 0.18s ease,
            box-shadow 0.18s ease,
            filter 0.18s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        filter: brightness(1.05);
        box-shadow: 0 10px 24px rgba(59, 130, 246, 0.45);
    }
    
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3);
    }

/* ===== Expander ===== */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        font-weight: 600;
    }

/* ===== Scrollbar ===== */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(#56ccf2, #2f80ed);
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'bot_process' not in st.session_state:
    st.session_state.bot_process = None
if 'bot_output' not in st.session_state:
    st.session_state.bot_output = []

# Function to get data from Google Sheets
def get_google_sheets_data():
    """Get data from Google Sheets"""
    try:
        # Try environment variable first
        creds_json = os.getenv('GOOGLE_CREDS_JSON')
        if creds_json:
            creds_dict = json.loads(creds_json)
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)  # type: ignore
            gc = gspread.authorize(creds)  # type: ignore
        else:
            # Fallback to file-based credentials
            gc = gspread.service_account(filename='gcredentials.json')
        
        # Open sheet
        sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Recap Visit YOVI')
        sheet = gc.open(sheet_name).sheet1
        data = sheet.get_all_records()
        
        if not data:
            return pd.DataFrame(), "No data found"
        
        df = pd.DataFrame(data)
        return df, None
        
    except Exception as e:
        return None, f"Error loading data: {str(e)}"

# Function to start the bot in a separate thread
def start_bot():
    """Start the bot in a separate thread with better error handling"""
    try:
        # Only use bot.py
        bot_file = 'bot.py'
        if not os.path.exists(bot_file):
            st.error("bot.py file not found!")
            return False
        
        # Use the same Python executable as Streamlit
        python_executable = sys.executable
        
        # Set environment variables for proper encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        
        # Start the bot process with improved error handling
        process = subprocess.Popen(
            [python_executable, bot_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
            encoding='utf-8',
            errors='replace'  # Replace unicode errors instead of failing
        )
        
        st.session_state.bot_process = process
        st.session_state.bot_running = True
        st.session_state.bot_output = []  # Reset output
        
        # Start a thread to monitor the process and capture output
        def monitor_process():
            try:
                while True:
                    if process.poll() is not None:  # Process ended
                        st.session_state.bot_running = False
                        st.error("Bot process terminated unexpectedly!")
                        break
                    
                    # Read output line by line
                    if process.stdout:
                        line = process.stdout.readline()
                        if line:
                            # Clean the line and add to output
                            clean_line = line.strip()
                            if clean_line:
                                st.session_state.bot_output.append(clean_line)
                                # Keep only last 50 lines
                                if len(st.session_state.bot_output) > 50:
                                    st.session_state.bot_output = st.session_state.bot_output[-50:]
                        else:
                            time.sleep(0.1)
                    else:
                        time.sleep(0.1)
                        
            except Exception as e:
                st.error(f"Error monitoring bot process: {str(e)}")
                st.session_state.bot_running = False
        
        threading.Thread(target=monitor_process, daemon=True).start()
        
        return True
        
    except Exception as e:
        st.error(f"Error starting bot: {str(e)}")
        return False

# Function to stop the bot
def stop_bot():
    """Stop the bot"""
    try:
        if st.session_state.bot_process:
            st.session_state.bot_process.terminate()
            # Wait a bit for graceful shutdown
            try:
                st.session_state.bot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                st.session_state.bot_process.kill()  # Force kill if needed
            st.session_state.bot_process = None
        st.session_state.bot_running = False
        return True
    except Exception as e:
        st.error(f"Error stopping bot: {str(e)}")
        return False

# Function to check if the bot is running
def check_bot_status():
    """Check if bot is running"""
    if st.session_state.bot_process:
        return st.session_state.bot_process.poll() is None
    return False

def run_fetch_on_start():
    if not st.session_state.get("fetch_api_ran", False):
        try:
            # subprocess.Popen([sys.executable, "fetch_api.py"])
            st.session_state.fetch_api_ran = True
            st.success("✅ fetch_api.py has been triggered on app start")
        except Exception as e:
            st.error(f"❌ Failed to run fetch_api.py: {e}")

def schedule_daily_fetch():
    def fetch_loop():
        while True:
            now = datetime.now()
            
            # Run fetch_api.py every 3 hours
            if now.hour % 3 == 0 and now.minute == 0:
                try:
                    subprocess.Popen([sys.executable, "fetch_api.py"])
                    print(f"✅ fetch_api.py executed at {now.strftime('%H:%M')}")
                except Exception as e:
                    print(f"❌ Error running fetch_api.py: {e}")
                time.sleep(60)
            else:
                time.sleep(30)

    # Only start the thread once
    if not st.session_state.get("fetch_thread_started", False):
        thread = threading.Thread(target=fetch_loop, daemon=True)
        thread.start()
        st.session_state.fetch_thread_started = True

# Main dashboard
def main():
    run_fetch_on_start()
    schedule_daily_fetch()
    
    st.markdown('<h1 class="main-header">🤖 YOVI Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("🎛️ Bot Controls")
    
    # Environment variables status
    st.sidebar.subheader("🔧 Environment Status")
    env_vars = {
        'API_ID': os.getenv('API_ID'),
        'API_HASH': os.getenv('API_HASH'),
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'GOOGLE_SHEET_NAME': os.getenv('GOOGLE_SHEET_NAME'),
        'GOOGLE_CREDS_JSON': os.getenv('GOOGLE_CREDS_JSON')
    }
    
    for var_name, var_value in env_vars.items():
        if var_value:
            st.sidebar.success(f"✅ {var_name}")
        else:
            st.sidebar.error(f"❌ {var_name}")
    
    # Bot control buttons
    st.sidebar.subheader("🚀 Bot Controls")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("▶️ Start Bot", type="primary"):
            if start_bot():
                st.success("Bot started successfully!")
                st.rerun()
    
    with col2:
        if st.button("⏹️ Stop Bot"):
            if stop_bot():
                st.success("Bot stopped successfully!")
                st.rerun()
    
    # Check bot status once and use it consistently
    bot_is_running = check_bot_status()
    
    # Bot status
    st.sidebar.subheader("📊 Bot Status")
    if bot_is_running:
        st.sidebar.success("🟢 Bot is running")
    else:
        st.sidebar.error("🔴 Bot is stopped")
    
    # Main content area
    tab1, tab2 = st.tabs(["📊 Dashboard", "⚙️ Settings"])
    
    with tab1:
        # Dashboard header with inline refresh button
        col1, col2 = st.columns([4, 1])
        with col1:
            st.header("📊 Dashboard Overview")
        with col2:
            if st.button("🔄 Refresh", type="secondary"):
                st.rerun()
        
        # Status cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_text = "🟢 Running" if bot_is_running else "🔴 Stopped"
            status_class = "success" if bot_is_running else "danger"
            st.markdown(f"""
            <div class="metric-card">
                <h3>Bot Status</h3>
                <p class="{status_class}">{status_text}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Get data count
            df, error = get_google_sheets_data()
            if df is not None and not df.empty:
                data_count = len(df)
            else:
                data_count = 0
            
            st.markdown(f"""
            <div class="metric-card">
                <h3>Total Records</h3>
                <p>{data_count}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <h3>Last Update</h3>
                <p>{}</p>
            </div>
            """.format(format_timestamp()), unsafe_allow_html=True)
        
        with col4:
            # Count today's records
            today_count = 0
            if df is not None and not df.empty and 'Timestamp' in df.columns:
                try:
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    today = get_current_time().date()
                    today_count = len(df[df['Timestamp'].dt.date == today])
                except:
                    today_count = 0
            
            st.markdown(f"""
            <div class="metric-card">
                <h3>Today's Records</h3>
                <p>{today_count}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Recent activity
        st.subheader("🕒 Recent Activity")
        if bot_is_running:
            st.info("Bot is actively monitoring for new messages...")
        else:
            st.warning("Bot is not running. Start the bot to begin monitoring.")
        
        # Live bot output
        st.subheader("📝 Live Bot Output")
        if st.session_state.bot_output:
            # Create a container for the output
            output_container = st.container()
            with output_container:
                for line in st.session_state.bot_output[-20:]:  # Show last 20 lines
                    st.text(line)
        else:
            st.info("No bot output yet. Start the bot to see live logs.")
        
        # Log viewer (from file)
        st.subheader("📄 Log File")
        if os.path.exists('bot.log'):
            with open('bot.log', 'r', encoding='utf-8', errors='replace') as f:
                logs = f.readlines()[-10:]  # Last 10 lines
                for log in logs:
                    st.text(log.strip())
        else:
            st.warning("No log file found")

    with tab2:
        st.header("⚙️ Settings")
        
        st.subheader("🔧 Configuration")
        
        # Environment variables editor
        st.subheader("Environment Variables")
        st.info("Edit your .env file to modify these settings")
        
        # Display current settings (masked)
        settings = {
            "API_ID": os.getenv('API_ID', 'Not set'),
            "API_HASH": os.getenv('API_HASH', 'Not set')[:10] + "..." if os.getenv('API_HASH') else 'Not set',
            "BOT_TOKEN": os.getenv('BOT_TOKEN', 'Not set')[:10] + "..." if os.getenv('BOT_TOKEN') else 'Not set',
            "GOOGLE_SHEET_NAME": os.getenv('GOOGLE_SHEET_NAME', 'Not set'),
            "GOOGLE_CREDS_JSON": os.getenv('GOOGLE_CREDS_JSON', 'Not set')
        }
        
        for key, value in settings.items():
            st.text_input(key, value, disabled=True)
        
        # System information
        st.subheader("💻 System Information")
        try:
            python_version = subprocess.check_output(['python', '--version']).decode().strip()
            st.text(f"Python Version: {python_version}")
        except:
            st.text("Python Version: Unable to determine")
        st.text(f"Streamlit Version: {st.__version__}")
        st.text(f"Working Directory: {os.getcwd()}")

    # Check if bot process has terminated
    if st.session_state.bot_process:
        if st.session_state.bot_process.poll() is not None:
            st.session_state.bot_running = False
            st.error("Bot process has terminated!")

if __name__ == "__main__":
    main()