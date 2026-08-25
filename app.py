from google import genai
from google.genai import types
import json
import os
import streamlit as st

# 🔑 [API 키 미리 입력 설정]
DEFAULT_API_KEY = ""

SAVE_FILE = "rpg_save.json"

st.set_page_config(
    page_title="Gemini 텍스트 RPG 시뮬레이터", page_icon="⚔️", layout="centered"
)
st.title("⚔️ 판타지 텍스트 RPG 게임 마스터")
st.markdown(
    "Google Gemini API와 Streamlit을 연동하여 스마트폰과 PC에서 즐기는 무제한"
    " 텍스트 RPG 공간입니다."
)

# 2. 사이드바 - 설정 및 세이브 백업 관리
st.sidebar.header("⚙️ 게임 설정 및 백업")

api_key_input = st.sidebar.text_input(
    "Google Gemini API 키 입력",
    value=DEFAULT_API_KEY,
    type="password",
    help="미리 입력해 두었다면 생략 가능합니다.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("💾 세이브 파일 관리")

# [기능 1] 현재 세이브 파일을 스마트폰/PC로 다운로드하는 버튼
if os.path.exists(SAVE_FILE):
  with open(SAVE_FILE, "r", encoding="utf-8") as f:
    save_data_str = f.read()
  st.sidebar.download_button(
      label="📥 내 세이브 파일 백업 (다운로드)",
      data=save_data_str,
      file_name="rpg_save.json",
      mime="application/json",
      help=(
          "게임을 마치기 전 이 버튼을 눌러 스마트폰에 세이브 파일을"
          " 저장하세요!"
      ),
  )

# [기능 2] 백업해둔 세이브 파일을 업로드해서 불러오는 기능
uploaded_save = st.sidebar.file_uploader(
    "📂 백업한 세이브 파일 불러오기",
    type=["json"],
    help="이전에 백업해 둔 json 파일을 업로드하면 즉시 이어서 할 수 있습니다.",
)

if uploaded_save is not None:
  try:
    # 업로드된 파일 내용을 읽어서 현재 세이브 파일로 덮어쓰기
    uploaded_bytes = uploaded_save.read()
    with open(SAVE_FILE, "wb") as f:
      f.write(uploaded_bytes)
    st.sidebar.success("✅ 세이브 파일을 성공적으로 불러왔습니다!")
    st.rerun()
  except Exception as e:
    st.sidebar.error(f"세이브 로드 실패: {e}")

# 새 게임 시작 버튼
if st.sidebar.button("🔄 새 게임 시작 (초기화)"):
  if os.path.exists(SAVE_FILE):
    os.remove(SAVE_FILE)
  for key in list(st.session_state.keys()):
    del st.session_state[key]
  st.rerun()

st.sidebar.markdown("---")

if not api_key_input:
  st.warning("⚠️ 사이드바에 **Gemini API 키**를 입력해 주세요.")
else:
  try:
    # 3. 클라이언트 및 세션 초기화
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
              "눈을 떠보니 음산한 기운이 감도는 고대 던전의 지하 감옥입니다. 게임을"
              " 시작해 주세요."
          )
          response = st.session_state.chat_session.send_message(initial_prompt)
          st.session_state.messages = [{
              "role": "assistant",
              "content": f"🏰 **[모험이 시작되었습니다]**\n\n{response.text}",
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

    # 4. 대화 기록 출력
    for message in st.session_state.messages:
      with st.chat_message(message["role"]):
        st.markdown(message["content"])

    # 5. 사용자 입력 처리 및 자동 저장
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

      st.session_state.messages.append(
          {"role": "assistant", "content": bot_response}
      )

      with open(SAVE_FILE, "w", encoding="utf-8") 방식로 as f:
        pass  # syntax fix below for safety
