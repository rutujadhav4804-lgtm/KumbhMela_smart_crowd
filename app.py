import streamlit as st
import pandas as pd
import os

# ---------------------------
# File paths
# ---------------------------
user_file = "users.csv"
log_file = "logs/zone_counts.csv"

# ---------------------------
# Helper Functions
# ---------------------------
def register_user(fullname, email, password):
    if not os.path.exists(user_file):
        df = pd.DataFrame(columns=["fullname", "email", "password"])
        df.to_csv(user_file, index=False)
    
    try:
        users = pd.read_csv(user_file)
    except pd.errors.EmptyDataError:
        users = pd.DataFrame(columns=["fullname", "email", "password"])
    
    if email.strip() in users['email'].astype(str).str.strip().values:
        return False
    new_user = pd.DataFrame([{
        "fullname": fullname.strip(),
        "email": email.strip(),
        "password": password.strip()
    }])
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv(user_file, index=False)
    return True

def login_user(email, password):
    if not os.path.exists(user_file):
        return False, ""
    try:
        users = pd.read_csv(user_file)
    except pd.errors.EmptyDataError:
        return False, ""
    users['email'] = users['email'].astype(str).str.strip()
    users['password'] = users['password'].astype(str).str.strip()
    user = users[(users['email'] == email.strip()) & (users['password'] == password.strip())]
    if not user.empty:
        return True, user.iloc[0]['fullname']
    else:
        return False, ""

def load_latest_zone_data():
    if not os.path.exists(log_file):
        return []
    try:
        df = pd.read_csv(log_file)
    except pd.errors.EmptyDataError:
        return []
    latest_data = df.groupby("zone").tail(1).to_dict('records')
    for row in latest_data:
        count = int(row['people_count'])
        if count < 8:
            row['status'] = "✅ Safe"
            row['color'] = "#4CAF50"
        elif count < 10:
            row['status'] = "🟡 Moderate"
            row['color'] = "#FF9800"
        else:
            row['status'] = "🚨 Overcrowded"
            row['color'] = "#F44336"
    return latest_data

def show_dashboard(fullname):
    st.title(f"Welcome {fullname} to Smart Crowd Dashboard")
    st.write("Real-time zone-wise crowd monitoring:")

    latest_data = load_latest_zone_data()
    if latest_data:
        for row in latest_data:
            st.markdown(
                f"""
                <div style="background-color:{row['color']}; padding:15px; border-radius:10px; margin-bottom:10px;">
                    <h4>{row['zone']}</h4>
                    <p>People Count: {row['people_count']}</p>
                    <p>Status: {row['status']}</p>
                </div>
                """, unsafe_allow_html=True
            )
    else:
        st.info("⚠️ No data yet. Run video detection first!")

# ---------------------------
# Streamlit Pages
# ---------------------------
page = st.sidebar.selectbox("Go to", ["Home", "Register", "Login"])

if page == "Home":
    st.title("Welcome to Smart Crowd Surveillance")
    st.write("Please register or login to access the dashboard.")

elif page == "Register":
    st.title("Register")
    fullname = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Register"):
        if register_user(fullname, email, password):
            st.success("Registration successful! You can now login.")
        else:
            st.error("Email already registered!")

elif page == "Login":
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        success, fullname = login_user(email, password)
        if success:
            st.success(f"Login successful! Welcome {fullname}")
            show_dashboard(fullname)
        else:
            st.error("Incorrect email or password!")
