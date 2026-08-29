import json
import os
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from openai import OpenAI
from pydantic import BaseModel, Field

# 🔑 [API 키 및 파일 설정]
SAVE_FILE = "rpg_sync_text_save.json"
LOG_FILE = "rpg_story_log.txt"

st.set_page_config(
    page_title="텍스트 RPG", page_icon="⚔️", layout="wide"
)
st.title("⚔️ 텍스트 실시간 RPG")
st.markdown(
    "AI가 매 턴마다 갱신하는 캐릭터 상태 정보 블록을 좌측 슬라이드바에 그대로 반영하는 판타지 RPG입니다."
)

# 🎨 [스크롤 위치 복원 JS]
st.markdown(
    """
    <script>
        (function() {
            const pWin = window.parent || window;
            const pDoc = pWin.document;
            const SCROLL_KEY = 'rpg_sync_text_scroll';
            function getScrollContainer() {
                return pDoc.querySelector('[data-testid="stAppViewContainer"]') || pDoc.querySelector('.main') || pWin;
            }
            const container = getScrollContainer();
            const savePos = function() {
                const pos = (container !== pWin) ? container.scrollTop : (pWin.pageYOffset || pDoc.documentElement.scrollTop);
                pWin.sessionStorage.setItem(SCROLL_KEY, pos);
            };
            if (container !== pWin) { container.addEventListener('scroll', savePos, { passive: true }); }
            else { pWin.addEventListener('scroll', savePos, { passive: true }); }
            function restoreScroll() {
                const saved = pWin.sessionStorage.setItem(SCROLL_KEY);
                if (saved !== null) {
                    const targetPos = parseInt(saved, 10);
                    const cont = getScrollContainer();
                    if (cont !== pWin) { cont.scrollTop = targetPos; } else { pWin.scrollTo(0, targetPos); }
                }
            }
            setTimeout(restoreScroll, 50);
            setTimeout(restoreScroll, 200);
        })();
    </script>
    """,
    unsafe_allow_html=True,
)


# 📋 [AI 응답 스키마]
class SyncTextRPGResponse(BaseModel):
    narrative: str = Field(
        description=" 상세한 현장 묘사 와 몰입감 있는 스토리 서사 묘사. 주플레이어의 행동에 따라 서사를 진행하고, 하단의 형식에 맞춰 캐릭터의 상태 동기화 텍스트(status_sync_text)를 반드시 최신 상태로 갱신하여 제공하세요."
    )
    status_sync_text: str = Field(
        description=(
            "현재 캐릭터의 상태를 보여주는 텍스트 블록. 반드시 항목별로 줄바꿈을 포함하여 작성하세요. 예시 형식:\n"
            "종족: 엘프\n"
            "직업: 마법사\n"
            "레벨: 1 (경험치: 0/100)\n"
            "체력(HP): 60/60\n"
            "마나(MP): 30/30\n"
            "골드: 20G\n"
            "장착 장비: 무기: 초보자의 무기, 갑옷: 여행자 가죽옷\n"
            "인벤토리: 체력 포션 (소), 마력 회복의 반지\n"
            "사용가능한 마법 및 기술: 마력탄, 방패술\n"
        )
    )
    choices: list[str] = Field(
        description="플레이어가 다음에 선택할 수 있는 행동지침 3~4가지"
    )


# 💾 [기본 데이터 및 세이브/로드 관리]
default_sync_text = (
    "종족: 미정\n"
    "직업: 미정\n"
    "레벨: 1 (경험치: 0/100)\n"
    "체력(HP): 60/60\n"
    "마나(MP): 30/30\n"
    "골드: 50G\n"
    "장착 장비: 무기: 초보자의 무기, 갑옷: 여행자 가죽옷\n"
    "사용가능한 마법 및 기술: 마력탄, 방패술\n"
    "인벤토리: 체력 포션 (소), 체력 포션 (소)\n"
)

def save_game():
    data = {
        "status_sync_text": st.session_state.get("status_sync_text", default_sync_text),
        "history": st.session_state.get("history", []),
        "game_concept": st.session_state.get("game_concept", ""),
    }
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def append_ai_log(narrative):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{narrative}\n\n" + "-" * 50 + "\n\n")


