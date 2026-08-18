import base64
import io
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ---------------------------------------------------------
# PAGE CONFIG & BASE CSS
# ---------------------------------------------------------
st.set_page_config(page_title="Squadron 153 Request Portal", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: url('https://raw.githubusercontent.com/tylermungcal/Squadron-Form/main/IMG_4502.jpeg') no-repeat center center fixed;
        background-size: cover;
    }
    
    /* Completely hide active tab blue underline / highlight border */
    [data-baseweb="tab-highlight"],
    [data-baseweb="tab-border"],
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"] {
        background-color: transparent !important;
        background: none !important;
        border-bottom: none !important;
        display: none !important;
    }
    
    /* SHRUNK TITLE BANNER CARD */
    .title-card {
        background-color: #00308f !important;
        padding: 15px 25px !important;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        margin-bottom: 20px;
    }
    .title-card h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
        font-size: 2rem !important;
    }
    
    /* MAIN FORM CARD CONTAINING ALL INPUTS */
    .form-card {
        background-color: #00308f !important;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        margin-bottom: 25px;
    }
    
    /* ALL FIELD LABELS AND HEADINGS IN WHITE */
    .form-card label, 
    .form-card label p,
    .form-card p,
    .form-card h2, .form-card h3,
    div[data-testid="stWidgetLabel"] p,
    div[data-testid="stWidgetLabel"] label,
    label[data-testid="stWidgetLabel"] * {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* File Uploader Container Styling */
    div[data-testid="stFileUploader"] section {
        border: 2px dashed #ffffff !important;
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# GOOGLE DRIVE API HELPER
# ---------------------------------------------------------
def upload_to_drive(uploaded_file):
    creds_data = st.secrets["google_drive"]

    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )

    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": uploaded_file.name,
        "parents": [creds_data["folder_id"]],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(uploaded_file.getvalue()),
        mimetype=uploaded_file.type or "application/octet-stream",
        resumable=True,
    )

    file = (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,
            supportsTeamDrives=True,
        )
        .execute()
    )

    return file.get("webViewLink")

# ---------------------------------------------------------
# TRAINING SCHEDULE & VALIDATION HELPERS
# ---------------------------------------------------------
TRAINING_SCHEDULE_DATES = [
    date(2026, 8, 26),
    date(2026, 9, 2),
    date(2026, 9, 9),
    date(2026, 9, 16),
    date(2026, 9, 23),
    date(2026, 9, 30),
    date(2026, 10, 7),
    date(2026, 10, 14),
    date(2026, 10, 21),
    date(2026, 11, 4),
    date(2026, 11, 11),
    date(2026, 12, 2),
    date(2026, 12, 9)
]

def is_valid_training_wednesday(selected_date: date) -> bool:
    if selected_date == date(2026, 10, 28):
        return False
    return selected_date.weekday() == 2 and selected_date in TRAINING_SCHEDULE_DATES

def is_submitted_before_friday_deadline(selected_date: date) -> bool:
    days_back_to_friday = (selected_date.weekday() - 4) % 7
    if days_back_to_friday == 0:
        days_back_to_friday = 7
    
    friday_deadline_date = selected_date - timedelta(days=days_back_to_friday)
    friday_deadline_dt = datetime.combine(friday_deadline_date, datetime.max.time())
    
    return datetime.now() <= friday_deadline_dt

# ---------------------------------------------------------
# CONSTANTS & SESSION STATE
# ---------------------------------------------------------
DASHBOARD_PIN = "1530"

drill_list = [
    "Achievement 1", "Achievement 2", "Achievement 3", "Wright Brothers Award", 
    "Achievement 4", "Achievement 5", "Achievement 6", "Achievement 7", "Achievement 8"
]
milestone_list = [
    "Wright Brothers Award", "Mitchell Aerospace Exam", "Mitchell Leadership Exam", 
    "Amelia Earhart Award", "Ira C. Eaker Award", "General Carl A. Spaatz Award"
]
essay_list = ["Achievement 8", "Ira C. Eaker Award", "General Carl A. Spaatz Award"]
sda_list = [
    "Achievement 9", "Achievement 10", "Achievement 11", "Achievement 12", 
    "Achievement 13", "Achievement 14", "Achievement 15", "Achievement 16"
]
full_list = drill_list + sda_list + [
    "Billy Mitchell Award", "Amelia Earhart Award", "Ira C. Eaker Award", "General Carl A. Spaatz Award"
]

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "form_submitted_success" not in st.session_state:
    st.session_state.form_submitted_success = False

if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if "dashboard_authenticated" not in st.session_state:
    st.session_state.dashboard_authenticated = False

v = st.session_state.form_version

