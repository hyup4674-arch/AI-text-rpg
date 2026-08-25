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
st.title("⚔️ 판타지 텍스트 RPG 게임 마스터")
st.markdown(
    "Google Gemini API와 Streamlit을 연동하여, 선택지에 따라 스토리가"
    " 진행되며 좌측 사이드바 상태창이 실시간 연동되는 텍스트 RPG 공간입니다."
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

# ⚙️ [좌측 사이드바: 게임 설정, 상태창, 백업 관리 통합]
st.sidebar.header("⚙️ 게임 설정 및 관리")

api_key_input = st.sidebar.text_input(
    "Google Gemini API 키 입력",
    value=DEFAULT_API_KEY,
    type="password",
    help="Google AI Studio에서 발급받은 API 키를 입력하세요.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 캐릭터 상태창")

stats = st.session_state.stats
st.sidebar.metric(label="❤️ 체력 (HP)", value=f"{stats['hp']} / {stats['max_hp']}")
st.sidebar.metric(label="💙 마나 (MP)", value=f"{stats['mp']} / {stats['max_mp']}")
st.sidebar.metric(label="💰 보유 골드", value=f"{stats['gold']} G")
st.sidebar.metric(label="⭐ 레벨", value=f"Lv. {stats['level']}")

st.sidebar.markdown("---")
st.sidebar.markdown("##### ⚔️ 장착 장비")
for slot, item in stats["equipment"].items():
  st.sidebar.write(f"- **{slot}**: {item}")

st.sidebar.markdown("##### 🎒 인벤토리")
st.sidebar.write(
    f"{', '.join(stats['inventory']) if stats['inventory'] else '없음'}"
)

st.sidebar.markdown("##### ✨ 사용 가능 기술")
st.sidebar.write(
    f"{', '.join(stats['skills']) if stats['skills'] else '없음'}"
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

# 🖥️ [메인 화면: 채팅 영역 전용 레이아웃]
if not api_key_input:
  st.warning("⚠️ 좌측 사이드바에 **Google Gemini API 키**를 입력해 주세요.")
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
          "플레이어가 '1', '2' 같은 번호 선택지나 자유로운 텍스트로 행동을 입력하면, 그 선택에 따라 즉시 스토리를 다음 단계로 전개하고 흥미진진한 상황과 선택지를 묘사하세요.\n"
          "현재 플레이어의 상태 정보:\n"
          f"- HP: {current_stats['hp']}/{current_stats['max_hp']}\n"
          f"- MP: {current_stats['mp']}/{current_stats['max_mp']}\n"
          f"- 골드: {current_stats['gold']}, 레벨: {current_stats['level']}\n"
          f"- 장비: {json.dumps(current_stats['equipment'], ensure_ascii=False)}\n"
          f"- 인벤토리: {json.dumps(current_stats['inventory'], ensure_ascii=False)}\n"
          f"- 기술: {json.dumps(current_stats['skills'], ensure_ascii=False)}\n\n"
          "주의사항: 답변 본문에는 [상태: ...] 같은 텍스트 상태창을 절대 출력하지 마십시오. "
          "대신 스탯, 장비, 인벤토리, 기술 등의 변동이 발생할 경우(또는 유지될 경우) 반드시 답변 맨 마지막 줄에 단독으로 "
          '[JSON_UPDATE: {"hp": 숫자, "max_hp": 숫자, "mp": 숫자, "max_mp": 숫자, "gold": 숫자, "level": 숫자, "equipment": {"무기": "...", "갑옷": "..."}, "inventory": ["..."], "skills": ["..."]}] '
          "형식의 JSON 데이터만 남겨주세요."
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
              " 시작해 주세요. (플레이어가 고를 수 있는 선택지도 2~3가지 함께"
              " 제시해 주세요)"
          )
          response = st.session_state.chat_session.send_message(initial_prompt)
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

    # 대화 기록 렌더링 (출력 시 [JSON_UPDATE] 태그는 숨김 처리)
    for message in st.session_state.messages:
      with st.chat_message(message["role"]):
        if message["role"] == "assistant":
          clean_content = re.sub(
              r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]",
              "",
              message["content"],
              flags=re.DOTALL,
          ).strip()
          st.markdown(clean_content)
        else:
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

          # JSON 데이터를 파싱하여 사이드바 상태창 업데이트
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
            except Exception as e:
              pass

          # 채팅창에는 [JSON_UPDATE] 태그를 제외한 순수 스토리만 렌더링
          clean_bot_response = re.sub(
              r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]",
              "",
              bot_response,
              flags=re.DOTALL,
          ).strip()
          st.markdown(clean_bot_response)

      st.session_state.messages.append(
          {"role": "assistant", "content": bot_response}
      )

      with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, ensure_ascii=False)

      # 상태 업데이트를 즉시 반영하기 위해 화면 재실행
      st.rerun()

  except Exception as e:
    st.error(
        f"❌ 오류가 발생했습니다. API 키가 올바른지 확인해 주세요. (상세 에러:"
        f" {e})"
    )
