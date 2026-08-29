import json
import os
import random
import streamlit as st
import streamlit.components.v1 as components

from google import genai
from google.genai import types

from openai import OpenAI
from pydantic import BaseModel, Field


# =========================================================
# 🔑 API 키 및 파일 설정
# =========================================================

SAVE_FILE = "rpg_sync_text_save.json"
LOG_FILE = "rpg_story_log.txt"


# =========================================================
# 🌐 Streamlit 기본 설정
# =========================================================

st.set_page_config(
    page_title="추리 퀘스트 주사위 판정 텍스트 RPG",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 판타지 추리 & 주사위 모험 RPG")

st.markdown(
    "상점에서는 오직 초보용 기초 장비와 포션만 구매할 수 있습니다. "
    "진정한 고급 장비, 마법, 스탯 상승은 마을 주민들과의 심도 있는 "
    "**대화와 복잡한 추리 퀘스트**를 통해서만 획득할 수 있습니다!"
)


# =========================================================
# 🎨 스크롤 위치 복원 JS
# =========================================================

st.markdown(
    """
    <script>
        (function() {
            const pWin = window.parent || window;
            const pDoc = pWin.document;
            const SCROLL_KEY = 'rpg_sync_text_scroll';

            function getScrollContainer() {
                return (
                    pDoc.querySelector('[data-testid="stAppViewContainer"]')
                    || pDoc.querySelector('.main')
                    || pWin
                );
            }

            const container = getScrollContainer();

            const savePos = function() {
                const pos = (container !== pWin)
                    ? container.scrollTop
                    : (pWin.pageYOffset || pDoc.documentElement.scrollTop);

                pWin.sessionStorage.setItem(SCROLL_KEY, pos);
            };

            if (container !== pWin) {
                container.addEventListener('scroll', savePos, { passive: true });
            } else {
                pWin.addEventListener('scroll', savePos, { passive: true });
            }

            function restoreScroll() {
                const saved = pWin.sessionStorage.getItem(SCROLL_KEY);

                if (saved !== null) {
                    const targetPos = parseInt(saved, 10);
                    const cont = getScrollContainer();

                    if (cont !== pWin) {
                        cont.scrollTop = targetPos;
                    } else {
                        pWin.scrollTo(0, targetPos);
                    }
                }
            }

            setTimeout(restoreScroll, 50);
            setTimeout(restoreScroll, 200);
        })();
    </script>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 📋 AI 응답 스키마
# =========================================================

class SyncTextRPGResponse(BaseModel):

    narrative: str = Field(
        description=(
            "주사위 눈의 결과와 플레이어의 선택을 반영한 서사. "
            "전투 발생 시 적의 HP가 0이 될 때까지의 라운드별 계산 과정을 "
            "압축하여 보여주세요. "
            "마을 방문이나 주민 대화 시에는 추리 단서와 심리적 요소를 "
            "상세히 묘사하세요."
        )
    )

    status_sync_text: str = Field(
        description=(
            "현재 캐릭터의 상태 텍스트 블록. 반드시 항목별로 줄바꿈 포함:\n"
            "종족: 인간\n"
            "직업: 전사\n"
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
    )

    choices: list[str] = Field(
        description=(
            "플레이어가 다음에 선택할 수 있는 행동지침 3~4가지. "
            "예: 상점 가기, 특정 주민과 대화하기, 추리 결판 내기, "
            "사냥터 가기 등"
        )
    )

    quest_update: str = Field(
        description=(
            "현재 진행 중인 추리 퀘스트의 핵심 요약, 수집된 단서, "
            "의심되는 인물 및 다음 수사 방향을 정리한 텍스트. "
            "우측 사이드바에 고정 노출됩니다."
        )
    )


# =========================================================
# 💾 기본 데이터
# =========================================================

default_sync_text = (
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


default_quest_text = (
    "📌 [현재 추리 퀘스트]\n"
    "- 상태: 퀘스트 미수주\n"
    "- 목표: 마을 광장을 방문하여 주민들과 대화하고 미스터리 사건을 파악하세요.\n"
    "- 수집된 단서: 없음\n"
)


# =========================================================
# 💾 저장
# =========================================================

def save_game():

    data = {
        "status_sync_text": st.session_state.get(
            "status_sync_text",
            default_sync_text
        ),

        "history": st.session_state.get(
            "history",
            []
        ),

        "game_concept": st.session_state.get(
            "game_concept",
            ""
        ),

        "active_quest_info": st.session_state.get(
            "active_quest_info",
            default_quest_text
        ),
    }

    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# 📜 AI 로그
# =========================================================

def append_ai_log(narrative):

    with open(LOG_FILE, "a", encoding="utf-8") as f:

        f.write(
            f"{narrative}\n\n"
            + "-" * 50
            + "\n\n"
        )


# =========================================================
# 📊 세션 초기화
# =========================================================

saved_data = None

if os.path.exists(SAVE_FILE):

    try:

        with open(
            SAVE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            saved_data = json.load(f)

    except Exception:

        saved_data = None


if "status_sync_text" not in st.session_state:

    st.session_state.status_sync_text = (
        saved_data.get(
            "status_sync_text",
            default_sync_text
        )
        if saved_data
        else default_sync_text
    )


if "active_quest_info" not in st.session_state:

    st.session_state.active_quest_info = (
        saved_data.get(
            "active_quest_info",
            default_quest_text
        )
        if saved_data
        else default_quest_text
    )


if "history" not in st.session_state:

    st.session_state.history = (
        saved_data.get(
            "history",
            []
        )
        if saved_data
        else []
    )


if "game_concept" not in st.session_state:

    st.session_state.game_concept = (
        saved_data.get(
            "game_concept",
            "판타지 모험. "
            "상점에서는 초보용 장비/포션만 판매. "
            "강력한 장비와 마법, 스탯 상승은 "
            "마을 주민들과의 깊이 있는 대화와 "
            "복잡한 두뇌 추리 퀘스트를 해결해야만 획득 가능함."
        )
        if saved_data
        else
        "판타지 모험. "
        "상점에서는 초보용 장비/포션만 판매. "
        "강력한 장비와 마법, 스탯 상승은 "
        "마을 주민들과의 깊이 있는 대화와 "
        "복잡한 두뇌 추리 퀘스트를 해결해야만 획득 가능함."
    )


# =========================================================
# ⚙️ 사이드바
# =========================================================

st.sidebar.header("⚙️ 게임 설정 및 AI 선택")


ai_provider = st.sidebar.selectbox(
    "🤖 AI 제공자 선택",
    [
        "Google Gemini",
        "Groq"
    ]
)


api_key_input = ""
selected_model = ""


# =========================================================
# 🟦 GOOGLE GEMINI
# =========================================================

if ai_provider == "Google Gemini":

    api_key_input = st.sidebar.text_input(
        "Google Gemini API 키 입력",
        type="password"
    )

    st.sidebar.markdown("### 🧠 Gemini 모델")

    selected_model = st.sidebar.selectbox(
        "Gemini 모델 선택",
        options=[
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
        ],
        index=0
    )

    st.sidebar.caption(
        "Gemini 3.7 Flash → 가장 강력\n"
        "Gemini 3.6 Flash → 균형형\n"
        "Gemini 3.5 Flash → 안정적인 범용형\n"
        "Gemini 3.5 Flash-Lite → 빠르고 가벼움\n"
        "Gemini 3.1 Flash-Lite → 초경량/고처리량"
    )


# =========================================================
# 🟩 GROQ
# =========================================================

else:

    api_key_input = st.sidebar.text_input(
        "Groq API 키 입력",
        type="password"
    )

    groq_model_option = st.sidebar.selectbox(
        "Groq 모델 선택",
        options=[
            "openai/gpt-oss-20b",
            "직접 입력",
        ],
        index=0
    )

    if groq_model_option == "직접 입력":

        selected_model = st.sidebar.text_input(
            "사용할 Groq 모델명 입력",
            value="llama-3.1-8b-instant"
        )

    else:

        selected_model = groq_model_option


# =========================================================
# 🔤 글자 크기
# =========================================================

font_size = st.sidebar.slider(
    "🔤 글자 크기",
    12,
    26,
    16,
    1
)


# =========================================================
# 📜 퀘스트 노트
# =========================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "📜 퀘스트 및 추리 수사 노트"
)


clean_quest_info = (
    st.session_state.active_quest_info
    .replace('"', '')
    .replace('{', '')
    .replace('}', '')
)


st.sidebar.markdown(
    f"""
    <div style="
        background-color: #1e1e1e;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #444;
        font-size: 14px;
        line-height: 1.5;
    ">
    {clean_quest_info.replace(chr(10), '<br>')}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 🛡️ 캐릭터 상태
# =========================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "🛡️ 캐릭터 상태 동기화"
)


clean_status = (
    st.session_state.status_sync_text
    .replace('"', '')
    .replace('{', '')
    .replace('}', '')
    .replace('[', '')
    .replace(']', '')
)


keys_to_break = [
    "종족:",
    "직업:",
    "레벨:",
    "체력(HP):",
    "마나(MP):",
    "힘:",
    "체력스탯:",
    "지능:",
    "민첩:",
    "골드:",
    "장착 장비:",
    "인벤토리:",
    "사용가능한 마법 및 기술:"
]


for key in keys_to_break:

    clean_status = clean_status.replace(
        key,
        f"\n{key}"
    )


st.sidebar.text(clean_status)


# =========================================================
# 💾 세이브 / 로드
# =========================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "💾 세이브 & 로드 관리"
)