# Create Tabs
tab_form, tab_dashboard = st.tabs(["📝 Submit Request", "📊 Live Request Dashboard"])

# ---------------------------------------------------------
# TAB 1: SUBMIT REQUEST FORM
# ---------------------------------------------------------
with tab_form:
    if st.session_state.form_submitted_success:
        st.success("✅ Submitted successfully! The form has been reset for a new entry.")
        st.session_state.form_submitted_success = False

    # Shrunk Header Banner
    st.markdown('''
        <div class="title-card">
            <h1 style="text-align: center;">Squadron 153 Promotion Form Requests</h1>
        </div>
    ''', unsafe_allow_html=True)

    # Main Form Container (Single Blue Card wrapping all fields)
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    
    email = st.text_input("Email Address *", key=f"email_{v}")
    flight = st.selectbox(
        "Flight *", 
        ["-- Select --", "Line Staff", "Support Staff", "Alpha Flight", "Bravo Flight", "Charlie Flight", "CTF"], 
        key=f"flight_{v}"
    )
    first_name = st.text_input("First Name *", key=f"first_name_{v}")
    last_name = st.text_input("Last Name *", key=f"last_name_{v}")
    
    request_type = st.selectbox(
        "Requesting a... *", 
        [
            "-- Select --", "Drill Test", "PRB", "CPFT (4th Wednesday)", 
            "Milestone Exam", "Essay Submission", "Technical Writing Submission (SDA)", "Specialty Exam"
        ],
        key=f"request_type_{v}"
    )

    achievement = None
    has_achievement_field = False
    if request_type == "Drill Test":
        has_achievement_field = True
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + drill_list, key=f"achievement_{v}")
    elif request_type == "Milestone Exam":
        has_achievement_field = True
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + milestone_list, key=f"achievement_{v}")
    elif request_type == "Essay Submission":
        has_achievement_field = True
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + essay_list, key=f"achievement_{v}")
    elif request_type == "Technical Writing Submission (SDA)":
        has_achievement_field = True
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + sda_list, key=f"achievement_{v}")
    elif request_type == "PRB":
        has_achievement_field = True
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + full_list, key=f"achievement_{v}")

    specialty_exam = None
    if request_type == "Specialty Exam":
        specialty_exam = st.selectbox("Exam Requested *", ["-- Select Exam --", "ICUT", "Other"], key=f"specialty_exam_{v}")

    meeting_date = st.date_input(
        "Requested Meeting Date *", 
        value=date.today(), 
        min_value=date.today(), 
        key=f"meeting_date_{v}"
    )

    uploaded_file = None
    if request_type in ["PRB", "Essay Submission", "Technical Writing Submission (SDA)", "Specialty Exam"]:
        uploaded_file = st.file_uploader(
            "Upload Required Document / CAPF Form *", 
            type=["pdf", "png", "jpg", "docx"], 
            key=f"uploaded_file_{v}"
        )

    # Validation Calculations
    valid_wednesday = is_valid_training_wednesday(meeting_date) if meeting_date else False
    valid_deadline = is_submitted_before_friday_deadline(meeting_date) if meeting_date else False

    # Required Field Validation Checks
    is_invalid_email = st.session_state.submitted and not email
    is_invalid_flight = st.session_state.submitted and (flight == "-- Select --")
    is_invalid_fname = st.session_state.submitted and not first_name
    is_invalid_lname = st.session_state.submitted and not last_name
    is_invalid_req = st.session_state.submitted and (request_type == "-- Select --")
    is_invalid_achieve = st.session_state.submitted and has_achievement_field and (not achievement or achievement == "-- Select --")
    is_invalid_date = st.session_state.submitted and (not valid_wednesday or not valid_deadline)

    # Dynamic Red Border Highlights
    red_css = ""
    if is_invalid_email:
        red_css += 'div[data-testid="stTextInput"]:has(input[aria-label="Email Address *"]) input { border: 2px solid #ff4b4b !important; background-color: #ffe6e6 !important; }\n'
    if is_invalid_flight:
        red_css += 'div[data-testid="stSelectbox"]:has(label[aria-label="Flight *"]) div[data-baseweb="select"] > div { border: 2px solid #ff4b4b !important; background-color: #ffe6e6 !important; }\n'
    if is_invalid_fname:
        red_css += 'div[data-testid="stTextInput"]:has(input[aria-label="First Name *"]) input { border: 2px solid #ff4b4b !important; background-color: #ffe6e6 !important; }\n'
    if is_invalid_lname:
        red_css += 'div[data-testid="stTextInput"]:has(input[aria-label="Last Name *"]) input { border: 2px solid #ff4b4b !important; background-color: #ffe6e6 !important; }\n'
    if is_invalid_req:
        red_css += 'div[data-testid="stSelectbox"]:has(label[aria-label="Requesting a... *"]) div[data-baseweb="select"] > div { border: 2px solid #ff4b4b !important; background-color: #ffe6e6 !important; }\n'
    if is_invalid_achieve:
        red_css += 'div[data-testid="stSelectbox"]:has(label[aria-label*="achievement"]) div[data-baseweb="select"] > div { border: 2px solid #ff4b4b !important; background-color: #ffe6e6 !important; }\n'
    if is_invalid_date:
        red_css += 'div[data-testid="stDateInput"] input { border: 2px solid #ff4b4b !important; background-color: #ffe6e6 !important; }\n'

    if red_css:
        st.markdown(f"<style>{red_css}</style>", unsafe_allow_html=True)

    if st.button("Submit Request"):
        st.session_state.submitted = True
        
        if (not email or flight == "-- Select --" or not first_name or not last_name 
            or request_type == "-- Select --" or (has_achievement_field and (not achievement or achievement == "-- Select --"))):
            st.error("⚠️ Please fill in all required fields highlighted in red.")
        elif not valid_wednesday:
            st.error("⚠️ Selected date must be a valid Wednesday meeting!")
        elif not valid_deadline:
            st.error("⚠️ Request deadline passed! Forms must be submitted by Friday 23:59 prior to the requested Wednesday.")
        else:
            file_url = ""
            
            # Upload to Drive
            if uploaded_file is not None:
                with st.spinner("Uploading file to Google Drive..."):
                    try:
                        file_url = upload_to_drive(uploaded_file)
                    except Exception as e:
                        st.error(f"⚠️ Drive API Upload Error: {e}")
                        st.exception(e)

            WEBHOOK_URL = "https://script.google.com/macros/s/AKfycby_iDEd9a3hmJQyLhKuP9833KirbBK19Mki2K43eNOSs6iVLYDZq2FEw66V06Bb65uP6g/exec"
            
            payload = {
                "email": email,
                "flight": flight,
                "firstName": first_name,
                "lastName": last_name,
                "requestType": request_type,
                "achievement": achievement if achievement else "",
                "specialtyExam": specialty_exam if specialty_exam else "",
                "meetingDate": str(meeting_date) if meeting_date else "",
                "fileUrl": file_url
            }
            
            try:
                with st.spinner("Submitting request..."):
                    response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
                
                if "Error" in response.text or "<!DOCTYPE html>" in response.text:
                    st.error("⚠️ Submission failed! Google Script returned an authorization or execution error.")
                else:
                    st.session_state.form_submitted_success = True
                    st.session_state.submitted = False
                    st.session_state.form_version += 1
                    st.rerun()
            except Exception as e:
                st.error(f"Error submitting form: {e}")
                    
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: LIVE REQUEST DASHBOARD (PIN PROTECTED)
# ---------------------------------------------------------
with tab_dashboard:
    st.markdown("## Live Squadron Requests")
    
    if not st.session_state.dashboard_authenticated:
        pin_input = st.text_input("Enter Staff PIN to Access Dashboard", type="password", key="pin_input_field")
        if st.button("Unlock Dashboard", key="unlock_btn"):
            if pin_input == DASHBOARD_PIN:
                st.session_state.dashboard_authenticated = True
                st.rerun()
            else:
                st.error("🔒 Incorrect PIN code. Access denied.")
    else:
        if st.button("🔒 Lock Dashboard", key="lock_btn"):
            st.session_state.dashboard_authenticated = False
            st.rerun()

        SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1aWN5BSWlMHYwBzrmijnlBEhP4ZEU9sJjx3VLIxqHnTE/gviz/tq?tqx=out:csv&gid=0"
        
        try:
            df = pd.read_csv(SHEET_CSV_URL)
            
            if "Status" not in df.columns:
                df["Status"] = "Pending"

            if "Document / File Link" in df.columns:
                df["Document / File Link"] = df["Document / File Link"].fillna("").astype(str)
                df["Document / File Link"] = df["Document / File Link"].apply(
                    lambda x: x if x.startswith("http") else None
                )

            st.data_editor(
                df,
                column_config={
                    "Status": st.column_config.SelectboxColumn(
                        "Request Status",
                        options=["Pending", "Approved", "In Progress", "Completed", "Denied"],
                        required=True,
                    ),
                    "Document / File Link": st.column_config.LinkColumn(
                        "Document / File Link",
                        display_text="View Document"
                    )
                },
                use_container_width=True,
                num_rows="fixed"
            )
        except Exception:
            st.info("No responses recorded yet or Google Sheet sharing setting needs 'Anyone with link can view'.")
