import base64
import io
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ---------------------------------------------------------
# PAGE CONFIG & SQUADRON 153 DESIGN LANGUAGE
# ---------------------------------------------------------
st.set_page_config(page_title="Squadron 153 Request Portal", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #002244;
        color: #FFFFFF;
    }
    .main-header {
        background-color: #001122;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #003366;
        margin-bottom: 2rem;
    }
    .main-header h1 { color: #FFFFFF !important; font-weight: 800; margin: 0; }
    .main-header h3 { color: #FFCC00 !important; margin-top: 5px; }
    
    label, .stMarkdown, p, span, h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
    }
    
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {
        background-color: #001122 !important;
        color: #FFFFFF !important;
        border: 1px solid #003366 !important;
    }
    
    .stButton>button {
        background-color: #003366 !important;
        color: #FFCC00 !important;
        font-weight: bold !important;
        border: 1px solid #FFCC00 !important;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #FFCC00 !important;
        color: #002244 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>✈️ CIVIL AIR PATROL</h1>
        <h3>Squadron 153 Cadet Request & Testing Portal</h3>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# GOOGLE DRIVE & SHEETS INTEGRATION
# ---------------------------------------------------------
def get_drive_service():
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            creds_info, 
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"Google Drive auth failed: {e}")
        return None

def upload_file_to_drive(uploaded_file, folder_id):
    try:
        service = get_drive_service()
        if not service:
            return None
        file_metadata = {'name': uploaded_file.name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getvalue()), mimetype=uploaded_file.type, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return None

@st.cache_data(ttl=300)
def load_cadet_progress():
    sheet_id = "1dUUf4xSWFX8KJoJPhqXd2glYmVGjVIZplvrToVd_Uyg"
    gid = "1661632143"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url, skiprows=4)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_schedule():
    sheet_id = "17wdWuOFBFyR507_vBITsTkI8il7k-1gDjLLPtNcCzt8"
    gid = "420770302"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame([
            {"Date": "1st Wednesday", "UOD": "ABU / OCP", "Focus": "Leadership / Drill"},
            {"Date": "2nd Wednesday", "UOD": "Blues (Class B)", "Focus": "AE / PRBs"},
            {"Date": "3rd Wednesday", "UOD": "ABU / OCP", "Focus": "Character / Safety"},
            {"Date": "4th Wednesday", "UOD": "PT Uniform", "Focus": "CPFT / Testing"},
            {"Date": "5th Wednesday", "UOD": "Civilian / Activity", "Focus": "Special Event"}
        ])

@st.cache_data(ttl=60)
def load_submitted_backend():
    sheet_id = "1aWN5BSWlMHYwBzrmijnlBEhP4ZEU9sJjx3VLIxqHnTE"
    gid = "0"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

progress_df = load_cadet_progress()
schedule_df = load_schedule()
backend_df = load_submitted_backend()

# ---------------------------------------------------------
# TABS SETUP
# ---------------------------------------------------------
tab_req, tab_dashboard, tab_progress, tab_sched = st.tabs([
    "📝 Submit Request", 
    "📈 Live Request Dashboard",
    "📊 Cadet Progress Report", 
    "📅 Wednesday Schedule & UOD"
])

# ---------------------------------------------------------
# HELPER: CHECK IF DRILL TEST IS ALLOWED
# ---------------------------------------------------------
def is_drill_test_allowed(target_ach_str):
    target = str(target_ach_str).lower()
    
    # Allowed specifically for Wright Brothers Award (Achievement 3)
    if "wright" in target or "achievement 3" in target:
        return True
        
    # Block for Mitchell, Earhart, Eaker, Spaatz milestone awards
    if any(m in target for m in ["mitchell", "earhart", "eaker", "spaatz"]):
        return False
        
    # Check for Achievement 9 or higher
    for i in range(9, 20):
        if f"achievement {i}" in target:
            return False
            
    return True