if os.path.exists(SAVE_FILE):

    with open(
        SAVE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        json_data_str = f.read()


    st.sidebar.download_button(
        label="📥 세이브 파일 저장",
        data=json_data_str,
        file_name="rpg_sync_text_save.json",
        mime="application/json",
        use_container_width=True,
    )


uploaded_file = st.sidebar.file_uploader(
    "📂 세이브 파일 불러오기",
    type=["json"]
)


if uploaded_file is not None:

    try:

        loaded_data = json.load(uploaded_file)

        if (
            "status_sync_text" in loaded_data
            and "history" in loaded_data
        ):

            st.session_state.status_sync_text = (
                loaded_data["status_sync_text"]
            )

            st.session_state.history = (
                loaded_data["history"]
            )

            st.session_state.game_concept = (
                loaded_data.get(
                    "game_concept",
                    st.session_state.game_concept
                )
            )

            st.session_state.active_quest_info = (
                loaded_data.get(
                    "active_quest_info",
                    default_quest_text
                )
            )

            save_game()

            st.sidebar.success(
                "🎉 불러오기 성공!"
            )

            st.rerun()

        else:

            st.sidebar.error(
                "❌ 올바르지 않은 세이브 형식입니다."
            )

    except Exception as e:

        st.sidebar.error(
            f"❌ 오류 발생: {e}"
        )


# =========================================================
# 🔄 새 게임
# =========================================================

st.sidebar.markdown("---")


if st.sidebar.button(
    "🔄 전체 초기화 및 새 게임",
    use_container_width=True
):

    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)

    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()


