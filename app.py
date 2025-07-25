# app.py
try:
    import streamlit as st
except ModuleNotFoundError:
    raise RuntimeError("streamlit 모듈이 설치되지 않았습니다. 'pip install streamlit' 명령어로 설치해주세요.")

import openai
import os
from datetime import date, datetime
from supabase_client import SupabaseClient
from gpt_agent import get_gpt_response

# Load environment
from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- LANGUAGE SUPPORT (must be at the top) ---
languages = {"한국어": "ko", "English": "en"}
lang = st.sidebar.selectbox("언어 / Language", list(languages.keys()), index=0)
lang_code = languages[lang]

# Translation dictionary
T = {
    "ko": {
        "user_settings": "👤 사용자 설정",
        "nickname": "닉네임",
        "nickname_ph": "훈련병 철수",
        "gender": "성별",
        "height": "신장(cm)",
        "height_ph": "예: 175",
        "weight": "체중(kg)",
        "weight_ph": "예: 70",
        "inbody": "InBody 정보 (선택)",
        "inbody_ph": "골격근량, 체지방량 등",
        "goal": "운동 목표",
        "style": "GPT 응답 스타일",
        "start": "🚀 시작하기",
        "current_rank": "🪖 현재 계급:",
        "condition_check": "📋 오늘 컨디션 체크",
        "condition_slider": "오늘 몸 상태는 어떤가요?",
        "routine_btn": "✅ 루틴 추천받기",
        "routine": "🏋️ 추천 루틴",
        "gpt_feedback": "💬 **GPT 피드백:**",
        "routine_saved": "✅ 오늘 루틴이 저장되었습니다!",
        "history": "📆 지난 기록 보기",
        "input_nickname": "좌측에서 닉네임을 입력하고 시작해주세요.",
        "rank_up": "축하합니다! 계급이 {prev} → {curr}로 승급했습니다!"
    },
    "en": {
        "user_settings": "👤 User Settings",
        "nickname": "Nickname",
        "nickname_ph": "Private Kim",
        "gender": "Gender",
        "height": "Height (cm)",
        "height_ph": "e.g. 175",
        "weight": "Weight (kg)",
        "weight_ph": "e.g. 70",
        "inbody": "InBody Info (optional)",
        "inbody_ph": "Skeletal muscle, body fat, etc.",
        "goal": "Fitness Goal",
        "style": "GPT Response Style",
        "start": "🚀 Start",
        "current_rank": "🪖 Current Rank:",
        "condition_check": "📋 Today's Condition Check",
        "condition_slider": "How do you feel today?",
        "routine_btn": "✅ Get Routine",
        "routine": "🏋️ Recommended Routine",
        "gpt_feedback": "💬 **GPT Feedback:**",
        "routine_saved": "✅ Today's routine has been saved!",
        "history": "📆 View Past Records",
        "input_nickname": "Please enter your nickname on the left to start.",
        "rank_up": "Congratulations! Your rank has advanced from {prev} to {curr}!"
    }
}



# Initialize DB client
supabase = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="훈련병코치 Bootcamper", page_icon="💪")
st.title("💪 훈련병코치 Bootcamper")

# --- SESSION STATE ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "style" not in st.session_state:
    st.session_state.style = None
if "nickname" not in st.session_state:
    st.session_state.nickname = None

# --- AUTH UI ---
if "user" not in st.session_state:
    st.session_state.user = None

from supabase import create_client

