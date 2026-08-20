import streamlit as st
import pandas as pd
import io
import requests
import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# Page Config
st.set_page_config(
    page_title="Squadron 153 Cadet Request & Testing Portal",
    page_icon="✈️",
    layout="centered"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 10px;
        background-color: #002244;
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
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
            supportsAllDrives=True  # Enables upload inside Shared Drives
        ).execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return None

# ---------------------------------------------------------
# DATA LOADERS
# ---------------------------------------------------------
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

@st.cache_data(ttl=15)
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

@st.cache_data(ttl=300)
def load_training_schedule():
    sheet_id = "17wdWuOFBFyR507_vBITsTkI8il7k-1gDjLLPtNcCzt8"
    gid = "127391265"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

# Navigation tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Submit Request", 
    "📈 Live Request Dashboard", 
    "📊 Cadet Progress Report", 
    "📅 Wednesday Schedule & UOD"
])

# ---------------------------------------------------------
# TAB 1: FORM SUBMISSION
# ---------------------------------------------------------
with tab1:
    st.subheader("Cadet Request Form")
    cadet_df = load_cadet_progress()
    
    if not cadet_df.empty and "Name" in cadet_df.columns:
        cadet_names = cadet_df["Name"].dropna().unique().tolist()
        cadet_names.sort()
        selected_name = st.selectbox("Select Your Name:*", ["-- Select Name --"] + cadet_names)
    else:
        selected_name = st.text_input("Enter Your Full Name:*")

    # Auto-fill fields
    cadet_email, cap_id, grade, flight = "", "", "", ""
    if selected_name and selected_name != "-- Select Name --" and not cadet_df.empty:
        match = cadet_df[cadet_df["Name"] == selected_name]
        if not match.empty:
            cadet_email = match.iloc[0].get("Email", "")
            cap_id = match.iloc[0].get("CAPID", "")
            grade = match.iloc[0].get("Grade", "")
            flight = match.iloc[0].get("Flight", "")

    email_input = st.text_input("Email Address:*", value=str(cadet_email) if pd.notna(cadet_email) else "")
    capid_input = st.text_input("CAP ID:*", value=str(cap_id) if pd.notna(cap_id) else "")
    grade_input = st.text_input("Current Grade/Rank:", value=str(grade) if pd.notna(grade) else "")
    flight_input = st.text_input("Flight:", value=str(flight) if pd.notna(flight) else "")

    request_type = st.selectbox("Request Type:*", [
        "-- Select Request Type --",
        "Achievement Test",
        "Milestone Exam",
        "Promotion Review Board (PRB)",
        "Staff Application / Interview",
        "SDA Submission",
        "Essay / Presentation Review",
        "General Inquiry"
    ])

    milestone_exam = ""
    if request_type == "Milestone Exam":
        milestone_exam = st.selectbox("Select Milestone Exam:", [
            "Wright Brothers (C/SSgt)",
            "Mitchell (C/2d Lt)",
            "Earhart (C/Capt)",
            "Eaker (C/Lt Col)"
        ])

    target_date = st.date_input("Target Date for Request/Testing:", min_value=datetime.date.today())

    st.write("---")
    st.subheader("Document Uploads")
    
    upload_folder_id = "12Z89jcG91dlFk19bpU5acPhSdiL-kK2z"
    uploaded_file = st.file_uploader("Upload Primary Document (SDA, Essay, PRB Form, etc.):", type=["pdf", "docx", "doc", "png", "jpg"])
    proof_file = st.file_uploader("Upload Proof/Prerequisite Document (Optional):", type=["pdf", "docx", "doc", "png", "jpg"])

    if st.button("Submit Request"):
        if not selected_name or selected_name == "-- Select Name --":
            st.error("Please select or enter your name.")
        elif not email_input:
            st.error("Please enter your email address.")
        elif request_type == "-- Select Request Type --":
            st.error("Please select a request type.")
        else:
            with st.spinner("Processing submission and uploading files..."):
                uploaded_url = ""
                proof_url = ""

                if uploaded_file:
                    uploaded_url = upload_file_to_drive(uploaded_file, upload_folder_id) or ""

                if proof_file:
                    proof_url = upload_file_to_drive(proof_file, upload_folder_id) or ""

                webhook_url = "https://script.google.com/macros/s/AKfycbz_Placeholder/exec"
                payload = {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cadet_name": selected_name,
                    "email": email_input,
                    "cap_id": capid_input,
                    "grade": grade_input,
                    "flight": flight_input,
                    "request_type": request_type,
                    "milestone_exam": milestone_exam,
                    "target_date": str(target_date),
                    "uploaded_file_url": uploaded_url,
                    "proof_file_url": proof_url,
                    "status": "Pending",
                    "comments": ""
                }

                try:
                    res = requests.post(webhook_url, json=payload)
                    st.success("Your request has been submitted successfully!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error posting submission to backend: {e}")

# ---------------------------------------------------------
# TAB 2: LIVE DASHBOARD (Password Protected)
# ---------------------------------------------------------
with tab2:
    st.subheader("Live Request Status")
    
    password = st.text_input("Enter Staff Password to View Requests:", type="password")
    if password == "sq153staff":
        backend_df = load_submitted_backend()
        if not backend_df.empty:
            st.dataframe(backend_df, use_container_width=True)
        else:
            st.info("No requests recorded yet.")
    elif password:
        st.error("Incorrect password.")
    else:
        st.warning("Please enter the password to access the staff dashboard.")

# ---------------------------------------------------------
# TAB 3: CADET PROGRESS REPORT
# ---------------------------------------------------------
with tab3:
    st.subheader("Cadet Progress Overview")
    progress_df = load_cadet_progress()
    
    if not progress_df.empty:
        if "Name" in progress_df.columns:
            search_names = progress_df["Name"].dropna().unique().tolist()
            search_names.sort()
            search_cadet = st.selectbox("Search Cadet Progress:", ["-- Show All Cadets --"] + search_names)
            
            if search_cadet != "-- Show All Cadets --":
                filtered_df = progress_df[progress_df["Name"] == search_cadet]
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.dataframe(progress_df, use_container_width=True)
        else:
            st.dataframe(progress_df, use_container_width=True)
    else:
        st.info("Progress data currently unavailable.")

# ---------------------------------------------------------
# TAB 4: SCHEDULE & UOD
# ---------------------------------------------------------
with tab4:
    st.subheader("Wednesday Schedule & Uniform of the Day (UOD)")
    schedule_df = load_training_schedule()
    if not schedule_df.empty:
        st.dataframe(schedule_df, use_container_width=True)
    else:
        st.info("Schedule data currently unavailable.")
