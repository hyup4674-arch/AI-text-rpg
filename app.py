from google import genai
from google.genai import types
import json
import os
import streamlit as st

# =====================================================================
# 🔑 [API 키 미리 입력 설정]
# 아래 따옴표 안에 본인의 Gemini API 키를 미리 입력해 두시면
# 앞으로 웹사이트에 접속할 때 키를 따로 입력하지 않아도 바로 게임이 시작됩니다!
# 예시: DEFAULT_API_KEY = "AQ.Ab8RN6J9q7GD1tjW3pLYNgr..."
# =====================================================================
DEFAULT_API_KEY = ""

# 세이브 파일 이름 정의
SAVE_FILE = "rpg_save.json"

# 1. 웹 페이지 레이아웃 및 설정
st.set_page_config(
    page_title="Gemini 텍스트 RPG 시뮬레이터", page_icon="⚔️", layout="centered"
)
st.title("⚔️ 판타지 텍스트 RPG 게임 마스터")
st.markdown(
    "Google Gemini API와 Streamlit을 연동하여 웹 브라우저에서 즐기는 무제한 텍스트"
    " RPG 공간입니다."
)

# 2. 사이드바 - 설정 및 세이브 관리
st.sidebar.header("⚙️ 게임 설정 및 관리")

# 코드 상단에 키가 있으면 기본값으로 자동 채워짐
api_key_input = st.sidebar.text_input(
    "Google Gemini API 키 입력",
    value=DEFAULT_API_KEY,
    type="password",
    help="상단 코드에 미리 입력해 두었다면 비워두어도 자동 적용됩니다.",
)

# 새 게임 시작 (세이브 파일 삭제 및 초기화) 버튼
if st.sidebar.button("🔄 새 게임 시작 (기존 저장 지우기)"):
  if os.path.exists(SAVE_FILE):
    os.remove(SAVE_FILE)
  for key in list(st.session_state.keys()):
    del st.session_state[key]
  st.rerun()

if not api_key_input:
  st.warning(
      "⚠️ 게임을 시작하려면 사이드바에 **Gemini API 키**를 입력해 주시거나, 코드"
      " 상단의 `DEFAULT_API_KEY` 변수에 키를 입력해 주세요."
  )
else:
  try:
    # 3. 클라이언트 및 세션 초기화 (세이브 파일 복원 기능 포함)
    if (
        "client" not in st.session_state
        or "chat_session" not in st.session_state
    ):
      st.session_state.client = genai.Client(api_key=api_key_input)

      system_instruction = (
          "당신은 몰입감 있는 정통 판타지 텍스트 RPG의 게임 마스터(GM)입니다. "
          "플레이어의 입력에 따라 흥미진진한 모험 상황을 묘사하고, "
          "매 턴 답변의 마지막 줄에 [상태: 체력 100/100, 골드 50, 소지품: 낡은 단검]과 같이 "
          "플레이어의 현재 상태를 업데이트해서 반드시 포함해 주세요."
      )

      # 세이브 파일이 존재하는지 확인
      loaded_messages = []
      if os.path.exists(SAVE_FILE):
        try:
          with open(SAVE_FILE, "r", encoding="utf-8") as f:
            loaded_messages = json.load(f)
        except Exception:
          loaded_messages = []

      st.session_state.messages = loaded_messages

      # 저장된 기록이 없다면 최초 오프닝 생성
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
              "눈을 떠보니 음산한 기운이 감도는 고대 던전의 지하 감옥입니다. 게임을"
              " 시작해 주세요."
          )
          response = st.session_state.chat_session.send_message(initial_prompt)
          st.session_state.messages = [{
              "role": "assistant",
              "content": f"🏰 **[모험이 시작되었습니다]**\n\n{response.text}",
          }]

          # 첫 세이브 파일 생성
          with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.messages, f, ensure_ascii=False)
      else:
        # 저장된 기록이 있는 경우, AI 모델이 이전 기억을 유지하도록 히스토리 복원
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

    # 4. 기존 대화 기록 화면에 출력
    for message in st.session_state.messages:
      with st.chat_message(message["role"]):
        st.markdown(message["content"])

    # 5. 사용자 입력(행동 지시) 처리 및 자동 저장
    if user_prompt := st.chat_input(
        "어떤 행동을 하시겠습니까? (예: 철창 흔들기, 북쪽 복도로 이동 등)"
    ):
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

      st.session_state.messages.append(
          {"role": "assistant", "content": bot_response}
      )

      # 💡 플레이어가 행동할 때마다 자동으로 'rpg_save.json' 파일에 실시간 저장
      with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, ensure_ascii=False)

  except Exception as e:
    st.error(
        f"❌ 오류가 발생했습니다. API 키가 올바른지 확인해 주세요. (상세 에러:"
        f" {e})"
    )