# Auth UI
if st.session_state.user is None:
    auth_action = st.sidebar.radio("Login or Signup" if lang_code=="en" else "로그인 또는 회원가입", ["Login", "Signup"] if lang_code=="en" else ["로그인", "회원가입"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button(auth_action):
        if auth_action in ["Signup", "회원가입"]:
            res = supabase.supabase.auth.sign_up({"email": email, "password": password})
            if res.user:
                st.session_state.user = res.user
                st.success("Signed up! Please complete your profile." if lang_code=="en" else "회원가입 성공! 프로필을 완성해주세요.")
            else:
                st.error("Signup failed.")
        else:
            res = supabase.supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                st.session_state.user = res.user
                st.success("Logged in!" if lang_code=="en" else "로그인 성공!")
            else:
                st.error("Login failed.")
    # Password reset
    if st.sidebar.button("Forgot Password?" if lang_code=="en" else "비밀번호 재설정"):
        if email:
            res = supabase.supabase.auth.reset_password_for_email(email)
            if not res.get("error"):
                st.success("Password reset email sent!" if lang_code=="en" else "비밀번호 재설정 이메일이 전송되었습니다!")
            else:
                st.error("Failed to send reset email." if lang_code=="en" else "재설정 이메일 전송 실패.")
        else:
            st.warning("Please enter your email above." if lang_code=="en" else "이메일을 입력해주세요.")
else:
    st.sidebar.write(f"Logged in as: {st.session_state.user.email}")
    # Email verification warning
    if st.session_state.user and not getattr(st.session_state.user, 'email_confirmed_at', None):
        st.warning("Please verify your email address. Check your inbox for a confirmation email." if lang_code=="en" else "이메일 인증을 완료해주세요. 받은 편지함을 확인하세요.")
    if st.sidebar.button("Logout" if lang_code=="en" else "로그아웃"):
        st.session_state.user = None
        st.session_state.user_id = None
        st.session_state.nickname = None
        st.session_state.style = None
        st.session_state.prev_rank = None

# --- PROFILE ONBOARDING/UPDATE ---
if st.session_state.user:
    user_id = st.session_state.user.id
    # Fetch user profile from users table
    user_profile = supabase.get_user(user_id)
    if not user_profile:
        # New user, ask for profile info
        st.sidebar.header(T[lang_code]["user_settings"])
        nickname = st.sidebar.text_input(T[lang_code]["nickname"], placeholder=T[lang_code]["nickname_ph"])
        gender = st.sidebar.selectbox(T[lang_code]["gender"], ["남성", "여성", "기타", "비공개"] if lang_code=="ko" else ["Male", "Female", "Other", "Private"])
        height = st.sidebar.text_input(T[lang_code]["height"], placeholder=T[lang_code]["height_ph"], max_chars=5)
        weight = st.sidebar.text_input(T[lang_code]["weight"], placeholder=T[lang_code]["weight_ph"], max_chars=5)
        inbody = st.sidebar.text_area(T[lang_code]["inbody"], placeholder=T[lang_code]["inbody_ph"])
        goal = st.sidebar.selectbox(T[lang_code]["goal"], ["체지방 감량", "근육 증가", "특전사 체력", "건강 유지", "혼합"] if lang_code=="ko" else ["Fat Loss", "Muscle Gain", "Special Forces Fitness", "Health Maintenance", "Mixed"])
        style = st.sidebar.selectbox(T[lang_code]["style"], ["조교", "친구", "연인", "세계 최고의 트레이너"] if lang_code=="ko" else ["Drill Sergeant", "Friend", "Lover", "Elite Trainer"])
        if st.sidebar.button(T[lang_code]["start"]):
            user = supabase.create_user_with_id(user_id, nickname, gender, height, weight, inbody, goal, style)
            st.session_state.user_id = user_id
            st.session_state.style = style
            st.session_state.nickname = nickname
            st.success(f"{nickname}님, 훈련 시작합니다!" if lang_code=="ko" else f"{nickname}, training started!")
    else:
        st.session_state.user_id = user_id
        st.session_state.style = user_profile["style"]
        st.session_state.nickname = user_profile["nickname"]

# --- 계급 계산 함수 ---
def calculate_rank(start_date_str):
    if not start_date_str:
        return "훈련병"
    days = (datetime.today().date() - datetime.fromisoformat(start_date_str).date()).days
    if days < 42:
        return "훈련병"
    elif days < 91:
        return "이병"
    elif days < 181:
        return "일병"
    elif days < 366:
        return "상병"
    elif days < 500:
        return "병장"
    elif days < 700:
        return "하사"
    elif days < 1000:
        return "중사"
    elif days < 1200:
        return "상사"
    elif days < 1500:
        return "준장"
    elif days < 1800:
        return "중장"
    elif days < 2100:
        return "대장"
    else:
        return "원수"




# --- MAIN UI ---
if st.session_state.user_id:
    user_data = supabase.get_user(st.session_state.user_id)
    rank = calculate_rank(user_data.get("created_at"))
    # Rank badge mapping
    rank_badges = {
        "훈련병": "🟢", "이병": "🔵", "일병": "🟣", "상병": "🟠", "병장": "🟡",
        "하사": "⚫️", "중사": "⚪️", "상사": "🟤", "준장": "⭐️", "중장": "🌟", "대장": "🏅", "원수": "👑"
    }
    badge = rank_badges.get(rank, "🎖️")
    st.markdown(f"### {T[lang_code]['current_rank']} {badge} **{rank}**")

    # Congratulatory message for rank up
    if "prev_rank" not in st.session_state:
        st.session_state.prev_rank = rank
    elif st.session_state.prev_rank != rank:
        st.success(T[lang_code]["rank_up"].format(prev=st.session_state.prev_rank, curr=rank))
        st.session_state.prev_rank = rank

    st.subheader(T[lang_code]["condition_check"])
    condition = st.slider(T[lang_code]["condition_slider"], 1, 10, 5)
    # Mood, energy, sleep fields
    mood_options = ["좋음", "보통", "나쁨"] if lang_code=="ko" else ["Good", "Normal", "Bad"]
    energy_options = ["충만", "보통", "피곤"] if lang_code=="ko" else ["Full", "Normal", "Tired"]
    sleep_options = ["충분", "보통", "부족"] if lang_code=="ko" else ["Enough", "Normal", "Lack"]
    mood = st.selectbox("기분" if lang_code=="ko" else "Mood", mood_options)
    energy = st.selectbox("에너지" if lang_code=="ko" else "Energy", energy_options)
    sleep = st.selectbox("수면" if lang_code=="ko" else "Sleep", sleep_options)
    if st.button(T[lang_code]["routine_btn"]):
        # Build a structured prompt
        prompt = (
            f"[사용자 정보]\n"
            f"닉네임: {user_data['nickname']}\n"
            f"성별: {user_data['gender']}\n"
            f"키: {user_data['height']}\n"
            f"체중: {user_data['weight']}\n"
            f"InBody: {user_data.get('inbody', '')}\n"
            f"목표: {user_data['goal']}\n"
            f"계급: {rank}\n"
            f"GPT 응답 스타일: {user_data['style']}\n"
            f"오늘 컨디션: {condition}/10\n"
            f"기분: {mood}\n"
            f"에너지: {energy}\n"
            f"수면: {sleep}\n"
            "\n[요청]\n"
            "위 사용자 정보를 바탕으로 오늘의 맞춤 운동 루틴을 추천해줘. 반드시 아래의 형식과 예시를 참고해서 답변해줘.\n"
        )
        gpt_text, routine_json, feedback = get_gpt_response(prompt, st.session_state.style)
        st.text_area(T[lang_code]["routine"], value=gpt_text, height=200)
        st.markdown(f"{T[lang_code]['gpt_feedback']} {feedback}")

        # Save to Supabase
        supabase.log_session(
            user_id=st.session_state.user_id,
            date_str=str(date.today()),
            condition=condition,
            routine=routine_json,
            feedback=feedback,
            mood=mood,
            energy=energy,
            sleep=sleep
        )
        st.success(T[lang_code]["routine_saved"])

    st.divider()
    st.subheader(T[lang_code]["history"])
    history = supabase.get_user_sessions(st.session_state.user_id)
    for entry in history:
        st.markdown(f"**{entry['date']}**: 컨디션 {entry['condition']} / 기분 {entry.get('mood', '')} / 에너지 {entry.get('energy', '')} / 수면 {entry.get('sleep', '')} / 루틴 요약 → {entry['feedback']}")
else:
    st.info(T[lang_code]["input_nickname"])
