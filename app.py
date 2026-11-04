import streamlit as st
from datetime import date, timedelta
import pandas as pd
import altair as alt
import gspread
from google.oauth2.service_account import Credentials

# --- SECURITY: AUTHORIZED USERS ---
VALID_USERS = {
    "Ardra": "Ardra@1803"
    "Dhanya": "1984"
    "Arja": "080225"
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["current_user"] = ""

# --- GOOGLE SHEETS SETUP (V5 - Rate Limit Fixed) ---
# The @st.cache_resource tag stops the app from spamming Google!
@st.cache_resource
def connect_to_google():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # Ensure the private key handles newline characters and is encoded as bytes
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(
        "https://docs.google.com/spreadsheets/d/129ZwB6nGV6cyYRVChlwGRxz1ONtDzfbWXzyxRn_Khh8/edit?gid=0#gid=0"
    ).sheet1

sheet = connect_to_google()

# Automatically add headers if the sheet is completely blank
headers = ["username", "log_date", "last_period", "flow", "water", "sleep", "steps", "screen_time", "mood", "anxiety", "study_time", "pages_read", "had_migraine", "migraine_pain", "rating", "weather", "highlight", "grateful", "media", "book", "journal"]
if len(sheet.get_all_values()) == 0:
    sheet.append_row(headers)

# --- THE LOGIN SCREEN ---
if not st.session_state["logged_in"]:
    st.title("🔒 Wellness Tracker Login")
    entered_username = st.text_input("Username").lower()
    entered_password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if entered_username in VALID_USERS and VALID_USERS[entered_username] == entered_password:
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = entered_username
            st.rerun()
        else:
            st.error("Incorrect username or password.")
            
# --- THE MAIN APP ---
else:
    user = st.session_state["current_user"]
    st.sidebar.title(f"Welcome, {user.capitalize()}!")
    menu = st.sidebar.radio("Go to:", ["Add Daily Log", "View History"])
    
    if st.sidebar.button("Log Out"):
        st.session_state["logged_in"] = False
        st.session_state["current_user"] = ""
        st.rerun()

    # PAGE 1: ADD LOG
    if menu == "Add Daily Log":
        st.title("My Wellness & Cycle Tracker")
        st.header("1. Cycle & Vitals")
        log_date = st.date_input("Today's Date", date.today())
        last_period = st.date_input("First day of last period?", date.today())
        days_since = (log_date - last_period).days

        flow = "None"
        if days_since < 0:
            st.write("Wait, your last period can't be in the future!")
        elif days_since <= 5:
            st.info(f"Day {days_since}: Menstrual Phase 🩸")
            flow = st.selectbox("Flow Intensity", ["Light", "Medium", "Heavy", "Spotting"])
        elif days_since <= 13:
            st.success(f"Day {days_since}: Follicular Phase 🌱")
        elif days_since <= 15:
            st.warning(f"Day {days_since}: Ovulation Phase ✨")
        elif days_since <= 25:
            st.info(f"Day {days_since}: Luteal Phase 🍂")
        else:
            st.error(f"Day {days_since}: Period is approaching! 🚨")

        col1, col2 = st.columns(2)
        with col1:
            water = st.number_input("Water (glasses)", 0, 20, 5)
            sleep = st.slider("Sleep (hours)", 0.0, 14.0, 7.5, 0.5)
        with col2:
            steps = st.selectbox("Step Count", ["Under 1k", "1k-2k", "2k-3k", "3k-5k", "5k+"])
            screen_time = st.slider("Screen (hours)", 0.0, 15.0, 4.0, 0.5)

        st.header("2. Mind & Grind")
        col3, col4 = st.columns(2)
        with col3:
            mood = st.selectbox("Overall Mood", ["Happy", "Calm", "Focused", "Anxious", "Stressed", "Sad"])
            anxiety = st.slider("Anxiety (1-10)", 1, 10, 1)
        with col4:
            study_time = st.number_input("Study (hours)", 0.0, 15.0, 2.0, 0.5)
            pages_read = st.number_input("Pages Read", 0, 500, 10)

        had_migraine = st.checkbox("Did you have a migraine today?")
        migraine_pain = st.slider("Migraine Intensity (1-10)", 1, 10, 5) if had_migraine else 0

        st.header("3. The Diary")
        rating = st.slider("Overall Day Rating (1-5)", 1, 5, 3)
        weather = st.selectbox("Weather", ["Sunny", "Cloudy", "Rainy", "Stormy"])
        highlight = st.text_input("Highlight of the day")
        grateful = st.text_input("One thing I'm grateful for")
        media = st.text_input("Media Watched")
        book = st.text_input("Book I'm reading")
        journal = st.text_area("Brain Dump...", height=150)

        if st.button("Save Daily Log"):
            new_row = [user, str(log_date), str(last_period), flow, water, sleep, steps, screen_time, mood, anxiety, study_time, pages_read, had_migraine, migraine_pain, rating, weather, highlight, grateful, media, book, journal]
            
            # Smart Save: Find if this date already exists for this user and overwrite it
            all_data = sheet.get_all_values()
            row_to_delete = None
            for i, row in enumerate(all_data):
                if len(row) >= 2 and row[0] == user and row[1] == str(log_date):
                    row_to_delete = i + 1 
                    break
            
            if row_to_delete:
                sheet.delete_rows(row_to_delete)
                
            sheet.append_row(new_row)
            st.success(f"Saved successfully to the Cloud!")

    # PAGE 2: VIEW HISTORY
    elif menu == "View History":
        st.title("🎨 My Year in Pixels")
        
        all_data = sheet.get_all_records()
        df = pd.DataFrame(all_data)
        
        if df.empty or user not in df['username'].values:
            st.info(f"No data yet for {user.capitalize()}! Go add some logs.")
        else:
            df = df[df['username'] == user]
            
            df['log_date'] = pd.to_datetime(df['log_date'])
            df['Month'] = df['log_date'].dt.strftime('%b')
            df['Day'] = df['log_date'].dt.day
            
            tab1, tab2, tab3 = st.tabs(["Vitals & Health", "Mind & Productivity", "Diary & Raw Data"])
            
            with tab1:
                st.subheader("💧 Hydration Grid")
                st.altair_chart(alt.Chart(df).mark_rect().encode(
                    x='Day:O', y=alt.Y('Month:O', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                    color=alt.Color('water:Q', scale=alt.Scale(scheme='blues')), tooltip=['log_date', 'water']
                ).properties(height=200), use_container_width=True)

                st.subheader("😴 Sleep Grid")
                st.altair_chart(alt.Chart(df).mark_rect().encode(
                    x='Day:O', y=alt.Y('Month:O', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                    color=alt.Color('sleep:Q', scale=alt.Scale(scheme='purples')), tooltip=['log_date', 'sleep']
                ).properties(height=200), use_container_width=True)
                
                st.subheader("🧠 Migraine Intensity")
                st.altair_chart(alt.Chart(df).mark_rect().encode(
                    x='Day:O', y=alt.Y('Month:O', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                    color=alt.Color('migraine_pain:Q', scale=alt.Scale(scheme='redpurple')), tooltip=['log_date', 'migraine_pain']
                ).properties(height=200), use_container_width=True)
                
                st.subheader("👟 Step Count Tracker")
                step_order = ["Under 1k", "1k-2k", "2k-3k", "3k-5k", "5k+"]
                st.altair_chart(alt.Chart(df).mark_rect().encode(
                    x='Day:O', y=alt.Y('Month:O', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                    color=alt.Color('steps:O', scale=alt.Scale(scheme='greens'), sort=step_order), tooltip=['log_date', 'steps']
                ).properties(height=200), use_container_width=True)

            with tab2:
                st.subheader("🌟 Overall Day Rating")
                st.altair_chart(alt.Chart(df).mark_rect().encode(
                    x='Day:O', y=alt.Y('Month:O', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                    color=alt.Color('rating:Q', scale=alt.Scale(scheme='yellowgreen')), tooltip=['log_date', 'rating', 'highlight']
                ).properties(height=200), use_container_width=True)

                st.subheader("😰 Anxiety Grid")
                st.altair_chart(alt.Chart(df).mark_rect().encode(
                    x='Day:O', y=alt.Y('Month:O', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                    color=alt.Color('anxiety:Q', scale=alt.Scale(scheme='oranges')), tooltip=['log_date', 'anxiety', 'mood']
                ).properties(height=200), use_container_width=True)

                st.subheader("📚 Study Hours")
                st.altair_chart(alt.Chart(df).mark_rect().encode(
                    x='Day:O', y=alt.Y('Month:O', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                    color=alt.Color('study_time:Q', scale=alt.Scale(scheme='tealblues')), tooltip=['log_date', 'study_time']
                ).properties(height=200), use_container_width=True)
                
                st.subheader("📱 Screen Time")
                st.altair_chart(alt.Chart(df).mark_rect().encode(
                    x='Day:O', y=alt.Y('Month:O', sort=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
                    color=alt.Color('screen_time:Q', scale=alt.Scale(scheme='reds')), tooltip=['log_date', 'screen_time']
                ).properties(height=200), use_container_width=True)

            with tab3:
                st.subheader("📖 My Complete Diary")
                display_df = df.drop(columns=['username'])
                st.dataframe(display_df.sort_values(by="log_date", ascending=False))