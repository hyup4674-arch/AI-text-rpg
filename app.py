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
    page_title="하드코어 텍스트 RPG", page_icon="⚔️", layout="wide"
)
st.title("⚔️ 하드코어 텍스트 RPG (자비 없는 생존)")
st.markdown(
    "선택에 따라 파멸과 죽음이 도사리는 하드코어 판타지 세계관입니다. 방심하면 영구 사망(Permadeath)합니다."
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
        description="상세하고 냉혹한 현장 묘사와 몰입감 있는 스토리 서사. 플레이어의 행동에 따른 잔인하거나 치명적인 결과를 숨기지 말고 묘사하세요. 사망 시 비참한 최후를 상세히 묘사하세요."
    )
    status_sync_text: str = Field(
        description=(
            "현재 캐릭터의 상태 텍스트 블록. 반드시 항목별로 줄바꿈 포함:\n"
            "상태: 생존 또는 사망(GAME OVER)\n"
            "종족: 인간\n"
            "직업: 전사\n"
            "레벨: 1 (경험치: 0/100)\n"
            "체력(HP): 100/100\n"
            "마나(MP): 20/20\n"
            "힘: 15\n"
            "체력스탯: 14\n"
            "지능: 8\n"
            "민첩: 10\n"
            "골드: 50G\n"
            "장착 장비: 무기: 낡은 단검, 갑옷: 누더기 옷\n"
            "인벤토리: 싸구려 체력 포션 (소)\n"
            "사용가능한 마법 및 기술: 베기, 도망치기\n"
        )
    )
    choices: list[str] = Field(
        description="플레이어가 다음에 선택할 수 있는 행동지침 3~4가지. 함정과 위험한 선택지를 반드시 포함하며, 레벨업 시 스탯(힘, 체력스탯, 지능, 민첩 중 1개)을 올리는 선택지를 포함해야 합니다."
    )


# 💾 [기본 데이터 및 세이브/로드 관리]
default_sync_text = (
    "상태: 생존\n"
    "종족: 인간\n"
    "직업: 미정\n"
    "레벨: 1 (경험치: 0/100)\n"
    "체력(HP): 100/100\n"
    "마나(MP): 20/20\n"
    "힘: 10\n"
    "체력스탯: 10\n"
    "지능: 10\n"
    "민첩: 10\n"
    "골드: 50G\n"
    "장착 장비: 무기: 낡은 단검, 갑옷: 누더기 옷\n"
    "인벤토리: 체력 포션 (소)\n"
    "사용가능한 마법 및 기술: 기본 공격, 도망치기\n"
)

def save_game():
    data = {
        "status_sync_text": st.session_state.get("status_sync_text", default_sync_text),
        "history": st.session_state.get("history", []),
        "game_concept": st.session_state.get("game_concept", ""),
        "is_game_over": st.session_state.get("is_game_over", False),
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
        saved_data.get("game_concept", "다크 판타지, 자비 없는 생존, 플레이어의 잘못된 선택은 부상, 자원 손실, 혹은 즉각적인 영구 사망(GAME OVER)을 초래함.")
        if saved_data
        else "다크 판타지, 자비 없는 생존, 플레이어의 잘못된 선택은 부상, 자원 손실, 혹은 즉각적인 영구 사망(GAME OVER)을 초래함."
    )