# ---------------------------------------------------------
# TAB 1: SUBMIT REQUEST
# ---------------------------------------------------------
with tab_req:
    st.markdown("### Cadet Request Form")
    
    if not progress_df.empty and "Cadet Name" in progress_df.columns:
        cadet_names = sorted([n for n in progress_df["Cadet Name"].dropna().unique() if str(n).strip()])
        selected_cadet = st.selectbox("Select Your Name:*", ["-- Select Name --"] + cadet_names)
        
        if selected_cadet != "-- Select Name --":
            cadet_row = progress_df[progress_df["Cadet Name"] == selected_cadet].iloc[0]
            working_ach = str(cadet_row.get("Working Towards Achievement No.", "N/A"))
            
            # Auto-populated parameters
            col1, col2, col3 = st.columns(3)
            with col1:
                cap_id = st.text_input("CAP ID:", value=str(cadet_row.get("CAP ID", "")))
            with col2:
                grade = st.text_input("Current Grade:", value=str(cadet_row.get("Grade", "")))
            with col3:
                flight = st.selectbox("Flight:", ["Alpha", "Bravo", "Charlie", "Delta", "Staff", "HQ"])

            st.info(f"**Cadet:** {selected_cadet} | **Target Achievement:** {working_ach}")

            # Define full original options list
            all_request_types = [
                "Drill Test", 
                "Milestone Drill Test", 
                "Staff Duty Analysis (SDA) - Written Report", 
                "Staff Duty Analysis (SDA) - Oral Presentation", 
                "Promotion Review Board (PRB)", 
                "Staff Review Board", 
                "CPFT Testing", 
                "Feedback Request", 
                "Form 60-80 / PT Waiver"
            ]

            # Filter out Drill Test if Achievement 9+ or Non-Wright Milestone Award
            drill_allowed = is_drill_test_allowed(working_ach)
            if not drill_allowed:
                available_types = [r for r in all_request_types if "Drill" not in r]
                st.caption("ℹ️ *Drill Tests are not applicable for Achievement 9+ or Milestone Awards (except Wright Brothers).*")
            else:
                available_types = all_request_types

            req_type = st.selectbox("Request Type:*", available_types)
            
            # Extract Cadet Progress Fields
            lead_val = str(cadet_row.get("Leadership", "")).strip()
            ae_val = str(cadet_row.get("Aerospace (AE) No. Completed", "0")).strip()
            
            prereq_valid = True
            error_msgs = []

            # Rule Crosschecking Logic
            if "Drill Test" in req_type:
                if not lead_val or lead_val in ["None", "nan"] or ae_val in ["0", "None", "nan", ""]:
                    prereq_valid = False
                    error_msgs.append("To request a **Drill Test**, you must have completed **Learn to Lead** and **AE Dimensions**.")
            
            elif "Staff Duty Analysis" in req_type:
                if not lead_val or lead_val in ["None", "nan"] or ae_val in ["0", "None", "nan", ""]:
                    prereq_valid = False
                    error_msgs.append("To request an **SDA**, your **Learn to Lead** and **AE Dimensions** must be completed.")

            st.markdown("#### Select Target Wednesday Date")
            target_date = st.date_input("Target Meeting Date:", value=datetime.now().date())

            if req_type == "Promotion Review Board (PRB)":
                if "Achievement 4" in working_ach or any(f"Achievement {i}" in working_ach for i in range(5, 17)):
                    st.warning("⚠️ **Reminder:** PRB Requests for Achievement 4+ must take place on a **Blues Night**.")

            if req_type == "CPFT Testing":
                if target_date.weekday() != 2:
                    prereq_valid = False
                    error_msgs.append("CPFT Testing must take place on a **Wednesday**.")

            if not prereq_valid:
                for msg in error_msgs:
                    st.error(f"❌ **Prerequisite Alert:** {msg}")

            with st.form("cadet_request_form", clear_on_submit=True):
                st.markdown("#### Document Uploads (Required for SDA)")
                uploaded_file = st.file_uploader("Upload SDA Report / Reference Documents:", type=["pdf", "docx", "doc", "jpg", "png"])
                comments = st.text_area("Additional Notes / Details for Staff:")
                
                submit_button = st.form_submit_button("Submit Request")
                if submit_button:
                    if not prereq_valid:
                        st.error("Please resolve the prerequisite conflicts listed above before submitting.")
                    else:
                        file_link = ""
                        if uploaded_file is not None:
                            folder_id = "1aWN5BSWlMHYwBzrmijnlBEhP4ZEU9sJjx3VLIxqHnTE"
                            with st.spinner("Uploading document to Google Drive..."):
                                file_link = upload_file_to_drive(uploaded_file, folder_id)

                        st.success(f"Request for {req_type} successfully submitted for {selected_cadet}!")
                        if file_link:
                            st.markdown(f"📄 **Uploaded Document:** [View in Drive]({file_link})")
    else:
        st.warning("Unable to fetch Cadet Progress data. Please check sheet connectivity.")

# ---------------------------------------------------------
# TAB 2: LIVE REQUEST DASHBOARD
# ---------------------------------------------------------
with tab_dashboard:
    st.markdown("### 📈 Live Submitted Requests Dashboard")
    st.caption("Synchronized with [Promotion Form Request Backend Sheet](https://docs.google.com/spreadsheets/d/1aWN5BSWlMHYwBzrmijnlBEhP4ZEU9sJjx3VLIxqHnTE/edit?gid=0#gid=0)")
    
    if not backend_df.empty:
        st.dataframe(backend_df, use_container_width=True, hide_index=True)
    else:
        st.info("No request records currently logged.")

# ---------------------------------------------------------
# TAB 3: CADET PROGRESS REPORT INTEGRATION
# ---------------------------------------------------------
with tab_progress:
    st.markdown("### 📊 Cadet Progress Lookup")
    st.caption("Live data from [SQ 153 Cadet Progress Sheet](https://docs.google.com/spreadsheets/d/1dUUf4xSWFX8KJoJPhqXd2glYmVGjVIZplvrToVd_Uyg/edit)")
    
    if not progress_df.empty:
        search_query = st.text_input("🔍 Search Cadet Name:")
        filtered_progress = progress_df.copy()
        if search_query:
            filtered_progress = filtered_progress[filtered_progress["Cadet Name"].str.contains(search_query, case=False, na=False)]
        st.dataframe(filtered_progress, use_container_width=True, hide_index=True)
    else:
        st.info("No progress report data available.")

# ---------------------------------------------------------
# TAB 4: WEDNESDAY SCHEDULE & UOD
# ---------------------------------------------------------
with tab_sched:
    st.markdown("### 📅 Squadron Meeting Schedule & Uniform of the Day (UOD)")
    st.caption("Reference this schedule from [153 Training Schedule Sheet](https://docs.google.com/spreadsheets/d/17wdWuOFBFyR507_vBITsTkI8il7k-1gDjLLPtNcCzt8/edit)")
    
    if not schedule_df.empty:
        st.dataframe(schedule_df, use_container_width=True, hide_index=True)
    else:
        st.info("No schedule data loaded.")
