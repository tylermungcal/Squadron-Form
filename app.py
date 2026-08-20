import base64
import io
import re
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ---------------------------------------------------------
# PAGE CONFIG & STYLING
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
# HELPER FUNCTIONS FOR GRADE, MILESTONE, & CAPF 60-90 MAPPING
# ---------------------------------------------------------
def infer_current_grade(target_ach_str):
    """Determines current rank based on target achievement."""
    s = str(target_ach_str).lower().strip()
    
    if "achievement 1" in s: return "C/Amn"
    if "achievement 2" in s or "curry" in s: return "C/A1C"
    if "achievement 3" in s or "wright" in s: return "C/SrA"
    if "achievement 4" in s or "arnold" in s: return "C/SSgt"
    if "achievement 5" in s or "fechet" in s: return "C/TSgt"
    if "achievement 6" in s or "lemay" in s: return "C/MSgt"
    if "achievement 7" in s or "rikenbacker" in s: return "C/SMSgt"
    if "achievement 8" in s or "mitchell" in s: return "C/CMSgt"
    if "achievement 9" in s or "earhart" in s: return "C/2d Lt"
    if "achievement 10" in s: return "C/2d Lt"
    if "achievement 11" in s: return "C/1st Lt"
    if "achievement 12" in s or "eaker" in s: return "C/1st Lt"
    if "achievement 13" in s or "spaatz" in s: return "C/Capt"
    if "achievement 14" in s or "achievement 15" in s or "achievement 16" in s: return "C/Maj"
    
    return "Cadet"

def get_capf60_90_info(grade_str):
    """Returns Phase description, form name, and URL based on grade."""
    g = grade_str.upper().strip()
    
    # Phase I: C/AB to C/SrA
    if g in ["C/AB", "C/AMN", "C/A1C", "C/SRA", "CADET"]:
        return {
            "phase": "Phase I (The Learning Phase)",
            "form_name": "CAPF 60-91 (Cadet Leadership Feedback - Phase I)",
            "url": "https://www.gocivilairpatrol.com/media/cms/CAPF_6091_25B1D25BA2960.pdf"
        }
    # Phase II: C/SSgt to C/CMSgt
    elif g in ["C/SSGT", "C/TSGT", "C/MSGT", "C/SMSGT", "C/CMSGT"]:
        return {
            "phase": "Phase II (The Leadership Phase)",
            "form_name": "CAPF 60-92 (Cadet Leadership Feedback - Phase II)",
            "url": "https://www.gocivilairpatrol.com/media/cms/CAPF_6092_F88D00D0FB843.pdf"
        }
    # Phase III: C/2d Lt to C/Capt
    elif g in ["C/2D LT", "C/1ST LT", "C/CAPT"]:
        return {
            "phase": "Phase III (The Command Phase)",
            "form_name": "CAPF 60-93 (Cadet Leadership Feedback - Phase III)",
            "url": "https://www.gocivilairpatrol.com/media/cms/CAPF_6093_A876BCE22180A.pdf"
        }
    # Phase IV: C/Maj to C/Col
    elif g in ["C/MAJ", "C/LTC", "C/COL"]:
        return {
            "phase": "Phase IV (The Executive Phase)",
            "form_name": "CAPF 60-94 (Cadet Leadership Feedback - Phase IV)",
            "url": "https://www.gocivilairpatrol.com/media/cms/CAPF_6094_55278EDDEBC4D.pdf"
        }
    
    return {
        "phase": "Phase I (The Learning Phase)",
        "form_name": "CAPF 60-91 (Cadet Leadership Feedback - Phase I)",
        "url": "https://www.gocivilairpatrol.com/media/cms/CAPF_6091_25B1D25BA2960.pdf"
    }

def detect_milestone_exam(target_ach_str):
    s = str(target_ach_str).lower().strip()
    if "achievement 3" in s or "wright" in s:
        return "Wright Brothers Award Exam"
    elif "achievement 8" in s or "mitchell" in s:
        return "Billy Mitchell Award Exam"
    elif "achievement 11" in s or "earhart" in s:
        return "Amelia Earhart Award Exam"
    elif "achievement 13" in s or "eaker" in s:
        return "Ira C. Eaker Award Exam"
    elif "spaatz" in s:
        return "General Carl A. Spaatz Award Exam"
    return "General Milestone Exam"

