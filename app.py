import streamlit as st
import requests

# 1. Page Configuration
st.set_page_config(page_title="Squadron Request Form", page_icon="✈️", layout="centered")

# 2. Simplified CSS (Background photo + Dark Blue Card only)
st.markdown("""
    <style>
    /* Full Page Background Image */
    .stApp {
        background: url('https://raw.githubusercontent.com/tylermungcal/Squadron-Form/main/IMG_4502.jpeg') no-repeat center center fixed;
        background-size: cover;
    }
    
    /* Center Card Container Styling (#00308f) */
    div[data-testid="stForm"] {
        background-color: #00308f;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    
    /* Ensure Form Labels and Title stay White on the Blue Card */
    div[data-testid="stForm"] label, 
    div[data-testid="stForm"] h2, 
    div[data-testid="stForm"] p,
    div[data-testid="stForm"] .stCaption {
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Form Header
st.markdown("## Squadron Request Form")

# Dropdown Option Lists
drill_list = ["Achievement 1", "Achievement 2", "Achievement 3", "Wright Brothers Award", "Achievement 4", "Achievement 5", "Achievement 6", "Achievement 7", "Achievement 8"]
milestone_list = ["Wright Brothers Award", "Mitchell Aerospace Exam", "Mitchell Leadership Exam", "Amelia Earhart Award", "Ira C. Eaker Award", "General Carl A. Spaatz Award"]
essay_list = ["Achievement 8", "Ira C. Eaker Award", "General Carl A. Spaatz Award"]
sda_list = ["Achievement 9", "Achievement 10", "Achievement 11", "Achievement 12", "Achievement 13", "Achievement 14", "Achievement 15", "Achievement 16"]
full_list = drill_list + sda_list + ["Billy Mitchell Award", "Amelia Earhart Award", "Ira C. Eaker Award", "General Carl A. Spaatz Award"]

with st.form("squadron_form", clear_on_submit=True):
    email = st.text_input("Email Address *")
    
    flight = st.selectbox("Flight *", [
        "-- Select Flight --", "Line Staff", "Support Staff", 
        "Alpha Flight", "Bravo Flight", "Charlie Flight", "Cadet Training Flight (CTF)"
    ])
    
    first_name = st.text_input("First Name *")
    last_name = st.text_input("Last Name *")
    
    request_type = st.selectbox("Requesting a... *", [
        "-- Select Request --", "Drill Test", "PRB", "CPFT (4th Wednesday)", 
        "Milestone Exam", "Essay Submission", "Technical Writing Submission (SDA)", "Specialty Exam"
    ])

    # Dynamic Field Logic
    achievement = None
    if request_type == "Drill Test":
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + drill_list)
    elif request_type == "Milestone Exam":
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + milestone_list)
    elif request_type == "Essay Submission":
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + essay_list)
    elif request_type == "Technical Writing Submission (SDA)":
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + sda_list)
    elif request_type == "PRB":
        achievement = st.selectbox("For what achievement / award? *", ["-- Select --"] + full_list)

    specialty_exam = None
    if request_type == "Specialty Exam":
        specialty_exam = st.selectbox("Exam Requested *", ["-- Select Exam --", "ICUT", "Other"])

    meeting_date = st.date_input("Requested Meeting Date")

    file_url = None
    if request_type in ["PRB", "Essay Submission", "Technical Writing Submission (SDA)", "Specialty Exam"]:
        label = "CAPF 60-90 Form Link (Phases 1-4) *" if request_type == "PRB" else "Document / PDF Link *"
        help_txt = "Upload your completed CAPF 60-90 form to Google Drive with link viewing access." if request_type == "PRB" else "Upload your document to Google Drive and paste the link."
        file_url = st.text_input(label, placeholder="https://drive.google.com/...", help=help_txt)

    submit_button = st.form_submit_button("Submit Request")

    if submit_button:
        if not email or flight == "-- Select Flight --" or not first_name or not last_name or request_type == "-- Select Request --":
            st.error("Please fill in all required fields.")
        else:
            WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzVSE7HA-fR--ME4MmTfYzyAzOYPhxT6IUDEK0d5PAvcxdgSOUPs9BoEP2okNKvE0e8Ow/exec"
            payload = {
                "email": email,
                "flight": flight,
                "firstName": first_name,
                "lastName": last_name,
                "requestType": request_type,
                "achievement": achievement if achievement else "",
                "specialtyExam": specialty_exam if specialty_exam else "",
                "meetingDate": str(meeting_date) if meeting_date else "",
                "fileUrl": file_url if file_url else ""
            }
            try:
                requests.post(WEBHOOK_URL, data=payload)
                st.success("Submitted successfully!")
            except Exception as e:
                st.error(f"Error submitting form: {e}")
