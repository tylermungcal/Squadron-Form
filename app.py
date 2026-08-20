import base64
import calendar
import io
import re
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ---------------------------------------------------------
# PAGE CONFIG & STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Squadron 153 Request Portal", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    .stApp {background-color: #002244; color: #FFFFFF;}
    .main-header {background-color: #001122; padding: 1.5rem; border-radius: 10px; text-align: center; border: 2px solid #003366; margin-bottom: 2rem;}
    .main-header h1 { color: #FFFFFF !important; font-weight: 800; margin: 0;}
    .main-header h3 { color: #FFCC00 !important; margin-top: 5px;}
    label, .stMarkdown, p, span, h1, h2, h3, h4, h5, h6 {color: #FFFFFF !important;}
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {background-color: #001122 !important; color: #FFFFFF !important; border: 1px solid #003366 !important;}
    .stButton>button {background-color: #003366 !important; color: #FFCC00 !important; font-weight: bold !important; border: 1px solid #FFCC00 !important; width: 100%;}
    .stButton>button:hover {background-color: #FFCC00 !important; color: #002244 !important;}
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
# GOOGLE DRIVE INTEGRATION (OAuth2)
# ---------------------------------------------------------
def get_drive_service():
    try:
        if "oauth" not in st.secrets:
            return None
        oauth_info = st.secrets["oauth"]
        creds = Credentials(
            token=None,
            refresh_token=oauth_info["refresh_token"],
            client_id=oauth_info["client_id"],
            client_secret=oauth_info["client_secret"],
            token_uri=oauth_info.get("token_uri", "https://oauth2.googleapis.com/token"),
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"Authentication Error: {e}")
        return None

def upload_file_to_drive(uploaded_file, folder_id):
    try:
        service = get_drive_service()
        if not service:
            return None
        file_metadata = {'name': uploaded_file.name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getvalue()), mimetype=uploaded_file.type, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Error uploading file to Drive: {e}")
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

@st.cache_data(ttl=60)
def load_submitted_backend():
    # Replace with your deployed Apps Script Web App URL
    url = "https://script.google.com/macros/s/AKfycby_iDEd9a3hmJQyLhKuP9833KirbBK19Mki2K43eNOSs6iVLYDZq2FEw66V06Bb65uP6g/exec"
    try:
        response = requests.get(url)
        data = response.json()
        if data and len(data) > 0:
            df = pd.DataFrame(data[1:], columns=data[0])
            df.columns = df.columns.str.strip()
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading backend: {e}")
        return pd.DataFrame()

progress_df = load_cadet_progress()
backend_df = load_submitted_backend()

# ---------------------------------------------------------
# CALENDAR & SCHEDULE HELPERS
# ---------------------------------------------------------
def is_4th_wednesday(date_obj):
    if date_obj.weekday() != 2:
        return False
    return 22 <= date_obj.day <= 28

def generate_wednesdays_through_dec(start_date):
    wednesdays = []
    current = start_date
    days_ahead = 2 - current.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current += pd.Timedelta(days=days_ahead)
    end_date = datetime(2026, 12, 31).date()
    while current <= end_date:
        is_cpft = is_4th_wednesday(current)
        is_5th = current.day >= 29
        is_xmas_break = (current.month == 12 and current.day in [23, 30])
        is_holiday_party = (current.month == 12 and current.day == 16)
        is_thanksgiving_break = (current.month == 11 and current.day >= 24)
        is_halloween = (current.month == 10 and current.day == 28)

        if is_xmas_break or is_thanksgiving_break:
            uod = "Civilian / N/A"
            notes = "🚫 No Meeting — Holiday Break"
            cat = "Holiday Break"
            cpft_str = "No"
        elif is_holiday_party:
            uod = "Ugly Sweaters / Civilian"
            notes = "🎄 Holiday Party — No Requests Permitted"
            cat = "Social / Event"
            cpft_str = "No"
        elif is_halloween:
            uod = "Utility Uniform (ABU/OCP)"
            notes = "🎃 Halloween Party — No Requests Permitted"
            cat = "Social / Event"
            cpft_str = "No"
        elif is_5th:
            uod = "Civilian / Activity"
            notes = "⚠️ No Requests Accepted — 5th Wednesday Event"
            cat = "Leadership / General"
            cpft_str = "No"
        elif is_cpft:
            uod = "Utility Uniform (ABU/OCP)"
            notes = "CPFT Testing Night (Arrive in PTs, change to Utility)"
            cat = "Fitness / CPFT"
            cpft_str = "✅ Yes"
        else:
            week_num = (current.day - 1) // 7 + 1
            if week_num == 1:
                uod = "Utility Uniform (ABU/OCP)"
                cat = "Emergency Services (ES)"
            elif week_num == 2:
                uod = "Blues (Class B)"
                cat = "Aerospace Education"
            else:
                uod = "Utility Uniform (ABU/OCP)"
                cat = "Character Development"
            notes = "Standard Requests Allowed"
            cpft_str = "No"

        wednesdays.append({
            "Meeting Date": current.strftime("%d-%b-%Y"),
            "Training Focus": cat,
            "UOD": uod,
            "4th Wed CPFT": cpft_str,
            "Status & Notes": notes
        })
        current += pd.Timedelta(days=7)
    return pd.DataFrame(wednesdays)

@st.cache_data(ttl=300)
def load_schedule():
    today = datetime.now().date()
    sheet_id = "17wdWuOFBFyR507_vBITsTkI8il7k-1gDjLLPtNcCzt8"
    tabs_gids = [
        ("AUG 26", "420770302"),
        ("SEP 26", "1383777558"),
        ("OCT 26", "1182276527"),
        ("NOV 26", "1905667352"),
        ("DEC 26", "165741634")
    ]
    parsed_meetings = []
    for tab_name, gid in tabs_gids:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        try:
            raw_df = pd.read_csv(url, header=None)
            for i, row in raw_df.iterrows():
                row_str = " ".join(row.dropna().astype(str))
                if "foxhunt" in row_str.lower():
                    continue
                match = re.search(r"(\d{1,2}-(?:\w+|\d{1,2})-\d{2,4})", row_str, re.IGNORECASE)
                if match:
                    date_raw = match.group(1)
                    try:
                        p_date = pd.to_datetime(date_raw).date()
                        if p_date < today:
                            continue
                        uod_val = "Utility Uniform (ABU/OCP)"
                        focus_val = "Standard Meeting"
                        for col_idx, cell in enumerate(row.dropna()):
                            cell_text = str(cell).strip()
                            if "UOD:" in cell_text or "Uniform" in cell_text or "Ugly Sweaters" in cell_text:
                                uod_val = cell_text.replace("UOD:", "").strip()
                            elif col_idx > 2 and cell_text != date_raw and "UOD" not in cell_text:
                                focus_val = cell_text
                        parsed_meetings.append({
                            "Meeting Date": p_date.strftime("%d-%b-%Y"),
                            "Date Obj": p_date,
                            "UOD": uod_val,
                            "Focus": focus_val
                        })
                    except Exception:
                        pass
        except Exception:
            continue

    if len(parsed_meetings) > 3:
        df = pd.DataFrame(parsed_meetings).drop_duplicates(subset=["Meeting Date"]).sort_values("Date Obj")
        condensed = []
        for idx, row in df.iterrows():
            dt = row["Date Obj"]
            f_lower = str(row["Focus"]).lower()
            is_cpft = is_4th_wednesday(dt) or "cpft" in f_lower
            is_halloween = (dt.month == 10 and dt.day == 28) or "halloween" in f_lower
            is_holiday_party = (dt.month == 12 and dt.day == 16) or "party" in f_lower
            is_xmas_break = (dt.month == 12 and dt.day in [23, 30])
            is_party = is_halloween or is_holiday_party or any(kw in f_lower for kw in ["social", "banquet"])

            if is_xmas_break:
                cat = "Holiday Break"
                uod_final = "Civilian / N/A"
                notes = "🚫 No Meeting — Holiday Break"
                cpft_flag = "No"
            elif is_holiday_party:
                cat = "Social / Event"
                uod_final = "Ugly Sweaters / Civilian"
                notes = "🎄 Holiday Party — No Requests Permitted"
                cpft_flag = "No"
            elif is_party:
                cat = "Social / Event"
                uod_final = "Utility Uniform (ABU/OCP)"
                notes = f"🎃 {row['Focus']} — No Requests Permitted" if is_halloween else f"⚠️ No Requests — Social ({row['Focus']})"
                cpft_flag = "No"
            else:
                if any(kw in f_lower for kw in ["es", "emergency", "ground team"]):
                    cat = "Emergency Services (ES)"
                elif any(kw in f_lower for kw in ["character", "moral", "cd"]):
                    cat = "Character Development"
                elif any(kw in f_lower for kw in ["ae", "aerospace", "stem"]):
                    cat = "Aerospace Education"
                elif is_cpft:
                    cat = "Fitness / CPFT"
                else:
                    cat = "Leadership / General"

                is_5th = dt.day >= 29
                is_break = any(kw in f_lower for kw in ["break", "holiday", "canceled"])
                uod_final = "Utility Uniform (ABU/OCP)" if is_cpft else row["UOD"]
                cpft_flag = "✅ Yes" if is_cpft else "No"

                if is_5th:
                    notes = "⚠️ No Requests — 5th Wednesday Event"
                elif is_break:
                    notes = f"🚫 No Meeting — {row['Focus']}"
                else:
                    notes = "CPFT Testing Night (Arrive in PTs, change to Utility)" if is_cpft else "Standard Requests Allowed"

            condensed.append({
                "Meeting Date": row["Meeting Date"],
                "Training Focus": cat,
                "UOD": uod_final,
                "4th Wed CPFT": cpft_flag,
                "Status & Notes": notes
            })
        return pd.DataFrame(condensed)

    return generate_wednesdays_through_dec(today)

# ---------------------------------------------------------
# CADET FORM HELPERS
# ---------------------------------------------------------
def infer_current_grade(target_ach_str):
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
    g = grade_str.upper().strip()
    if g in ["C/AB", "C/AMN", "C/A1C", "C/SRA", "CADET"]:
        return {
            "phase": "Phase I (The Learning Phase)",
            "form_name": "CAPF 60-91 (Cadet Leadership Feedback - Phase I)",
            "url": "https://www.gocivilairpatrol.com/media/cms/CAPF_6091_25B1D25BA2960.pdf"
        }
    elif g in ["C/SSGT", "C/TSGT", "C/MSGT", "C/SMSGT", "C/CMSGT"]:
        return {
            "phase": "Phase II (The Leadership Phase)",
            "form_name": "CAPF 60-92 (Cadet Leadership Feedback - Phase II)",
            "url": "https://www.gocivilairpatrol.com/media/cms/CAPF_6092_F88D00D0FB843.pdf"
        }
    elif g in ["C/2D LT", "C/1ST LT", "C/CAPT"]:
        return {
            "phase": "Phase III (The Command Phase)",
            "form_name": "CAPF 60-93 (Cadet Leadership Feedback - Phase III)",
            "url": "https://www.gocivilairpatrol.com/media/cms/CAPF_6093_39C650ED8081A.pdf"
        }
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

def calculate_submission_deadline(target_wed_date):
    thursday_prior = target_wed_date - timedelta(days=6)
    return datetime(thursday_prior.year, thursday_prior.month, thursday_prior.day, 23, 59, 59)

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

    # Folder IDs
    PRIMARY_FOLDER_ID = st.secrets.get("DRIVE_FOLDER_ID", "12Z89jcG91dlFk19bpU5acPhSdiL-kK2z")
    PROOF_FOLDER_ID = "1m1gy0TRXXQ4gUMgm_Jj31ilUpIBoOEQE"  # eServices Screenshot Folder

    if not progress_df.empty and "Cadet Name" in progress_df.columns:
        cadet_names = sorted([n for n in progress_df["Cadet Name"].dropna().unique() if str(n).strip()])
        selected_cadet = st.selectbox("Select Your Name:*", ["-- Select Name --"] + cadet_names)

        if selected_cadet != "-- Select Name --":
            cadet_row = progress_df[progress_df["Cadet Name"] == selected_cadet].iloc[0]
            working_ach = str(cadet_row.get("Working Towards Achievement No.", "N/A"))
            raw_cap_id = str(cadet_row.get("CAP ID", "")).replace(".0", "").strip()
            inferred_email = str(cadet_row.get("Email", cadet_row.get("Cadet Email", ""))).strip()
            inferred_grade = infer_current_grade(working_ach)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                cap_id_input = st.text_input("CAP ID (6 Digits):*", value=raw_cap_id)
            with col2:
                email_input = st.text_input("Email Address:*", value=inferred_email)
            with col3:
                grade_input = st.text_input("Current Grade (Auto-Inferred):*", value=inferred_grade)
            with col4:
                flight_input = st.selectbox("Flight:*", ["Alpha", "Bravo", "Charlie", "CTF", "Support", "Line"])

            st.info(f"**Cadet:** {selected_cadet} | **Target Achievement:** {working_ach}")

            all_request_types = [
                "-- Select Request Type --",
                "4th Wednesday CPFT",
                "Drill Test",
                "PRB",
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

            if req_type == "-- Select Request Type --":
                st.info("💡 Please select a **Request Type** above to continue.")
            else:
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

                lead_val = str(cadet_row.get("Leadership", "")).strip()
                ae_val = str(cadet_row.get("Aerospace (AE) No. Completed", "0")).strip()

                prereq_valid = True
                error_msgs = []

                clean_cap_id = re.sub(r"\D", "", cap_id_input)
                if len(clean_cap_id) != 6:
                    prereq_valid = False
                    error_msgs.append("CAP ID must be exactly **6 digits**.")

                if "@" not in email_input or "." not in email_input:
                    prereq_valid = False
                    error_msgs.append("Please enter a valid **email address**.")

                eservices_proof_file = None
                if req_type != "4th Wednesday CPFT":
                    manual_override = st.checkbox("I have completed my prerequisites, but the Cadet Progress report is displaying incorrect info.")
                    if manual_override:
                        st.warning("⚠️ **eServices Verification Required:** Please upload a screenshot of your **Cadet Promotions Track Report** from eServices showing completed prerequisites.")
                        eservices_proof_file = st.file_uploader("Upload eServices Promotions Track Screenshot:* (Required)", type=["png", "jpg", "jpeg", "pdf"], key="eservices_proof")
                        if eservices_proof_file is None:
                            prereq_valid = False
                            error_msgs.append("You must upload an eServices screenshot to verify completed prerequisites.")
                    else:
                        if req_type == "Drill Test":
                            if not lead_val or lead_val in ["None", "nan"] or ae_val in ["0", "None", "nan", ""]:
                                prereq_valid = False
                                error_msgs.append("To request a **Drill Test**, you must have completed **Learn to Lead** and **AE Dimensions**.")
                        elif req_type in ["Technical Writing Submission (SDA)", "Essay Submission"]:
                            if not lead_val or lead_val in ["None", "nan"] or ae_val in ["0", "None", "nan", ""]:
                                prereq_valid = False
                                error_msgs.append("To request an **SDA / Essay Submission**, **Learn to Lead** and **AE Dimensions** must be completed.")

                st.markdown("#### Select Target Wednesday Date")
                target_date = st.date_input("Target Meeting Date:", value=datetime.now().date())

                if target_date.weekday() != 2:
                    prereq_valid = False
                    error_msgs.append("Requests can only be submitted for **Wednesday meeting dates**.")

                if req_type == "4th Wednesday CPFT" and not is_4th_wednesday(target_date):
                    prereq_valid = False
                    error_msgs.append("4th Wednesday CPFT requests can **only** be submitted for dates that are the **4th Wednesday** of the month.")

                deadline_dt = calculate_submission_deadline(target_date)
                now = datetime.now()
                st.caption(f"🕒 **Submission Deadline for {target_date.strftime('%d-%b-%Y')}:** {deadline_dt.strftime('%A, %b %d, %Y at 23:59')}")

                if now > deadline_dt:
                    prereq_valid = False
                    error_msgs.append(f"The deadline for requesting **{target_date.strftime('%d-%b-%Y')}** passed on **{deadline_dt.strftime('%b %d at 23:59')}** (Thursday of the week prior).")

                is_halloween_date = (target_date.month == 10 and target_date.day == 28)
                is_holiday_party = (target_date.month == 12 and target_date.day == 16)
                is_xmas_break = (target_date.month == 12 and target_date.day in [23, 30])
                is_5th_wed = (target_date.weekday() == 2 and target_date.day >= 29)

                if is_halloween_date or is_holiday_party or is_xmas_break or is_5th_wed:
                    prereq_valid = False
                    error_msgs.append("No requests are permitted on **Party or Holiday Break dates** (e.g., Halloween Party / Holiday Party / Xmas Break / 5th Wednesday).")

                if req_type == "PRB":
                    if "Achievement 4" in working_ach or any(f"Achievement {i}" in working_ach for i in range(5, 17)):
                        st.warning("⚠️ **Reminder:** PRB Requests for Achievement 4+ must take place on a **Blues Night**.")

                is_upload_required = req_type in ["Technical Writing Submission (SDA)", "Essay Submission", "PRB"] or (
                    req_type == "Milestone Exam" and selected_exam_name in ["Ira C. Eaker Award Exam", "General Carl A. Spaatz Award Exam"]
                )
                
                no_upload_needed = req_type in ["Drill Test", "4th Wednesday CPFT"] or (
                    req_type == "Milestone Exam" and selected_exam_name not in ["Ira C. Eaker Award Exam", "General Carl A. Spaatz Award Exam"]
                )

                uploaded_file = None
                if not no_upload_needed:
                    st.markdown("#### Document Uploads")
                    if req_type == "PRB":
                        prb_info = get_capf60_90_info(grade_input)
                        st.markdown(f"**Required Form:** Submit your **[{prb_info['form_name']}]({prb_info['url']})** for **{prb_info['phase']}** ({grade_input}).")
                        label = f"Upload completed {prb_info['form_name'].split(' ')[0]} PDF/Image:* (Required)"
                    elif is_upload_required:
                        label = f"Upload {req_type} Document:* (Required)"
                    else:
                        label = "Upload Reference Documents (Optional):"

                    uploaded_file = st.file_uploader(label, type=["pdf", "docx", "doc", "jpg", "png"])

                    if is_upload_required and uploaded_file is None:
                        prereq_valid = False
                        error_msgs.append(f"You must upload a document for **{req_type}** before submitting.")

                if not prereq_valid:
                    for msg in error_msgs:
                        st.error(f"❌ **Validation Alert:** {msg}")

                if req_type == "4th Wednesday CPFT":
                    st.info("ℹ️ **4th Wednesday Note:** Arrive in PTs for testing at 1800, then change into Utility after testing.")

                with st.form("cadet_request_form", clear_on_submit=True):
                    comments = st.text_area("Additional Notes / Details for Staff:")
                    submit_button = st.form_submit_button("Submit Request")

                    if submit_button:
                        if not prereq_valid:
                            st.error("Please resolve the prerequisite, required upload, and date validation errors listed above before submitting.")
                        else:
                            file_link = ""
                            proof_link = ""

                            with st.spinner("Processing request and uploading files..."):
                                if uploaded_file is not None:
                                    file_link = upload_file_to_drive(uploaded_file, PRIMARY_FOLDER_ID) or ""

                                if eservices_proof_file is not None:
                                    proof_link = upload_file_to_drive(eservices_proof_file, PROOF_FOLDER_ID) or ""

                                webhook_url = st.secrets.get("WEBHOOK_URL", "https://script.google.com/macros/s/AKfycbz_Placeholder/exec")
                                payload = {
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "cadet_name": selected_cadet,
                                    "email": email_input,
                                    "cap_id": clean_cap_id,
                                    "grade": grade_input,
                                    "flight": flight_input,
                                    "request_type": req_type,
                                    "milestone_exam": selected_exam_name if req_type == "Milestone Exam" else "",
                                    "target_date": target_date.strftime("%d-%b-%Y"),
                                    "uploaded_file_url": file_link,
                                    "proof_file_url": proof_link,
                                    "status": "Pending",
                                    "comments": comments
                                }

                                try:
                                    res = requests.post(webhook_url, json=payload)
                                    st.success(f"Request for **{req_type}** successfully submitted for **{selected_cadet}**!")
                                    st.balloons()
                                except Exception as e:
                                    st.error(f"Error posting submission to backend: {e}")

# ---------------------------------------------------------
# TAB 2: LIVE REQUEST DASHBOARD
# ---------------------------------------------------------
with tab_dashboard:
    st.markdown("### Live Request Status Dashboard")
    
    # Password Lock Gate
    dashboard_password = st.text_input("Enter Dashboard Password:", type="password", key="dash_pass")
    
    if dashboard_password == "1530":
        st.success("Access Granted")
        st.markdown("---")
        
        # Load backend requests CSV (Ensure URL matches your backend spreadsheet)
        backend_url = "https://docs.google.com/spreadsheets/d/1aWN5BSWlMHYwBzrmijnlBEhP4ZEU9sJjx3VLIxqHnTE/export?format=csv&gid=0"
        
        try:
            backend_df = pd.read_csv(backend_url)
            backend_df.columns = backend_df.columns.str.strip()
        except Exception as e:
            backend_df = pd.DataFrame()
        
        if not backend_df.empty:
            m1, m2 = st.columns(2)
            m1.metric("Total Requests Recorded", len(backend_df))
            
            # Display status metrics if Status column exists
            status_col = [col for col in backend_df.columns if "status" in col.lower()]
            if status_col:
                pending_cnt = len(backend_df[backend_df[status_col[0]].astype(str).str.lower().str.contains("pending", na=False)])
                m2.metric("Pending Requests", pending_cnt)

            st.dataframe(backend_df, use_container_width=True, hide_index=True)
        else:
            st.info("No requests currently recorded or unable to load backend sheet.")
            
    elif dashboard_password != "":
        st.error("Incorrect password. Access denied.")
    else:
        st.warning("🔒 This dashboard is password protected. Please enter the password above.")

# ---------------------------------------------------------
# TAB 3: CADET PROGRESS REPORT
# ---------------------------------------------------------
with tab_progress:
    st.markdown("### Cadet Progress Overview")
    if not progress_df.empty:
        df_display = progress_df.copy()
        
        # Map exact sheet column headers to clean display labels
        column_mapping = {
            "CAP ID": "CAPID",
            "Cadet Name": "Cadet Name",
            "Assigned Flight": "Assigned Flight",
            "Working Towards Achievement No.": "Achievement Working Towards",
            "Leadership": "Leadership",
            "AE Req Date": "AE Req Date",
            "Drill Test": "Drill Test",
            "Fitness": "Fitness (CPFT)",
            "PRB": "PRB",
            "Promotion Eligible Date": "Promotion Eligible Date",
            "Notes: Needed for Promotion": "Notes: Needed for Promotion",
            "PT Expiry": "PT Expiry"
        }
        
        df_display = df_display.rename(columns=column_mapping)

        # The 12 Target columns to display in the overview table
        target_columns = [
            "Cadet Name",
            "CAPID",
            "Assigned Flight",
            "Achievement Working Towards",
            "Leadership",
            "AE Req Date",
            "Drill Test",
            "Fitness (CPFT)",
            "PRB",
            "Promotion Eligible Date",
            "Notes: Needed for Promotion",
            "PT Expiry"
        ]

        # Build dropdown options mapping both Cadet Name and CAPID
        search_options = [""]
        option_map = {}

        for idx, row in df_display.iterrows():
            name = str(row["Cadet Name"]).strip() if "Cadet Name" in df_display.columns and pd.notna(row["Cadet Name"]) else ""
            
            capid_raw = row["CAPID"] if "CAPID" in df_display.columns else ""
            if pd.notna(capid_raw) and str(capid_raw).strip() != "":
                capid_str = str(capid_raw).split('.')[0].strip()
            else:
                capid_str = ""

            if name or capid_str:
                label = f"{name} (CAPID: {capid_str})" if name and capid_str else (name or f"CAPID: {capid_str}")
                search_options.append(label)
                option_map[label] = idx

        selected_option = st.selectbox(
            "Search Cadet by Name or CAPID:",
            options=sorted(list(set(search_options))),
            index=0,
            placeholder="Type Name or CAPID..."
        )

        # Render dataframe only when a cadet is selected
        if selected_option and selected_option in option_map:
            selected_idx = option_map[selected_option]
            filtered_df = df_display.iloc[[selected_idx]]

            available_cols = [col for col in target_columns if col in filtered_df.columns]
            st.dataframe(filtered_df[available_cols], use_container_width=True, hide_index=True)
        else:
            st.info("🔍 Please search or select a cadet name or CAPID to view their progress record.")
    else:
        st.info("Cadet progress sheet currently unavailable.")

# ---------------------------------------------------------
# TAB 4: WEDNESDAY SCHEDULE & UOD
# ---------------------------------------------------------
with tab_sched:
    st.markdown("### Wednesday Training Schedule & Uniform of the Day")
    schedule_df = load_schedule()
    if not schedule_df.empty:
        st.dataframe(schedule_df, use_container_width=True)
    else:
        st.info("Schedule currently unavailable.")