def is_drill_test_allowed(target_ach_str):
    target = str(target_ach_str).lower()
    if "wright" in target or "achievement 3" in target:
        return True
    if any(m in target for m in ["mitchell", "earhart", "eaker", "spaatz"]):
        return False
    for i in range(9, 20):
        if f"achievement {i}" in target:
            return False
    return True

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
            
            raw_cap_id = str(cadet_row.get("CAP ID", "")).replace(".0", "").strip()
            inferred_grade = infer_current_grade(working_ach)

            col1, col2, col3 = st.columns(3)
            with col1:
                cap_id_input = st.text_input("CAP ID (6 Digits):*", value=raw_cap_id)
            with col2:
                grade_input = st.text_input("Current Grade (Auto-Inferred):*", value=inferred_grade)
            with col3:
                flight_input = st.selectbox("Flight:*", ["Alpha", "Bravo", "Charlie", "CTF", "Support", "Line"])

            st.info(f"**Cadet:** {selected_cadet} | **Target Achievement:** {working_ach}")

            all_request_types = [
                "Drill Test", 
                "PRB", 
                "4th Wednesday CPFT", 
                "Milestone Exam", 
                "Technical Writing Submission (SDA)", 
                "Essay Submission", 
                "Specialty Exam"
            ]

            drill_allowed = is_drill_test_allowed(working_ach)
            if not drill_allowed:
                available_types = [r for r in all_request_types if r != "Drill Test"]
                st.caption("ℹ️ *Drill Tests are not applicable for Achievement 9+ or Milestone Awards (except Wright Brothers).*")
            else:
                available_types = all_request_types

            req_type = st.selectbox("Request Type:*", available_types)
            
            selected_exam_name = ""
            if req_type == "Milestone Exam":
                detected_exam = detect_milestone_exam(working_ach)
                exam_options = [
                    "Wright Brothers Award Exam", 
                    "Billy Mitchell Award Exam", 
                    "Amelia Earhart Award Exam", 
                    "Ira C. Eaker Award Exam", 
                    "General Carl A. Spaatz Award Exam"
                ]
                default_idx = exam_options.index(detected_exam) if detected_exam in exam_options else 0
                selected_exam_name = st.selectbox("Select Target Milestone Exam:*", exam_options, index=default_idx)

            # Rule Crosschecking Logic
            lead_val = str(cadet_row.get("Leadership", "")).strip()
            ae_val = str(cadet_row.get("Aerospace (AE) No. Completed", "0")).strip()
            
            prereq_valid = True
            error_msgs = []

            # CAP ID Validation
            clean_cap_id = re.sub(r"\D", "", cap_id_input)
            if len(clean_cap_id) != 6:
                prereq_valid = False
                error_msgs.append("CAP ID must be exactly **6 digits** (no letters or extra symbols).")

            if req_type == "Drill Test":
                if not lead_val or lead_val in ["None", "nan"] or ae_val in ["0", "None", "nan", ""]:
                    prereq_valid = False
                    error_msgs.append("To request a **Drill Test**, you must have completed **Learn to Lead** and **AE Dimensions**.")
            
            elif req_type in ["Technical Writing Submission (SDA)", "Essay Submission"]:
                if not lead_val or lead_val in ["None", "nan"] or ae_val in ["0", "None", "nan", ""]:
                    prereq_valid = False
                    error_msgs.append("To request an **SDA / Essay Submission**, your **Learn to Lead** and **AE Dimensions** must be completed.")

            st.markdown("#### Select Target Wednesday Date")
            target_date = st.date_input("Target Meeting Date:", value=datetime.now().date())

            if req_type == "PRB":
                if "Achievement 4" in working_ach or any(f"Achievement {i}" in working_ach for i in range(5, 17)):
                    st.warning("⚠️ **Reminder:** PRB Requests for Achievement 4+ must take place on a **Blues Night**.")

            if req_type == "4th Wednesday CPFT":
                if target_date.weekday() != 2:
                    prereq_valid = False
                    error_msgs.append("CPFT Testing must take place on a **Wednesday**.")

            if not prereq_valid:
                for msg in error_msgs:
                    st.error(f"❌ **Validation / Prerequisite Alert:** {msg}")

            with st.form("cadet_request_form", clear_on_submit=True):
                st.markdown("#### Document Uploads")
                
                # Dynamic CAPF 60-90 routing for PRB requests
                if req_type == "PRB":
                    prb_info = get_capf60_90_info(grade_input)
                    st.markdown(f"**Required Form:** Submit your **[{prb_info['form_name']}]({prb_info['url']})** for **{prb_info['phase']}** ({grade_input}).")
                    uploaded_file = st.file_uploader(f"Upload completed {prb_info['form_name'].split(' ')[0]} PDF/Image:", type=["pdf", "docx", "doc", "jpg", "png"])
                else:
                    uploaded_file = st.file_uploader("Upload SDA Report, Essay, or Reference Documents (if applicable):", type=["pdf", "docx", "doc", "jpg", "png"])

                comments = st.text_area("Additional Notes / Details for Staff:")
                
                submit_button = st.form_submit_button("Submit Request")
                if submit_button:
                    if not prereq_valid:
                        st.error("Please resolve the prerequisite and CAP ID errors listed above before submitting.")
                    else:
                        file_link = ""
                        if uploaded_file is not None:
                            folder_id = "1aWN5BSWlMHYwBzrmijnlBEhP4ZEU9sJjx3VLIxqHnTE"
                            with st.spinner("Uploading document to Google Drive..."):
                                file_link = upload_file_to_drive(uploaded_file, folder_id)

                        submission_summary = f"Request for **{req_type}**"
                        if selected_exam_name:
                            submission_summary += f" ({selected_exam_name})"
                            
                        st.success(f"{submission_summary} successfully submitted for {selected_cadet} (CAP ID: {clean_cap_id}, {grade_input}, {flight_input} Flight)!")
                        if file_link:
                            st.markdown(f"📄 **Uploaded Document:** [View in Drive]({file_link})")
    else:
        st.warning("Unable to fetch Cadet Progress data. Please check sheet connectivity.")