# 📊 [세션 초기화]
saved_data = None
if os.path.exists(SAVE_FILE):
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
    except Exception:
        pass

if "status_sync_text" not in st.session_state:
    st.session_state.status_sync_text = (
        saved_data.get("status_sync_text", default_sync_text)
        if saved_data
        else default_sync_text
    )

if "history" not in st.session_state:
    st.session_state.history = (
        saved_data.get("history", []) if saved_data else []
    )

if "game_concept" not in st.session_state:
    st.session_state.game_concept = (
        saved_data.get("game_concept", "인간의 본성을 파고드는 사랑, 전우애, 질투, 시기, 배신, 집단의 갈등, 모략 상세하고 몰입감 있는 스토리 서사 묘사. 주인공은 단지 전투만 하는게 아니라 판타지세상 에서 실제처럼 생존합니다 플레이어의 행동에 따라 서사를 진행하고, 하단의 형식에 맞춰 캐릭터의 상태 동기화 텍스트(status_sync_text)를 반드시 최신 상태로 갱신하여 제공하세요")
        if saved_data
        else "인간의 본성을 파고드는 사랑, 전우애, 질투, 시기, 배신, 집단의 갈등, 모략 상세하고 몰입감 있는 스토리 서사 묘사. 주인공은 단지 전투만 하는게 아니라 판타지세상 에서 실제처럼 생존합니다 플레이어의 행동에 따라 서사를 진행하고, 하단의 형식에 맞춰 캐릭터의 상태 동기화 텍스트(status_sync_text)를 반드시 최신 상태로 갱신하여 제공하세요"
    )


# ⚙️ [사이드바 UI]
st.sidebar.header("⚙️ 게임 설정 및 AI 선택")

ai_provider = st.sidebar.selectbox("🤖 AI 제공자 선택", ["Google Gemini", "Groq"])

api_key_input = ""
selected_model = ""

if ai_provider == "Google Gemini":
    api_key_input = st.sidebar.text_input("Google Gemini API 키 입력", type="password")
    selected_model = st.sidebar.selectbox(
        "Gemini 모델 선택",
        options=[
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash-lite",
        ],
        index=0,
    )
else:
    api_key_input = st.sidebar.text_input("Groq API 키 입력", type="password")
    groq_model_option = st.sidebar.selectbox(
        "Groq 모델 선택",
        options=[
            "openai/gpt-oss-20b",
            "직접 입력",
        ],
        index=0,
    )
    if groq_model_option == "직접 입력":
        selected_model = st.sidebar.text_input("사용할 Groq 모델명 입력", value="llama-3.1-8b-instant")
    else:
        selected_model = groq_model_option

font_size = st.sidebar.slider("🔤 글자 크기", 12, 26, 16, 1)

# 🎭 [게임 컨셉 입력창 추가]
st.sidebar.markdown("---")
st.sidebar.subheader("🎭 게임 컨셉 및 세계관 설정")
game_concept_input = st.sidebar.text_area(
    "게임 방향성을 자유롭게 입력하세요",
    value=st.session_state.game_concept,
    height=100,
    help="AI가 이 컨셉을 바탕으로 스토리를 진행합니다. (예: 어두운 다크 판타지, 사이버펑크 모험, 개그 코미디 세계관 등)"
)
if game_concept_input != st.session_state.game_concept:
    st.session_state.game_concept = game_concept_input
    save_game()

