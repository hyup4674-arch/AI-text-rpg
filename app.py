import json
import os
import re
import streamlit as st
from google import genai
from google.genai import types

# 🔑 [API 키 입력 설정]
DEFAULT_API_KEY = ""
SAVE_FILE = "rpg_save.json"

st.set_page_config(
    page_title="Gemini 텍스트 RPG 시뮬레이터", page_icon="⚔️", layout="wide"
)

# 🎨 [우측 상태창 상단 고정(Sticky) CSS 적용]
st.markdown(
    """
    <style>
    /* 메인 화면의 두 번째 열(우측 상태창)을 스크롤 시 상단에 고정 */
    [data-testid="column"]:nth-of-type(2) {
        position: sticky;
        top: 5rem;
        height: fit-content;
        z-index: 99;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚔️ 판타지 텍스트 RPG 게임 마스터 (우측 고정 상태 패널)")
st.markdown(
    "Google Gemini API와 Streamlit을 연동하여, 화면 우측에 캐릭터의 모든"
    " 스탯·장비·기술이 항상 고정 표시되는 텍스트 RPG 공간입니다."
)

# 📊 [캐릭터 종합 스탯 및 장비/기술 시스템 초기화]
if "stats" not in st.session_state:
  st.session_state.stats = {
      "hp": 100,
      "max_hp": 100,
      "mp": 50,
      "max_mp": 50,
      "gold": 50,
      "level": 1,
      "equipment": {"무기": "낡은 단검", "갑옷": "누더기 옷", "장신구": "없음"},
      "inventory": ["낡은 단검", "체력 포션 (소)"],
      "skills": ["기본 찌르기", "약한 응급 치료"],
  }

# 사이드바 설정 (API 키 입력 및 세이브/백업)
st.sidebar.header("⚙️ 게임 설정 및 백업")

api_key_input = st.sidebar.text_input(
    "Google Gemini API 키 입력",
    value=DEFAULT_API_KEY,
    type="password",
    help="Google AI Studio에서 발급받은 API 키를 입력하세요.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("💾 세이브 파일 관리")

if os.path.exists(SAVE_FILE):
  with open(SAVE_FILE, "r", encoding="utf-8") as f:
    save_data_str = f.read()
  st.sidebar.download_button(
      label="📥 내 세이브 파일 백업 (다운로드)",
      data=save_data_str,
      file_name="rpg_save.json",
      mime="application/json",
      help="게임을 마치기 전 이 버튼을 눌러 세이브 파일을 저장하세요!",
  )

uploaded_save = st.sidebar.file_uploader(
    "📂 백업한 세이브 파일 불러오기",
    type=["json"],
    help="이전에 백업해 둔 json 파일을 업로드하면 즉시 이어서 할 수 있습니다.",
)

if uploaded_save is not None:
  try:
    uploaded_bytes = uploaded_save.read()
    with open(SAVE_FILE, "wb") as f:
      f.write(uploaded_bytes)
    st.sidebar.success("✅ 세이브 파일을 성공적으로 불러왔습니다!")
    st.rerun()
  except Exception as e:
    st.sidebar.error(f"세이브 로드 실패: {e}")

if st.sidebar.button("🔄 새 게임 시작 (초기화)"):
  if os.path.exists(SAVE_FILE):
    os.remove(SAVE_FILE)
  for key in list(st.session_state.keys()):
    del st.session_state[key]
  st.rerun()

st.sidebar.markdown("---")

# 🖥️ [화면 레이아웃 분할: 왼쪽은 채팅 영역(2.5), 오른쪽은 상시 고정 상태 패널(1)]
chat_col, status_col = st.columns([2.5, 1], gap="medium")

# 우측 상태 패널 구성 (스크롤 시 고정됨)
with status_col:
  st.markdown("### 🛡️ 캐릭터 상태창")
  with st.container(border=True):
    stats = st.session_state.stats
    st.metric(
        label="❤️ 체력 (HP)", value=f"{stats['hp']} / {stats['max_hp']}"
    )
    st.metric(
        label="💙 마나 (MP)", value=f"{stats['mp']} / {stats['max_mp']}"
    )
    st.metric(label="💰 보유 골드", value=f"{stats['gold']} G")
    st.metric(label="⭐ 레벨", value=f"Lv. {stats['level']}")

    st.markdown("---")
    st.markdown("##### ⚔️ 장착 장비")
    for slot, item in stats["equipment"].items():
      st.write(f"- **{slot}**: {item}")

    st.markdown("---")
    st.markdown("##### 🎒 인벤토리")
    st.write(
        f"{', '.join(stats['inventory']) if stats['inventory'] else '없음'}"
    )

    st.markdown("---")
    st.markdown("##### ✨ 사용 가능 기술")
    st.write(f"{', '.join(stats['skills']) if stats['skills'] else '없음'}")

# 왼쪽 채팅 영역 구성
with chat_col:
  if not api_key_input:
    st.warning(
        "⚠️ 좌측 사이드바에 **Google Gemini API 키**를 입력해 주세요."
    )
  else:
    try:
      if (
          "client" not in st.session_state
          or "chat_session" not in st.session_state
      ):
        st.session_state.client = genai.Client(api_key=api_key_input)

        current_stats = st.session_state.stats
        system_instruction = (
            "당신은 몰입감 있는 정통 판타지 텍스트 RPG의 게임 마스터(GM)입니다. "
            "플레이어의 입력에 따라 흥미진진한 모험 상황을 묘사하세요.\n"
            "현재 플레이어의 상태 정보:\n"
            f"- HP: {current_stats['hp']}/{current_stats['max_hp']}\n"
            f"- MP: {current_stats['mp']}/{current_stats['max_mp']}\n"
            f"- 골드: {current_stats['gold']}, 레벨: {current_stats['level']}\n"
            f"- 장비: {json.dumps(current_stats['equipment'], ensure_ascii=False)}\n"
            f"- 인벤토리: {json.dumps(current_stats['inventory'], ensure_ascii=False)}\n"
            f"- 기술: {json.dumps(current_stats['skills'], ensure_ascii=False)}\n\n"
            "매 턴 답변의 마지막 줄에 [상태: 체력 XX/XX, 마나 XX/XX, 골드 XX, 장비: ..., 인벤토리: ..., 기술: ...]를 포함하고, "
            "스탯, 장비, 인벤토리, 기술 등의 변동이 발생할 경우 반드시 답변 맨 마지막 줄에 단독으로 "
            '[JSON_UPDATE: {"hp": 숫자, "max_hp": 숫자, "mp": 숫자, "max_mp": 숫자, "gold": 숫자, "level": 숫자, "equipment": {"무기": "...", "갑옷": "..."}, "inventory": ["..."], "skills": ["..."]}] '
            "형식의 JSON 데이터를 포함해 주세요. 변동이 없더라도 현재 상태의 전체 JSON을 반드시 포함해 주세요."
        )

        loaded_messages = []
        if os.path.exists(SAVE_FILE):
          try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
              loaded_messages = json.load(f)
          except Exception:
            loaded_messages = []

        st.session_state.messages = loaded_messages

        if not st.session_state.messages:
          st.session_state.chat_session = st.session_state.client.chats.create(
              model="gemini-3.6-flash",
              config=types.GenerateContentConfig(
                  system_instruction=system_instruction,
                  temperature=0.8,
              ),
          )
          with st.spinner("새로운 게임 세계를 생성하는 중입니다..."):
            initial_prompt = (
                "눈을 떠보니 음산한 기운이 감도는 고대 던전의 지하 감옥입니다."
                " 게임을 시작해 주세요."
            )
            response = st.session_state.chat_session.send_message(
                initial_prompt
            )
            bot_response = response.text
            st.session_state.messages = [{
                "role": "assistant",
                "content": f"🏰 **[모험이 시작되었습니다]**\n\n{bot_response}",
            }]

            with open(SAVE_FILE, "w", encoding="utf-8") as f:
              json.dump(st.session_state.messages, f, ensure_ascii=False)
        else:
          api_history = []
          for msg in st.session_state.messages:
            r = (
                "model"
                if msg["role"] == "assistant"
                else ("user" if msg["role"] == "user" else None)
            )
            if r:
              api_history.append(
                  types.Content(
                      role=r, parts=[types.Part.from_text(text=msg["content"])]
                  )
              )

          st.session_state.chat_session = st.session_state.client.chats.create(
              model="gemini-3.6-flash",
              history=api_history if api_history else None,
              config=types.GenerateContentConfig(
                  system_instruction=system_instruction,
                  temperature=0.8,
              ),
          )

      for message in st.session_state.messages:
        with st.chat_message(message["role"]):
          st.markdown(message["content"])

      if user_prompt := st.chat_input("어떤 행동을 하시겠습니까?"):
        st.session_state.messages.append(
            {"role": "user", "content": user_prompt}
        )
        with st.chat_message("user"):
          st.markdown(user_prompt)

        with st.chat_message("assistant"):
          with st.spinner("게임 마스터가 다음 상황을 계산 중입니다..."):
            response = st.session_state.chat_session.send_message(user_prompt)
            bot_response = response.text
            st.markdown(bot_response)

            match = re.search(
                r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]", bot_response, re.DOTALL
            )
            if match:
              try:
                updated_json_str = match.group(1)
                updated_data = json.loads(updated_json_str)
                for k, v in updated_data.items():
                  if k in st.session_state.stats:
                    st.session_state.stats[k] = v
                st.rerun()
              except Exception as e:
                pass

        st.session_state.messages.append(
            {"role": "assistant", "content": bot_response}
        )

        with open(SAVE_FILE, "w", encoding="utf-8") as f:
          json.dump(st.session_state.messages, f, ensure_ascii=False)

    except Exception as e:
      st.error(
          f"❌ 오류가 발생했습니다. API 키가 올바른지 확인해 주세요. (상세 에러:"
          f" {e})"
      )