# ---------------------------------------------------------
# TAB 2: LIVE REQUEST DASHBOARD
# ---------------------------------------------------------
with tab_dashboard:
    st.markdown("### 📈 Live Submitted Requests Dashboard")
    st.caption("Synchronized with [Promotion Form Request Backend Sheet](https://docs.google.com/spreadsheets/d/1aWN5BSWlMHYwBzrmijnlBEhP4ZEU9sJjx3VLIxqHnTE/edit#gid=0)")
    
    if not backend_df.empty:
        st.dataframe(backend_df, use_container_width=True, hide_index=True)
    else:
        st.info("No request records currently logged.")

# ---------------------------------------------------------
# TAB 3: CADET PROGRESS REPORT INTEGRATION
# ---------------------------------------------------------
with tab_progress:
    st.markdown("### 📊 Cadet Progress Lookup")
    st.caption("Live data from [SQ 153 Cadet Progress Sheet](https://docs.google.com/spreadsheets/d/1dUUf4xSWFX8KJoJPhqXd2glYmVGjVIZplvrToVd_Uyg/edit#gid=1661632143)")
    
    if not progress_df.empty:
        # Search Box Input
        search_query = st.text_input(
            "🔍 Search by Cadet Name or CAP ID:", 
            placeholder="Type a name (e.g., 'Smith') or CAP ID (e.g., '123456')..."
        ).strip()

        if search_query:
            # Filter logic for both Name and CAP ID
            query_str = str(search_query).lower()
            
            # Helper column matching
            name_match = progress_df["Cadet Name"].astype(str).str.lower().str.contains(query_str, na=False)
            
            capid_col = "CAP ID" if "CAP ID" in progress_df.columns else progress_df.columns[0]
            capid_match = progress_df[capid_col].astype(str).str.contains(query_str, na=False)

            filtered_df = progress_df[name_match | capid_match].copy()

            if not filtered_df.empty:
                # Helper function to format PT status and check expiry
                def format_pt_status(row):
                    pt_val = str(row.get("Fitness", "")).strip()
                    pt_exp = str(row.get("PT Expiry", "")).strip()
                    
                    if pt_exp and pt_exp.lower() not in ["none", "nan", ""]:
                        try:
                            exp_date = pd.to_datetime(pt_exp).date()
                            if exp_date < datetime.now().date():
                                return f"❌ Expired ({pt_exp})"
                            return f"✅ Valid (Expires {pt_exp})"
                        except Exception:
                            pass
                    return pt_val if pt_val and pt_val.lower() != "nan" else "N/A"

                # Standardize column mapping to display only concise fields
                summary_df = pd.DataFrame()
                summary_df["CAP ID"] = filtered_df[capid_col].astype(str).str.replace(".0", "", regex=False)
                summary_df["Cadet Name"] = filtered_df.get("Cadet Name", "N/A")
                summary_df["Flight"] = filtered_df.get("Assigned Flight", filtered_df.get("Flight", "N/A"))
                summary_df["Working Towards"] = filtered_df.get("Working Towards Achievement No.", "N/A")
                summary_df["Leadership Completed"] = filtered_df.get("Leadership", "N/A")
                summary_df["Drill Test Completed"] = filtered_df.get("Drill Test", "N/A")
                summary_df["AE Completed"] = filtered_df.get("Aerospace (AE) No. Completed", "N/A")
                summary_df["PT Status"] = filtered_df.apply(format_pt_status, axis=1)
                summary_df["Promotion Eligible"] = filtered_df.get("Promotion Eligible Date", "N/A")
                summary_df["Needs for Promotion"] = filtered_df.get("Notes: Needed for Promotion", "N/A")

                st.markdown(f"**Found {len(summary_df)} matching record(s):**")
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
            else:
                st.warning(f"No cadet records found matching **'{search_query}'**.")
        else:
            st.info("💡 **Enter a Cadet Name or CAP ID above to display progress data.**")
    else:
        st.error("Unable to load cadet progress data. Please check connection to Google Sheets.")

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