if "is_game_over" not in st.session_state:
    st.session_state.is_game_over = (
        saved_data.get("is_game_over", False) if saved_data else False
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
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
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

st.sidebar.markdown("---")
st.sidebar.subheader("🎭 세계관 설정")
game_concept_input = st.sidebar.text_area(
    "게임 배경 및 컨셉",
    value=st.session_state.game_concept,
    height=80,
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
st.sidebar.subheader("🛡️ 캐릭터 상태 동기화")

clean_status = (
    st.session_state.status_sync_text
    .replace('"', '')
    .replace('{', '')
    .replace('}', '')
    .replace('[', '')
    .replace(']', '')
)

keys_to_break = [
    "상태:", "종족:", "직업:", "레벨:", "체력(HP):", "마나(MP):", 
    "힘:", "체력스탯:", "지능:", "민첩:", "골드:", 
    "장착 장비:", "인벤토리:", "사용가능한 마법 및 기술:"
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
        label="📥 세이브 파일 저장",
        data=json_data_str,
        file_name="rpg_sync_text_save.json",
        mime="application/json",
        use_container_width=True,
    )

uploaded_file = st.sidebar.file_uploader(
    "📂 세이브 파일 불러오기", type=["json"]
)
if uploaded_file is not None:
    try:
        loaded_data = json.load(uploaded_file)
        if "status_sync_text" in loaded_data and "history" in loaded_data:
            st.session_state.status_sync_text = loaded_data["status_sync_text"]
            st.session_state.history = loaded_data["history"]
            st.session_state.game_concept = loaded_data.get("game_concept", st.session_state.game_concept)
            st.session_state.is_game_over = loaded_data.get("is_game_over", False)
            save_game()
            st.sidebar.success("🎉 불러오기 성공!")
            st.rerun()
        else:
            st.sidebar.error("❌ 올바르지 않은 세이브 형식입니다.")
    except Exception as e:
        st.sidebar.error(f"❌ 오류 발생: {e}")

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
    system_instruction = (
        "당신은 자비 없고 냉혹한 하드코어 판타지 TRPG 게임 마스터(GM)입니다.\n"
        f"[게임 컨셉]\n{concept_str}\n\n"
        "【절대 규칙】\n"
        "1. 플레이어의 선택이 무모하거나 잘못되면, 구제불능의 부상, 아이템 손실, 혹은 즉각적인 영구 사망(GAME OVER) 처리를 가감 없이 수행하세요. 절대로 억지 해피엔딩이나 우연한 행운으로 플레이어를 구해주지 마세요.\n"
        "2. 체력(HP)이 0이 되거나 치명적인 함정을 밟으면 '상태: 사망(GAME OVER)'으로 기록하고 모험을 종료시키세요.\n"
        "3. 레벨업 시 플레이어가 스탯(힘, 체력스탯, 지능, 민첩 중 1개)을 선택하여 올릴 수 있도록 선택지에 반영하세요.\n"
        "4. 캐릭터 상태 동기화 텍스트(status_sync_text)의 모든 항목(상태, 종족, 직업, 레벨, HP, MP, 힘, 체력스탯, 지능, 민첩, 골드 등)을 갱신하세요."
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
                    temperature=0.8,
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
            groq_system_instruction = system_instruction + "\n반드시 아래 JSON 구조로만 응답하세요:\n{\n  \"narrative\": \"서사 내용...\",\n  \"status_sync_text\": \"상태 텍스트...\",\n  \"choices\": [\"선택지1\", \"선택지2\", \"선택지3\"]\n}"
            
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": groq_system_instruction},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8,
            )
            return SyncTextRPGResponse.model_validate_json(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Groq API 통신 에러: {e}")
            return None


# 🎮 [메인 화면 로직]
if not api_key_input:
    st.warning(f"⚠️ 좌측 사이드바에 {ai_provider} API 키를 입력해 주세요.")
else:
    # 1. 게임 오버 처리
    if st.session_state.is_game_over:
        st.error("💀 당신은 사망했습니다. 영구 사망(Permadeath) 규칙에 따라 이 모험은 실패로 끝났습니다.")
        if st.button("🔥 완전히 새로운 스토리와 모험으로 다시 시작하기", use_container_width=True):
            if os.path.exists(SAVE_FILE):
                os.remove(SAVE_FILE)
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # 2. 직업 선택 화면 (처음 시작할 때)
    elif not st.session_state.history:
        st.subheader("🛡️ 캐릭터 직업 선택")
        selected_job = st.selectbox("원하는 직업을 선택하세요", ["전사", "마법사", "도적", "성기사", "사냥꾼"])
        
        if st.button("⚔️ 이 직업으로 하드코어 모험 시작하기", use_container_width=True):
            initial_action = f"인간 종족의 '{selected_job}' 직업으로 새롭고 위험 가득한 하드코어 모험을 시작합니다. 첫 번째 오프닝 상황을 묘사하고 위험한 선택지들을 제시해 주세요."
            
            # 직업별 초기 스탯 설정 반영
            job_stats = {
                "전사": "상태: 생존\n종족: 인간\n직업: 전사\n레벨: 1 (경험치: 0/100)\n체력(HP): 120/120\n마나(MP): 10/10\n힘: 16\n체력스탯: 14\n지능: 8\n민첩: 10\n골드: 30G\n장착 장비: 무기: 녹슨 검, 갑옷: 낡은 가죽 갑옷\n인벤토리: 체력 포션 (소)\n사용가능한 마법 및 기술: 강한 베기, 방어태세",
                "마법사": "상태: 생존\n종족: 인간\n직업: 마법사\n레벨: 1 (경험치: 0/100)\n체력(HP): 70/70\n마나(MP): 50/50\n힘: 8\n체력스탯: 8\n지능: 16\n민첩: 10\n골드: 40G\n장착 장비: 무기: 마력의 나무 지팡이, 갑옷: 천 로브\n인벤토리: 마나 포션 (소)\n사용가능한 마법 및 기술: 마력탄, 마나 보호막",
                "도적": "상태: 생존\n종족: 인간\n직업: 도적\n레벨: 1 (경험치: 0/100)\n체력(HP): 80/80\n마나(MP): 20/20\n힘: 10\n체력스탯: 9\n지능: 11\n민첩: 16\n골드: 50G\n장착 장비: 무기: 단검 쌍수, 갑옷: 가죽 조끼\n인벤토리: 해독제, 연막탄\n사용가능한 마법 및 기술: 급습, 잠금 해제",
                "성기사": "상태: 생존\n종족: 인간\n직업: 성기사\n레벨: 1 (경험치: 0/100)\n체력(HP): 110/110\n마나(MP): 30/30\n힘: 14\n체력스탯: 14\n지능: 12\n민첩: 8\n골드: 20G\n장착 장비: 무기: 축복받은 메이스, 갑옷: 철제 흉갑\n인벤토리: 성수\n사용가능한 마법 및 기술: 징벌, 치유 기원",
                "사냥꾼": "상태: 생존\n종족: 인간\n직업: 사냥꾼\n레벨: 1 (경험치: 0/100)\n체력(HP): 90/90\n마나(MP): 20/20\n힘: 11\n체력스탯: 10\n지능: 10\n민첩: 15\n골드: 35G\n장착 장비: 무기: 숏보우, 갑옷: 사냥꾼 가죽옷\n인벤토리: 화살 30발\n사용가능한 마법 및 기술: 정밀 사격, 덫 설치"
            }
            st.session_state.status_sync_text = job_stats.get(selected_job, default_sync_text)

            with st.spinner("잔혹한 판타지 세계를 생성하는 중..."):
                res = call_ai_sync_text(initial_action)
                if res:
                    st.session_state.status_sync_text = res.status_sync_text
                    if "사망" in res.status_sync_text or "GAME OVER" in res.status_sync_text:
                        st.session_state.is_game_over = True
                    st.session_state.history.append({
                        "role": "assistant",
                        "narrative": res.narrative,
                        "choices": res.choices,
                    })
                    append_ai_log(res.narrative)
                    save_game()
                    st.rerun()

    # 3. 정상 플레이 진행
    else:
        for h in st.session_state.history:
            with st.chat_message(h["role"]):
                st.markdown(h.get("narrative", ""))
                
                if h["role"] == "assistant":
                    narrative_text = h.get("narrative", "")
                    safe_text = narrative_text.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
                    
                    html_code = f"""
                    <div style="margin-top: 5px; margin-bottom: 5px;">
                        <button onclick="window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance('{safe_text}'); u.lang='ko-KR'; window.speechSynthesis.speak(u);" 
                                style="background-color: #262730; color: white; border: 1px solid #4a4a4a; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-family: sans-serif; font-weight: bold;">
                            🔊 음성으로 듣기
                        </button>
                    </div>
                    """
                    components.html(html_code, height=45)

        current_choices = []
        if st.session_state.history:
            last_h = st.session_state.history[-1]
            current_choices = last_h.get("choices", [])

        user_action = None
        if current_choices and not st.session_state.is_game_over:
            st.markdown("##### 🎯 행동 선택 (신중하게 고르세요)")
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

        chat_input = st.chat_input("원하는 행동을 직접 입력하세요...", disabled=st.session_state.is_game_over)
        final_input = user_action or chat_input

        if final_input and not st.session_state.is_game_over:
            st.session_state.history.append(
                {"role": "user", "narrative": final_input}
            )
            with st.chat_message("user"):
                st.markdown(final_input)

            with st.spinner("게임 마스터가 냉혹한 판정을 내리는 중..."):
                res = call_ai_sync_text(final_input)

                if res:
                    st.session_state.status_sync_text = res.status_sync_text
                    
                    if "사망" in res.status_sync_text or "GAME OVER" in res.status_sync_text or "체력(HP): 0" in res.status_sync_text:
                        st.session_state.is_game_over = True

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
