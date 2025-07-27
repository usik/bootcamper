# app.py
try:
    import streamlit as st
except ModuleNotFoundError:
    raise RuntimeError("streamlit 모듈이 설치되지 않았습니다. 'pip install streamlit' 명령어로 설치해주세요.")

import openai
import os
from datetime import date, datetime
from supabase_client import SupabaseClient
from gpt_agent import get_gpt_response, load_prompt
import logging
import re
import random

# --- MOTIVATIONAL QUOTES ---
QUOTES = {
    "ko": [
        "오늘의 작은 실천이 내일의 큰 변화를 만듭니다!",
        "포기하지 마세요. 꾸준함이 힘입니다.",
        "운동은 나를 위한 최고의 투자입니다.",
        "오늘도 한 걸음 더!",
        "힘들수록 성장하는 중입니다."
    ],
    "en": [
        "Small steps today, big changes tomorrow!",
        "Don't give up. Consistency is power.",
        "Exercise is the best investment in yourself.",
        "One step further, every day!",
        "Struggle means you're growing."
    ]
}

# --- FAQ CONTENT ---
FAQS = {
    "ko": [
        ("이 앱은 어떻게 사용하나요?", "회원가입 후 프로필을 입력하고, 매일 컨디션을 체크하면 AI가 맞춤 운동 루틴을 추천해줍니다."),
        ("운동 기록은 어디서 볼 수 있나요?", "메인 화면 하단의 '지난 기록 보기'에서 확인할 수 있습니다."),
        ("AI 트레이너는 무엇인가요?", "GPT 기반의 AI가 여러분의 컨디션과 목표에 맞춰 운동을 코칭해줍니다."),
    ],
    "en": [
        ("How do I use this app?", "Sign up, complete your profile, and check in daily. The AI will recommend a personalized workout routine."),
        ("Where can I see my workout history?", "Scroll down to 'View Past Records' on the main screen."),
        ("What is the AI Trainer?", "A GPT-powered AI that coaches you based on your condition and goals."),
    ]
}

# --- STREAK TRACKER ---
def get_streak(history):
    streak = 0
    today = date.today()
    for entry in history:
        entry_date = datetime.fromisoformat(entry['date']).date()
        if (today - entry_date).days == streak:
            streak += 1
        else:
            break
    return streak

# Set up logging for errors
logging.basicConfig(filename='app_errors.log', level=logging.ERROR)

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

def is_valid_email(email):
    # Simple regex for email validation
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