# 🎨 [글자 크기 CSS]
st.markdown(
    f"""
    <style>
        .stChatMessage p, .stChatMessage div {{ font-size: {font_size}px !important; line-height: 1.6 !important; }}
        div.stButton > button, div.stButton > button p {{
            font-size: {font_size + 4}px !important;
            font-weight: bold !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 현재 캐릭터 상태 동기화 정보")

clean_status = (
    st.session_state.status_sync_text
    .replace('"', '')
    .replace('{', '')
    .replace('}', '')
    .replace('[', '')
    .replace(']', '')
)

keys_to_break = [
    "직업:", "레벨:", "체력(HP):", "마나(MP):", 
    "골드:", "장착 장비:", "인벤토리:", "사용가능한 마법 및 기술:"
]
for key in keys_to_break:
    clean_status = clean_status.replace(key, f"\n{key}")

st.sidebar.text(clean_status)

# 💾 [세이브/로드 다운로드 섹션]
st.sidebar.markdown("---")
st.sidebar.subheader("💾 세이브 & 로드 관리")

if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        json_data_str = f.read()
    st.sidebar.download_button(
        label="📥 게임 상태 파일 저장 (다운로드)",
        data=json_data_str,
        file_name="rpg_sync_text_save.json",
        mime="application/json",
        use_container_width=True,
    )

uploaded_file = st.sidebar.file_uploader(
    "📂 세이브 파일 불러오기 (업로드)", type=["json"]
)
if uploaded_file is not None:
    try:
        loaded_data = json.load(uploaded_file)
        if "status_sync_text" in loaded_data and "history" in loaded_data:
            st.session_state.status_sync_text = loaded_data["status_sync_text"]
            st.session_state.history = loaded_data["history"]
            st.session_state.game_concept = loaded_data.get("game_concept", st.session_state.game_concept)
            save_game()
            st.sidebar.success("🎉 게임을 성공적으로 불러왔습니다!")
            st.rerun()
        else:
            st.sidebar.error("❌ 올바르지 않은 세이브 파일 형식입니다.")
    except Exception as e:
        st.sidebar.error(f"❌ 파일을 읽는 중 오류 발생: {e}")

if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_data_str = f.read()
    st.sidebar.download_button(
        label="📜 전체 스토리 로그 다운로드 (TXT)",
        data=log_data_str,
        file_name="rpg_story_log.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.sidebar.markdown("---")
if st.sidebar.button("🔄 전체 초기화 및 새 게임", use_container_width=True):
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# 🤖 [AI 호출 함수]
def call_ai_sync_text(user_action):
    concept_str = st.session_state.game_concept.strip()
    concept_instruction = f"\n\n[주요 게임 컨셉 및 배경 설정]\n{concept_str}\n위 컨셉과 분위기를 강력하게 반영하여 스토리를 전개하세요." if concept_str else ""

    system_instruction = (
        "당신은 판타지 RPG의 친절하고 다정한 게임 마스터(GM)입니다."
        f"{concept_instruction}\n\n"
        "플레이어의 행동에 따라 이야기를 진행하고, 하단의 형식에 맞춰 캐릭터의 상태 동기화 텍스트(status_sync_text)를 반드시 최신 상태로 갱신하여 제공하세요.\n\n"
        "status_sync_text 형식 예시:\n"
        "종족: 엘프\n"
        "직업: 마법사\n"
        "레벨: 1 (경험치: 0/100)\n"
        "체력(HP): 60/60\n"
        "마나(MP): 30/30\n"
        "골드: 20G\n"
        "장착 장비: 무기: 초보자의 무기, 갑옷: 여행자 가죽옷\n"
        "인벤토리: 체력 포션 (소), 마력 회복의 반지\n"
        "사용가능한 마법 및 기술: 마력탄, 방패술\n"
        "아이템 구매, 골드 변동, 체력/마나 소모, 아이템 획득 시 정확히 반영해 주세요."
    )

    prompt = (
        f"[현재 캐릭터 상태 동기화 정보]\n{st.session_state.status_sync_text}\n\n"
        f"최근 대화 기록:\n"
        + json.dumps(st.session_state.history[-6:], ensure_ascii=False)
        + f"\n\n플레이어의 행동 또는 선택: {user_action}"
    )

    if ai_provider == "Google Gemini":
        try:
            client = genai.Client(api_key=api_key_input)
            response = client.models.generate_content(
                model=selected_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=SyncTextRPGResponse,
                    temperature=0.7,
                ),
            )
            return SyncTextRPGResponse.model_validate_json(response.text)
        except Exception as e:
            st.error(f"Gemini API 호출 오류: {e}")
            return None
    else:
        try:
            client = OpenAI(
                api_key=api_key_input,
                base_url="https://api.groq.com/openai/v1"
            )
            groq_system_instruction = system_instruction + "\n반드시 아래의 JSON 구조로만 응답하세요:\n{\n  \"narrative\": \"서사 내용...\",\n  \"status_sync_text\": \"상태 동기화 텍스트...\",\n  \"choices\": [\"선택지1\", \"선택지2\", \"선택지3\"]\n}"
            
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": groq_system_instruction},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            return SyncTextRPGResponse.model_validate_json(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Groq API 통신 에러 발생: {e}")
            return None


# 🎮 [메인 화면 로직]
if not api_key_input:
    st.warning(f"⚠️ 좌측 사이드바에 {ai_provider} API 키를 입력해 주세요.")
else:
    if not st.session_state.history:
        with st.spinner("모험의 세계를 여는 중..."):
            res = call_ai_sync_text(
                "모험가가 되기 위해 첫 발걸음을 내딛습니다. 오프닝을 시작해 주세요."
            )
            if res:
                st.session_state.status_sync_text = res.status_sync_text
                st.session_state.history.append({
                    "role": "assistant",
                    "narrative": res.narrative,
                    "choices": res.choices,
                })
                append_ai_log(res.narrative)
                save_game()
                st.rerun()

    else:
        # 본문 스토리 및 음성 버튼 출력
        for idx, h in enumerate(st.session_state.history):
            with st.chat_message(h["role"]):
                st.markdown(h.get("narrative", ""))
                
                if h["role"] == "assistant":
                    narrative_text = h.get("narrative", "")
                    safe_text = narrative_text.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
                    
                    html_code = f"""
                    <div style="margin-top: 5px; margin-bottom: 5px;">
                        <button onclick="window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance('{safe_text}'); u.lang='ko-KR'; window.speechSynthesis.speak(u);" 
                                style="background-color: #262730; color: white; border: 1px solid #4a4a4a; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-family: sans-serif; font-weight: bold;">
                            🔊 본문 음성으로 듣기
                        </button>
                    </div>
                    """
                    components.html(html_code, height=45)

        # 현재 턴 선택지 및 선택지별 음성 듣기 버튼 출력
        current_choices = []
        if st.session_state.history:
            last_h = st.session_state.history[-1]
            current_choices = last_h.get("choices", [])

        user_action = None
        if current_choices:
            st.markdown("##### 🎯 행동 선택")
            for idx, ch in enumerate(current_choices):
                col_btn, col_tts = st.columns([5, 1])
                with col_btn:
                    if st.button(
                        f"👉 {ch}",
                        key=f"ch_{len(st.session_state.history)}_{idx}",
                        use_container_width=True,
                    ):
                        user_action = ch
                with col_tts:
                    safe_ch = ch.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
                    ch_tts_html = f"""
                    <div style="margin-top: 2px;">
                        <button onclick="window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance('{safe_ch}'); u.lang='ko-KR'; window.speechSynthesis.speak(u);" 
                                style="background-color: #262730; color: white; border: 1px solid #4a4a4a; padding: 8px 10px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: bold; width: 100%;">
                            🔊 듣기
                        </button>
                    </div>
                    """
                    components.html(ch_tts_html, height=45)

        chat_input = st.chat_input("원하는 행동을 자유롭게 입력하세요...")
        final_input = user_action or chat_input

        if final_input:
            st.session_state.history.append(
                {"role": "user", "narrative": final_input}
            )
            with st.chat_message("user"):
                st.markdown(final_input)

            with st.spinner("게임 마스터가 처리 중..."):
                res = call_ai_sync_text(final_input)

                if res:
                    st.session_state.status_sync_text = res.status_sync_text

                    st.session_state.history.append({
                        "role": "assistant",
                        "narrative": res.narrative,
                        "choices": res.choices,
                    })

                    append_ai_log(res.narrative)

                    if len(st.session_state.history) > 30:
                        st.session_state.history = st.session_state.history[-30:]
                        
                    save_game()
                    st.rerun()