# =========================================================
# 🎨 CSS
# =========================================================

st.markdown(
    f"""
    <style>

        .stChatMessage p,
        .stChatMessage div {{
            font-size: {font_size}px !important;
            line-height: 1.6 !important;
        }}

        div.stButton > button,
        div.stButton > button p {{
            font-size: {font_size + 4}px !important;
            font-weight: bold !important;
        }}

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 🤖 AI 호출 함수
# =========================================================

def call_ai_sync_text(
    user_action,
    dice_val
):

    concept_str = (
        st.session_state.game_concept.strip()
    )


    # =====================================================
    # 시스템 프롬프트
    # =====================================================

    system_instruction = (

        "당신은 판타지 추리 RPG의 게임 마스터(GM)입니다.\n"

        f"[게임 컨셉]\n"
        f"{concept_str}\n\n"

        "【규칙】\n"

        "1. 사망이나 영구적 파멸은 절대 없습니다. "
        "어떤 선택을 하거나 실패하더라도 게임이 끝나지 않으며, "
        "피해를 입어도 체력이 최소 1 이상 남거나 회복 수단이 제공됩니다.\n"

        "2. 상점 이용 규칙 (매우 중요): "
        "마을 상점에서는 오직 초보용 장비와 포션만 판매합니다. "
        "전설적인 무기나 고위 마법을 상점에서 판매하지 마세요.\n"

        "3. 추리 퀘스트 규칙 (매우 중요): "
        "강력한 장비, 희귀 마법, 대폭의 스탯 상승은 반드시 "
        "마을 주민들과 대화하고 모순점을 찾아내는 "
        "복잡한 두뇌 추리 퀘스트를 해결해야만 얻을 수 있습니다.\n"

        "4. 여러 NPC가 서로 다른 거짓말, 알리바이, "
        "숨겨진 목적을 가지고 있어야 합니다. "
        "플레이어가 실제로 단서를 비교하고 추론해야 합니다.\n"

        "5. quest_update에는 현재 추리 퀘스트의 진행 상황, "
        "수집된 결정적 단서, 의심되는 인물 및 다음 수사 방향을 "
        "상세히 기록하세요.\n"

        "6. 전투가 발생하면 한 번의 응답 안에서 "
        "적 HP가 0이 될 때까지 전투를 끝내세요. "
        "각 라운드의 핵심 피해 계산은 간결하게 표시하세요.\n"

        "7. 주사위 1~6의 결과를 반드시 실제 판정에 반영하세요.\n"

        "8. 캐릭터 상태(status_sync_text)는 매 턴 최신 상태로 갱신하세요.\n"

        "9. 레벨업, 경험치, 골드, HP, MP, 장비, 아이템을 "
        "절대로 임의로 되돌리지 마세요.\n"

        "10. 이전 상태와 현재 상태 사이에 모순이 생기지 않도록 하세요.\n"

        "11. choices에는 플레이어가 실제로 선택할 수 있는 "
        "구체적인 행동 3~4개를 제공하세요.\n"

        "12. 추리 실패 시에도 새로운 단서나 다른 수사 방향이 "
        "생기도록 하여 게임 진행이 막히지 않게 하세요.\n"
    )


    # =====================================================
    # 최근 기록
    # =====================================================

    recent_history = json.dumps(
        st.session_state.history[-6:],
        ensure_ascii=False
    )


    prompt = (

        "[현재 캐릭터 상태 동기화 정보]\n"
        f"{st.session_state.status_sync_text}\n\n"

        "[현재 퀘스트 수사 노트]\n"
        f"{st.session_state.active_quest_info}\n\n"

        "[최근 대화 기록]\n"
        f"{recent_history}\n\n"

        f"[플레이어의 행동 또는 선택]\n"
        f"{user_action}\n\n"

        f"🎲 [이번 턴 주사위 결과]\n"
        f"{dice_val} (1~6)"
    )


    # =====================================================
    # 🟦 Gemini
    # =====================================================

    if ai_provider == "Google Gemini":

        try:

            client = genai.Client(
                api_key=api_key_input
            )


            # -------------------------------------------------
            # Gemini 3.x
            #
            # temperature를 사용하지 않습니다.
            # Google의 Gemini 3.x 최신 권장 방식입니다.
            # -------------------------------------------------

            response = client.models.generate_content(

                model=selected_model,

                contents=prompt,

                config=types.GenerateContentConfig(

                    system_instruction=system_instruction,

                    response_mime_type="application/json",

                    response_schema=SyncTextRPGResponse,

                ),
            )


            return SyncTextRPGResponse.model_validate_json(
                response.text
            )


        except Exception as e:

            st.error(
                f"Gemini API 호출 오류 "
                f"[{selected_model}]: {e}"
            )

            return None


    # =====================================================
    # 🟩 Groq
    # =====================================================

    else:

        try:

            client = OpenAI(

                api_key=api_key_input,

                base_url="https://api.groq.com/openai/v1"
            )


            groq_system_instruction = (

                system_instruction

                +

                "\n반드시 아래 JSON 구조로만 응답하세요:\n"

                "{\n"

                '  "narrative": "서사 내용...",\n'

                '  "status_sync_text": "상태 텍스트...",\n'

                '  "choices": ["선택지1", "선택지2", "선택지3"],\n'

                '  "quest_update": "퀘스트 및 단서 요약..."\n'

                "}"
            )


            response = client.chat.completions.create(

                model=selected_model,

                messages=[

                    {
                        "role": "system",
                        "content": groq_system_instruction
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }

                ],

                response_format={
                    "type": "json_object"
                },

                max_tokens=8192,

                temperature=0.7,
            )


            return SyncTextRPGResponse.model_validate_json(
                response.choices[0].message.content
            )


        except Exception as e:

            st.error(
                f"Groq API 통신 에러: {e}"
            )

            return None


# =========================================================
# 🎮 메인 화면
# =========================================================

if not api_key_input:

    st.warning(
        f"⚠️ 좌측 사이드바에 "
        f"{ai_provider} API 키를 입력해 주세요."
    )


else:

    # =====================================================
    # 1. 처음 시작
    # =====================================================

    if not st.session_state.history:

        st.subheader(
            "🛡️ 캐릭터 직업 선택"
        )


        selected_job = st.selectbox(
            "원하는 직업을 선택하세요",
            [
                "전사",
                "마법사",
                "도적",
                "성기사",
                "사냥꾼"
            ]
        )


        if st.button(
            "⚔️ 이 직업으로 모험 시작하기",
            use_container_width=True
        ):

            initial_action = (

                f"인간 종족의 '{selected_job}' "
                "직업으로 모험을 시작합니다. "

                "고아원을 떠나 판타지 마을에 도착해 "
                "상점과 마을 광장의 주민들을 만나 "
                "미스터리 추리 퀘스트를 시작하는 "
                "오프닝 상황을 제시해 주세요."
            )


            initial_dice = random.randint(
                1,
                6
            )


            # -------------------------------------------------
            # 직업별 초기 스탯
            # -------------------------------------------------

            job_stats = {

                "전사":
                "종족: 인간\n"
                "직업: 전사\n"
                "레벨: 1 (경험치: 0/100)\n"
                "체력(HP): 120/120\n"
                "마나(MP): 10/10\n"
                "힘: 16\n"
                "체력스탯: 14\n"
                "지능: 8\n"
                "민첩: 10\n"
                "골드: 30G\n"
                "장착 장비: 무기: 녹슨 검, 갑옷: 낡은 가죽 갑옷\n"
                "인벤토리: 체력 포션 (소)\n"
                "사용가능한 마법 및 기술: 강한 베기, 방어태세",


                "마법사":
                "종족: 인간\n"
                "직업: 마법사\n"
                "레벨: 1 (경험치: 0/100)\n"
                "체력(HP): 70/70\n"
                "마나(MP): 50/50\n"
                "힘: 8\n"
                "체력스탯: 8\n"
                "지능: 16\n"
                "민첩: 10\n"
                "골드: 40G\n"
                "장착 장비: 무기: 마력의 나무 지팡이, 갑옷: 천 로브\n"
                "인벤토리: 마나 포션 (소)\n"
                "사용가능한 마법 및 기술: 마력탄, 마나 보호막",


                "도적":
                "종족: 인간\n"
                "직업: 도적\n"
                "레벨: 1 (경험치: 0/100)\n"
                "체력(HP): 80/80\n"
                "마나(MP): 20/20\n"
                "힘: 10\n"
                "체력스탯: 9\n"
                "지능: 11\n"
                "민첩: 16\n"
                "골드: 50G\n"
                "장착 장비: 무기: 단검 쌍수, 갑옷: 가죽 조끼\n"
                "인벤토리: 해독제, 연막탄\n"
                "사용가능한 마법 및 기술: 급습, 잠금 해제",


                "성기사":
                "종족: 인간\n"
                "직업: 성기사\n"
                "레벨: 1 (경험치: 0/100)\n"
                "체력(HP): 110/110\n"
                "마나(MP): 30/30\n"
                "힘: 14\n"
                "체력스탯: 14\n"
                "지능: 12\n"
                "민첩: 8\n"
                "골드: 20G\n"
                "장착 장비: 무기: 축복받은 메이스, 갑옷: 철제 흉갑\n"
                "인벤토리: 성수\n"
                "사용가능한 마법 및 기술: 징벌, 치유 기원",


                "사냥꾼":
                "종족: 인간\n"
                "직업: 사냥꾼\n"
                "레벨: 1 (경험치: 0/100)\n"
                "체력(HP): 90/90\n"
                "마나(MP): 20/20\n"
                "힘: 11\n"
                "체력스탯: 10\n"
                "지능: 10\n"
                "민첩: 15\n"
                "골드: 35G\n"
                "장착 장비: 무기: 숏보우, 갑옷: 사냥꾼 가죽옷\n"
                "인벤토리: 화살 30발\n"
                "사용가능한 마법 및 기술: 정밀 사격, 덫 설치"
            }


            st.session_state.status_sync_text = (
                job_stats.get(
                    selected_job,
                    default_sync_text
                )
            )


            with st.spinner(
                "모험의 세계를 생성하는 중..."
            ):

                res = call_ai_sync_text(
                    initial_action,
                    initial_dice
                )


                if res:

                    st.session_state.status_sync_text = (
                        res.status_sync_text
                    )

                    st.session_state.active_quest_info = (
                        res.quest_update
                    )


                    st.session_state.history.append({

                        "role": "assistant",

                        "narrative":
                            f"🎲 [주사위 결과: {initial_dice}]\n\n"
                            + res.narrative,

                        "choices":
                            res.choices,
                    })


                    append_ai_log(
                        res.narrative
                    )


                    save_game()

                    st.rerun()


    # =====================================================
    # 2. 정상 플레이
    # =====================================================

    else:

        for h in st.session_state.history:

            with st.chat_message(
                h["role"]
            ):

                st.markdown(
                    h.get(
                        "narrative",
                        ""
                    )
                )


                # -------------------------------------------------
                # TTS
                # -------------------------------------------------

                if h["role"] == "assistant":

                    narrative_text = (
                        h.get(
                            "narrative",
                            ""
                        )
                    )


                    safe_text = (
                        narrative_text
                        .replace(
                            '"',
                            '\\"'
                        )
                        .replace(
                            "'",
                            "\\'"
                        )
                        .replace(
                            "\n",
                            " "
                        )
                    )


                    html_code = f"""

                    <div style="
                        margin-top: 5px;
                        margin-bottom: 5px;
                    ">

                        <button
                            onclick="
                                window.speechSynthesis.cancel();

                                const u =
                                    new SpeechSynthesisUtterance(
                                        '{safe_text}'
                                    );

                                u.lang='ko-KR';

                                window.speechSynthesis.speak(u);
                            "

                            style="
                                background-color: #262730;
                                color: white;
                                border: 1px solid #4a4a4a;
                                padding: 6px 14px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-size: 13px;
                                font-family: sans-serif;
                                font-weight: bold;
                            "
                        >

                            🔊 음성으로 듣기

                        </button>

                    </div>

                    """


                    components.html(
                        html_code,
                        height=45
                    )


        # =================================================
        # 현재 선택지
        # =================================================

        current_choices = []


        if st.session_state.history:

            last_h = (
                st.session_state.history[-1]
            )

            current_choices = (
                last_h.get(
                    "choices",
                    []
                )
            )


        user_action = None


        if current_choices:

            st.markdown(
                "##### 🎯 행동 선택 (선택 시 주사위가 굴러갑니다)"
            )


            for idx, ch in enumerate(
                current_choices
            ):

                col_btn, col_tts = st.columns(
                    [5, 1]
                )


                with col_btn:

                    if st.button(

                        f"👉 {ch}",

                        key=f"ch_"
                             f"{len(st.session_state.history)}_"
                             f"{idx}",

                        use_container_width=True
                    ):

                        user_action = ch


                with col_tts:

                    safe_ch = (
                        ch
                        .replace(
                            '"',
                            '\\"'
                        )
                        .replace(
                            "'",
                            "\\'"
                        )
                        .replace(
                            "\n",
                            " "
                        )
                    )


                    ch_tts_html = f"""

                    <div style="
                        margin-top: 2px;
                    ">

                        <button

                            onclick="
                                window.speechSynthesis.cancel();

                                const u =
                                    new SpeechSynthesisUtterance(
                                        '{safe_ch}'
                                    );

                                u.lang='ko-KR';

                                window.speechSynthesis.speak(u);
                            "

                            style="
                                background-color: #262730;
                                color: white;
                                border: 1px solid #4a4a4a;
                                padding: 8px 10px;
                                border-radius: 6px;
                                cursor: pointer;
                                font-size: 13px;
                                font-weight: bold;
                                width: 100%;
                            "
                        >

                            🔊 듣기

                        </button>

                    </div>

                    """


                    components.html(
                        ch_tts_html,
                        height=45
                    )


        # =================================================
        # 직접 입력
        # =================================================

        chat_input = st.chat_input(
            "원하는 행동을 직접 입력하세요 "
            "(예: 상점 주인에게 초보용 포션 구매, "
            "촌장과 대화하기 등)..."
        )


        final_input = (
            user_action
            or chat_input
        )


        # =================================================
        # 플레이어 행동 처리
        # =================================================

        if final_input:

            dice_val = random.randint(
                1,
                6
            )


            display_user_input = (
                f"{final_input} "
                f"(🎲 주사위 굴림: {dice_val})"
            )


            st.session_state.history.append({

                "role": "user",

                "narrative":
                    display_user_input
            })


            with st.chat_message(
                "user"
            ):

                st.markdown(
                    display_user_input
                )


            with st.spinner(
                f"🎲 주사위가 굴러갑니다... "
                f"[눈금: {dice_val}] "
                f"판정 및 추리/전투 처리 중..."
            ):

                res = call_ai_sync_text(
                    final_input,
                    dice_val
                )


                if res:

                    st.session_state.status_sync_text = (
                        res.status_sync_text
                    )

                    st.session_state.active_quest_info = (
                        res.quest_update
                    )


                    st.session_state.history.append({

                        "role": "assistant",

                        "narrative":
                            f"🎲 **[주사위 결과: {dice_val}]**\n\n"
                            + res.narrative,

                        "choices":
                            res.choices,
                    })


                    append_ai_log(
                        f"[주사위: {dice_val}] "
                        f"{res.narrative}"
                    )


                    # -------------------------------------------------
                    # 대화 기록 최대 30개
                    # -------------------------------------------------

                    if len(
                        st.session_state.history
                    ) > 30:

                        st.session_state.history = (
                            st.session_state.history[-30:]
                        )


                    save_game()

                    st.rerun()