if st.session_state.user is None:
    auth_action = st.sidebar.radio("Login or Signup" if lang_code=="en" else "로그인 또는 회원가입", ["Login", "Signup"] if lang_code=="en" else ["로그인", "회원가입"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button(auth_action):
        if not email or not password:
            st.error("Please enter both email and password." if lang_code=="en" else "이메일과 비밀번호를 모두 입력해주세요.")
        elif not is_valid_email(email):
            st.error("Please enter a valid email address." if lang_code=="en" else "유효한 이메일 주소를 입력해주세요.")
        else:
            if auth_action in ["Signup", "회원가입"]:
                try:
                    res = supabase.supabase.auth.sign_up({"email": email, "password": password})
                    if hasattr(res, 'user') and res.user:
                        st.session_state.user = res.user
                        st.success("Signed up! Please complete your profile." if lang_code=="en" else "회원가입 성공! 프로필을 완성해주세요.")
                    elif hasattr(res, 'error') and res.error:
                        if 'already registered' in str(res.error).lower() or 'user already exists' in str(res.error).lower():
                            st.error("This email is already registered. Please log in instead." if lang_code=="en" else "이미 등록된 이메일입니다. 로그인 해주세요.")
                        else:
                            st.error("Signup failed. Please try again later." if lang_code=="en" else "회원가입에 실패했습니다. 다시 시도해주세요.")
                    else:
                        st.error("Signup failed. Please try again later." if lang_code=="en" else "회원가입에 실패했습니다. 다시 시도해주세요.")
                except Exception as e:
                    if 'already registered' in str(e).lower() or 'user already exists' in str(e).lower():
                        st.error("This email is already registered. Please log in instead." if lang_code=="en" else "이미 등록된 이메일입니다. 로그인 해주세요.")
                    else:
                        st.error("Signup failed. Please try again later." if lang_code=="en" else "회원가입에 실패했습니다. 다시 시도해주세요.")
            else:
                try:
                    res = supabase.supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if hasattr(res, 'user') and res.user:
                        st.session_state.user = res.user
                        st.success("Logged in!" if lang_code=="en" else "로그인 성공!")
                    elif hasattr(res, 'error') and res.error:
                        st.error("Login failed. Please check your email and password." if lang_code=="en" else "로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.")
                    else:
                        st.error("Login failed. Please try again later." if lang_code=="en" else "로그인에 실패했습니다. 다시 시도해주세요.")
                except Exception as e:
                    st.error("Login failed. Please try again later." if lang_code=="en" else "로그인에 실패했습니다. 다시 시도해주세요.")
    # Password reset
    if st.sidebar.button("Forgot Password?" if lang_code=="en" else "비밀번호 재설정"):
        if not email:
            st.warning("Please enter your email above." if lang_code=="en" else "이메일을 입력해주세요.")
        elif not is_valid_email(email):
            st.error("Please enter a valid email address." if lang_code=="en" else "유효한 이메일 주소를 입력해주세요.")
        else:
            try:
                res = supabase.supabase.auth.reset_password_for_email(email)
                if not res.get("error"):
                    st.success("Password reset email sent!" if lang_code=="en" else "비밀번호 재설정 이메일이 전송되었습니다!")
                else:
                    st.error("Failed to send reset email. Please try again later." if lang_code=="en" else "재설정 이메일 전송에 실패했습니다. 다시 시도해주세요.")
            except Exception as e:
                st.error("Failed to send reset email. Please try again later." if lang_code=="en" else "재설정 이메일 전송에 실패했습니다. 다시 시도해주세요.")
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

# --- PROFILE ONBOARDING/UPDATE & MAIN UI ---
if st.session_state.user:
    user_id = st.session_state.user.id
    user_profile = supabase.get_user(user_id)
    if not user_profile and not st.session_state.get("user_id"):
        # Show onboarding form (nickname, gender, etc.)
        st.sidebar.header(T[lang_code]["user_settings"])
        nickname = st.sidebar.text_input(T[lang_code]["nickname"], placeholder=T[lang_code]["nickname_ph"])
        gender = st.sidebar.selectbox(T[lang_code]["gender"], ["남성", "여성", "기타", "비공개"] if lang_code=="ko" else ["Male", "Female", "Other", "Private"])
        height = st.sidebar.text_input(T[lang_code]["height"], placeholder=T[lang_code]["height_ph"], max_chars=5)
        weight = st.sidebar.text_input(T[lang_code]["weight"], placeholder=T[lang_code]["weight_ph"], max_chars=5)
        inbody = st.sidebar.text_area(T[lang_code]["inbody"], placeholder=T[lang_code]["inbody_ph"])
        goal = st.sidebar.selectbox(T[lang_code]["goal"], ["체지방 감량", "근육 증가", "특전사 체력", "건강 유지", "혼합"] if lang_code=="ko" else ["Fat Loss", "Muscle Gain", "Special Forces Fitness", "Health Maintenance", "Mixed"])
        style = st.sidebar.selectbox(T[lang_code]["style"], ["조교", "친구", "연인", "세계 최고의 트레이너"] if lang_code=="ko" else ["Drill Sergeant", "Friend", "Lover", "Elite Trainer"])
        if st.sidebar.button(T[lang_code]["start"]):
            try:
                user = supabase.create_user_with_id(user_id, nickname, gender, height, weight, inbody, goal, style)
                st.session_state.user_id = user_id
                st.session_state.style = style
                st.session_state.nickname = nickname
                st.success(f"{nickname}님, 훈련 시작합니다!" if lang_code=="ko" else f"{nickname}, training started!")
            except Exception as e:
                st.error("Profile creation failed. Please try again later." if lang_code=="en" else "프로필 생성에 실패했습니다. 다시 시도해주세요.")
        st.info("프로필 정보를 입력하고 시작해주세요." if lang_code=="ko" else "Please complete your profile to get started.")
    elif st.session_state.get("user_id"):
        # Show main UI
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
            spinner_msg = "루틴을 생성 중입니다... 잠시만 기다려주세요!" if lang_code=="ko" else "Generating your routine... Please wait!"
            with st.spinner(spinner_msg):
                # Get previous session summary for prompt
                history = supabase.get_user_sessions(st.session_state.user_id)
                prev_summary = ""
                if history:
                    last = history[0]
                    prev_summary = (
                        f"[이전 세션 요약]\n"
                        f"날짜: {last['date']}\n"
                        f"컨디션: {last.get('condition', '')}\n"
                        f"기분: {last.get('mood', '')}\n"
                        f"에너지: {last.get('energy', '')}\n"
                        f"수면: {last.get('sleep', '')}\n"
                        f"피드백: {last.get('feedback', '')}\n"
                    )
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
                    f"{prev_summary}"
                    "\n[요청]\n"
                    "위 사용자 정보를 바탕으로 오늘의 맞춤 운동 루틴을 추천해줘. 반드시 아래의 형식과 예시를 참고해서 답변해줘.\n"
                )
                gpt_text, routine_json, feedback = get_gpt_response(prompt, st.session_state.style)
                # Show GPT summary/feedback clearly
                st.markdown("#### 📝 요약 및 피드백" if lang_code=="ko" else "#### 📝 Summary & Feedback")
                st.text_area(T[lang_code]["routine"], value=gpt_text, height=120)
                st.markdown(f"{T[lang_code]['gpt_feedback']} {feedback}")
                # Display the actual routine as a readable list and improved table if available
                routine_done = False
                if routine_json and "routine" in routine_json:
                    st.markdown("#### 오늘의 운동 루틴" if lang_code=="ko" else "#### Today's Workout Routine")
                    # Bullet list
                    for step in routine_json["routine"]:
                        desc = []
                        if "운동" in step:
                            desc.append(step["운동"])
                        if "세트" in step:
                            desc.append(f"{step['세트']}세트" if lang_code=="ko" else f"{step['세트']} sets")
                        if "반복" in step:
                            reps = step["반복"]
                            # Format reps/time
                            if isinstance(reps, (int, float)):
                                if "분" in str(reps) or "min" in str(reps):
                                    reps_str = f"{round(float(reps), 1)}분" if lang_code=="ko" else f"{round(float(reps), 1)} min"
                                else:
                                    reps_str = f"{int(round(float(reps)))}회" if lang_code=="ko" else f"{int(round(float(reps)))} reps"
                            elif any(x in str(reps) for x in ["분", "min", "minute", "minutes"]):
                                reps_str = f"{reps}" if lang_code=="ko" else f"{reps} min"
                            else:
                                reps_str = f"{reps}회" if lang_code=="ko" else f"{reps} reps"
                            desc.append(reps_str)
                        if "중량" in step:
                            weight = step["중량"]
                            if "%" in str(weight):
                                weight_str = f"{weight}"  # Already has %
                            else:
                                weight_str = f"{weight}kg" if lang_code=="ko" else f"{weight} kg"
                            desc.append(weight_str)
                        st.markdown("- " + ", ".join(desc))
                    # Improved table
                    def format_cell(val, key):
                        if key == "반복":
                            if isinstance(val, (int, float)):
                                if "분" in str(val) or "min" in str(val):
                                    return f"{round(float(val), 1)}분" if lang_code=="ko" else f"{round(float(val), 1)} min"
                                else:
                                    return f"{int(round(float(val)))}회" if lang_code=="ko" else f"{int(round(float(val)))} reps"
                            elif any(x in str(val) for x in ["분", "min", "minute", "minutes"]):
                                return f"{val}" if lang_code=="ko" else f"{val} min"
                            else:
                                return f"{val}회" if lang_code=="ko" else f"{val} reps"
                        if key == "중량":
                            if "%" in str(val):
                                return val
                            else:
                                return f"{val}kg" if lang_code=="ko" else f"{val} kg"
                        return val
                    # Format table data
                    formatted_table = []
                    for row in routine_json["routine"]:
                        formatted_row = {k: format_cell(v, k) for k, v in row.items()}
                        formatted_table.append(formatted_row)
                    st.table(formatted_table)
                    # Routine Done Button
                    if st.button("✅ 오늘 루틴 완료!" if lang_code=="ko" else "✅ Mark Routine as Done!"):
                        routine_done = True
                        st.success("오늘의 루틴을 완료했습니다!" if lang_code=="ko" else "You completed today's routine!")
                        st.balloons()
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
                # Show streak and progress bar
                streak = get_streak(history)
                st.markdown(f"🔥 {'연속 출석' if lang_code=='ko' else 'Daily Streak'}: {streak}일" if lang_code=="ko" else f"🔥 Daily Streak: {streak} days")
                st.progress(min(streak/7, 1.0), text=("7일 연속 출석까지!" if lang_code=="ko" else "To 7-day streak!"))
                if streak > 0 and streak % 7 == 0:
                    st.snow()
                # Motivational quote
                st.info(random.choice(QUOTES[lang_code]))

            st.divider()
            st.subheader(T[lang_code]["history"])
            history = supabase.get_user_sessions(st.session_state.user_id)
            for entry in history:
                st.markdown(f"**{entry['date']}**: 컨디션 {entry['condition']} / 기분 {entry.get('mood', '')} / 에너지 {entry.get('energy', '')} / 수면 {entry.get('sleep', '')} / 루틴 요약 → {entry['feedback']}")

            # Progress graph for mood/energy/sleep
            if history:
                import pandas as pd
                df = pd.DataFrame(history)
                df = df.sort_values("date")
                cols = []
                if "mood" in df.columns:
                    cols.append("mood")
                if "energy" in df.columns:
                    cols.append("energy")
                if "sleep" in df.columns:
                    cols.append("sleep")
                if cols:
                    st.line_chart(df.set_index("date")[cols])

            # --- Chat-like UI with AI Trainer ---
            st.divider()
            st.subheader("💬 AI 트레이너와 대화하기" if lang_code=="ko" else "💬 Chat with AI Trainer")
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
            user_chat_input = st.chat_input("AI 트레이너에게 질문해보세요!" if lang_code=="ko" else "Ask your AI trainer anything!")
            if user_chat_input:
                st.session_state.chat_history.append({"role": "user", "content": user_chat_input})
                # Build chat prompt history for GPT
                chat_messages = []
                for msg in st.session_state.chat_history:
                    chat_messages.append({"role": msg["role"], "content": msg["content"]})
                # Add system prompt for style
                system_prompt = load_prompt(st.session_state.style if "style" in st.session_state else "세계 최고의 트레이너")
                chat_messages = ([{"role": "system", "content": system_prompt}] + chat_messages)
                with st.spinner("AI 트레이너가 답변 중입니다..." if lang_code=="ko" else "AI trainer is typing..."):
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        st.error("OPENAI_API_KEY is not set.")
                    else:
                        client = openai.OpenAI(api_key=api_key)
                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=chat_messages,
                            temperature=0.8
                        )
                        ai_reply = response.choices[0].message.content.strip()
                        st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
                        st.chat_message("assistant").write(ai_reply)
    else:
        st.info("프로필 정보를 입력하고 시작해주세요." if lang_code=="ko" else "Please complete your profile to get started.")

# FAQ/help section in sidebar
with st.sidebar.expander("❓ 자주 묻는 질문" if lang_code=="ko" else "❓ FAQ / Help"):
    for q, a in FAQS[lang_code]:
        st.markdown(f"**Q: {q}**\n- {a}")
