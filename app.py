import json
import os
import random
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
st.title("⚔️ 판타지 텍스트 RPG 게임 마스터 (전투 중 스토리 동시 열람 버전)")
st.markdown(
    "전투 중에도 이전 스토리와 대화 내용을 확인하며 턴제 전투를 즐길 수 있는"
    " 텍스트 RPG 공간입니다."
)

# 📊 [캐릭터 종합 스탯 및 전투 관련 상태 초기화]
if "stats" not in st.session_state:
  st.session_state.stats = {
      "hp": 50,
      "max_hp": 50,
      "mp": 20,
      "max_mp": 20,
      "gold": 10,
      "level": 1,
      "equipment": {"무기": "녹슨 단검", "갑옷": "누더기 옷", "장신구": "없음"},
      "inventory": ["녹슨 단검", "체력 포션 (소)"],
      "skills": ["기본 찌르기", "급소 베기"],
  }

if "in_combat" not in st.session_state:
  st.session_state.in_combat = False
  st.session_state.pending_combat = False
  st.session_state.enemy = None
  st.session_state.pending_enemy = None
  st.session_state.combat_log = []

# ⚙️ [좌측 사이드바: 게임 설정 및 모델 선택 드롭다운]
st.sidebar.header("⚙️ 게임 설정 및 관리")

api_key_input = st.sidebar.text_input(
    "Google Gemini API 키 입력",
    value=DEFAULT_API_KEY,
    type="password",
    help="Google AI Studio에서 발급받은 API 키를 입력하세요.",
)

# 📌 사용 가능한 Flash/Lite 모델 목록 드롭다운
default_models = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash",
]

available_models = default_models
if api_key_input:
  try:
    temp_client = genai.Client(api_key=api_key_input)
    fetched = []
    for m in temp_client.models.list():
      m_name = getattr(m, "name", "")
      if m_name:
        clean_name = m_name.replace("models/", "")
        if "flash" in clean_name or "lite" in clean_name:
          fetched.append(clean_name)
    if fetched:
      available_models = sorted(list(set(fetched)))
  except Exception:
    pass

default_index = 0
if "gemini-3.5-flash-lite" in available_models:
  default_index = available_models.index("gemini-3.5-flash-lite")

selected_model = st.sidebar.selectbox(
    "사용할 Gemini 모델 선택",
    options=available_models,
    index=default_index,
    help="현재 API 계정에서 지원하는 모델 목록입니다.",
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


# ⚔️ [로컬 파이썬 전투 처리 함수]
def process_combat_action(action):
  player = st.session_state.stats
  enemy = st.session_state.enemy
  logs = st.session_state.combat_log

  skip_counter_attack = False

  if action == "공격":
    dmg = random.randint(6, 14)
    enemy["hp"] = max(0, enemy["hp"] - dmg)
    logs.append(
        f"⚔️ 나의 공격! **{enemy['name']}**에게 {dmg}의 피해를 입혔습니다."
    )

  elif action.startswith("스킬_"):
    skill_name = action.replace("스킬_", "")
    mp_cost = 8
    if player["mp"] < mp_cost:
      logs.append("❌ 마나(MP)가 부족하여 기술을 사용할 수 없습니다!")
      st.session_state.combat_log = logs
      return
    else:
      player["mp"] -= mp_cost
      dmg = random.randint(18, 30)
      enemy["hp"] = max(0, enemy["hp"] - dmg)
      logs.append(
          f"✨ 기술 [{skill_name}] 발동! **{enemy['name']}**에게 강력한"
          f" {dmg}의 피해를 입혔습니다. (MP -{mp_cost})"
      )

  elif action == "회피 시도":
    if random.random() < 0.5:
      logs.append("🏃 대성공! 적의 공격 궤도를 완벽히 읽고 회피했습니다!")
      skip_counter_attack = True
    else:
      logs.append("💨 회피 실패! 몸을 피하지 못하고 공격을 허용합니다...")

  elif action == "방어/블럭":
    logs.append("🛡️ 방어 태세를 취합니다! 이번 턴 받는 피해가 반으로 줄어듭니다.")

  elif action == "포션 사용":
    if "체력 포션 (소)" in player["inventory"]:
      player["inventory"].remove("체력 포션 (소)")
      heal = 25
      player["hp"] = min(player["max_hp"], player["hp"] + heal)
      logs.append(f"🧪 체력 포션을 마셔 HP가 {heal} 회복되었습니다!")
    else:
      logs.append("❌ 인벤토리에 체력 포션이 없습니다!")

  if enemy["hp"] > 0 and not skip_counter_attack:
    enemy_dmg = random.randint(5, 12)
    if action == "방어/블럭":
      enemy_dmg //= 2

    player["hp"] = max(0, player["hp"] - enemy_dmg)
    logs.append(
        f"💥 **{enemy['name']}**의 반격! 내게 {enemy_dmg}의 피해를 입혔습니다."
    )

  # 승리 판정
  if enemy["hp"] <= 0:
    reward_gold = random.randint(5, 15)
    player["gold"] += reward_gold
    logs.append(
        f"🎉 **[전투 승리!]** {enemy['name']}을(를) 쓰러뜨렸습니다! (보상:"
        f" {reward_gold} 골드 획득)"
    )
    st.session_state.in_combat = False

    if "chat_session" in st.session_state:
      try:
        post_prompt = (
            f"전투에서 승리했습니다! 상대는 '{enemy['name']}'였으며, {reward_gold} 골드를 획득했습니다. "
            f"전투가 끝난 직후의 상황을 생생하게 묘사하고, 플레이어가 다음에 고를 수 있는 선택지 2~3가지를 함께 제시해 주세요."
        )
        response = st.session_state.chat_session.send_message(post_prompt)
        ai_response = response.text
        st.session_state.messages.append({
            "role": "assistant",
            "content": (
                f"⚔️ **[전투 승리]** {enemy['name']}을(를) 물리쳤습니다! (보상:"
                f" {reward_gold} 골드)\n\n{ai_response}"
            ),
        })
      except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "content": (
                f"⚔️ **[전투 승리]** {enemy['name']}을(를) 물리쳤습니다! (보상:"
                f" {reward_gold} 골드)\n\n(다음 스토리 생성 중 에러 발생: {e})"
            ),
        })

  # 패배 판정
  elif player["hp"] <= 0:
    logs.append(
        "💀 **[치명패]** 체력이 모두 소모되어 쓰러졌습니다... 암흑이 찾아옵니다."
    )
    st.session_state.in_combat = False
    player["hp"] = 10

    if "chat_session" in st.session_state:
      try:
        post_prompt = (
            "전투에서 패배하여 쓰러졌으나 간신히 목숨을 건졌습니다. 플레이어가 정신을 차린 후의 "
            "처참한 상황을 묘사하고, 앞으로 어떻게 할 것인지 선택지 2~3가지를 제시해 주세요."
        )
        response = st.session_state.chat_session.send_message(post_prompt)
        ai_response = response.text
        st.session_state.messages.append({
            "role": "assistant",
            "content": (
                "💀 **[치명패]** 적에게 패배하여 정신을 잃었습니다...\n\n"
                f"{ai_response}"
            ),
        })
      except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "content": (
                "💀 **[치명패]** 적에게 패배하여 정신을 잃었습니다...\n\n(스토리"
                f" 생성 중 에러 발생: {e})"
            ),
        })

  st.session_state.combat_log = logs


# 🖥️ [메인 화면: 채팅 및 로컬 전투 영역]
if not api_key_input:
  st.warning("⚠️ 좌측 사이드바에 **Google Gemini API 키**를 입력해 주세요.")
else:
  try:
    if (
        "client" not in st.session_state
        or "chat_session" not in st.session_state
        or st.session_state.get("current_model") != selected_model
    ):
      st.session_state.client = genai.Client(api_key=api_key_input)
      st.session_state.current_model = selected_model

      system_instruction = (
          "당신은 몰입감 있는 정통 판타지 텍스트 RPG의 게임 마스터(GM)입니다. "
          "주인공은 현재 초라하고 매우 약한 상태(Lv.1, 녹슨 단검 소지)에서 시작합니다. "
          "절대로 플레이어를 과도하게 띄워주거나 쉽게 이기게 만들지 말고, 고난도 생존의 재미를 느낄 수 있도록 밸런스를 엄격하게 유지하세요. "
          "예상치 못한 불행, 자원 부족, 위기 상황이 자주 찾아오며, 때로는 극적인 행운이 찾아옵니다. "
          "직업은 전사, 마법사, 성직자, 궁수, 도적 중에서 선택할 수 있으며 각 직업별로 전문적인 스킬을 배우고 발전시킬 수 있습니다.\n"
          "매 프롬프트마다 전송되는 [현재 내 상태 정보]를 최우선 기준으로 삼아 스토리를 전개하고, 몬스터와 조우하여 **전투가 벌어지면**, 답변 본문 마지막 줄에 단독으로 "
          '[START_COMBAT: {"name": "초급 몬스터이름", "hp": 30, "atk": 8}] 형식의 JSON을 출력하여 전투 조우 신호를 보내세요.\n'
          "주의사항: 답변 본문에는 [상태: ...] 같은 텍스트 상태창을 절대 출력하지 마십시오. "
          "스탯 변동이 발생할 경우 반드시 답변 맨 마지막 줄에 단독으로 "
          '[JSON_UPDATE: {"hp": 숫자, "max_hp": 숫자, "mp": 숫자, "max_mp": 숫자, "gold": 숫자, "level": 숫자, "equipment": {"무기": "...", "갑옷": "..."}, "inventory": ["..."], "skills": ["..."]}] '
          "형식의 JSON 데이터를 남겨주세요."
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
            model=selected_model,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.8,
            ),
        )
        with st.spinner(
            f"[{selected_model}] 모델로 새로운 게임 세계를 생성하는 중입니다..."
        ):
          initial_prompt = (
              "눈을 떠보니 음산한 기운이 감도는 고대 던전의 지하 감옥입니다. 몸은 쇠약하고 쥐새끼가 울부짖는 최악의 환경입니다. 먼저 플레이어에게 "
              "어떤 직업(전사, 마법사, 성직자, 궁수, 도적 중 택1)을 선택할 것인지 묻고, "
              "앞으로 펼쳐질 고난도 생존 모험의 서막을 열어주세요. (선택지 5가지를 함께 제시해 주세요)"
          )
          try:
            response = st.session_state.chat_session.send_message(
                initial_prompt
            )
            bot_response = response.text
          except Exception as e:
            bot_response = (
                f"세계 생성 중 API 에러가 발생했습니다. (선택 모델: {selected_model})\n에러: {e}"
            )

          st.session_state.messages = [{
              "role": "assistant",
              "content": f"🏰 **[생존 모험이 시작되었습니다 ({selected_model})]**\n\n{bot_response}",
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
            model=selected_model,
            history=api_history if api_history else None,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.8,
            ),
        )

    # ================= [공통: 이전 대화 기록(스토리) 먼저 렌더링] =================
    for message in st.session_state.messages:
      with st.chat_message(message["role"]):
        if message["role"] == "assistant":
          clean_content = re.sub(
              r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]",
              "",
              message["content"],
              flags=re.DOTALL,
          )
          clean_content = re.sub(
              r"\[START_COMBAT:\s*(\{.*?\})\s*\]",
              "",
              clean_content,
              flags=re.DOTALL,
          ).strip()
          st.markdown(clean_content)
        else:
          st.markdown(message["content"])

    st.markdown("---")

    # ================= [화면 분기: 전투 대기(확인) vs 전투 중 vs 평상시 스토리 입력] =================
    if st.session_state.pending_combat:
      # ⚠️ [전투 시작 전 확인 화면]
      enemy = st.session_state.pending_enemy
      st.warning(
          f"⚠️ **[전투가 임박했습니다!]**\n\n상대: **{enemy['name']}**"
          " 조우!\n준비가 되었다면 아래 확인 버튼을 눌러 전투를 시작하세요."
      )

      if st.button("⚔️ 확인 (전투 시작)", use_container_width=True):
        st.session_state.in_combat = True
        st.session_state.enemy = st.session_state.pending_enemy
        st.session_state.pending_combat = False
        st.session_state.combat_log = [
            f"🚨 **{st.session_state.enemy['name']}**과의 긴장되는 전투가"
            " 시작되었습니다!"
        ]
        st.rerun()

    elif st.session_state.in_combat:
      # ⚔️ [로컬 전투 UI - API 호출 없음]
      enemy = st.session_state.enemy
      st.error(
          f"⚠️ **[긴급 생존 전투!]** 상대: **{enemy['name']}** (적 체력:"
          f" {enemy['hp']} / {enemy['max_hp']})"
      )

      # 기본 행동 버튼
      col1, col2, col3, col4 = st.columns(4)
      if col1.button("⚔️ 기본 공격", use_container_width=True):
        process_combat_action("공격")
        st.rerun()
      if col2.button("🏃 회피 시도", use_container_width=True):
        process_combat_action("회피 시도")
        st.rerun()
      if col3.button("🛡️ 방어/블럭", use_container_width=True):
        process_combat_action("방어/블럭")
        st.rerun()
      if col4.button("🧪 포션 사용", use_container_width=True):
        process_combat_action("포션 사용")
        st.rerun()

      st.markdown("---")

      # ✨ 전문 기술(스킬) 선택 영역
      st.markdown("##### ✨ 전문 기술 사용 (MP 8 소모)")
      available_skills = stats.get("skills", [])
      if available_skills:
        sc1, sc2 = st.columns([3, 1])
        with sc1:
          selected_skill = st.selectbox(
              "사용할 기술 선택",
              available_skills,
              label_visibility="collapsed",
          )
        with sc2:
          if st.button("✨ 기술 발동", use_container_width=True):
            process_combat_action(f"스킬_{selected_skill}")
            st.rerun()
      else:
        st.info("현재 배운 전문 기술이 없습니다.")

      st.markdown("---")
      st.markdown("##### 📜 실시간 전투 로그")
      for log in reversed(st.session_state.combat_log[-6:]):
        st.markdown(f"- {log}")

    else:
      # 📖 [평상시 스토리 입력 영역]
      if user_prompt := st.chat_input("어떤 행동을 하시겠습니까?"):
        st.session_state.messages.append(
            {"role": "user", "content": user_prompt}
        )
        with st.chat_message("user"):
          st.markdown(user_prompt)

        with st.chat_message("assistant"):
          with st.spinner("게임 마스터가 다음 상황을 계산 중입니다..."):
            try:
              current_stats = st.session_state.stats
              augmented_prompt = (
                  f"[현재 내 상태 정보 - HP: {current_stats['hp']}/{current_stats['max_hp']}, "
                  f"MP: {current_stats['mp']}/{current_stats['max_mp']}, "
                  f"골드: {current_stats['gold']}G, 레벨: {current_stats['level']}, "
                  f"인벤토리: {json.dumps(current_stats['inventory'], ensure_ascii=False)}]\n"
                  f"플레이어 행동: {user_prompt}"
              )

              response = st.session_state.chat_session.send_message(
                  augmented_prompt
              )
              bot_response = response.text

              # 1. 전투 시작 트리거 감지 ([START_COMBAT])
              combat_match = re.search(
                  r"\[START_COMBAT:\s*(\{.*?\})\s*\]", bot_response, re.DOTALL
              )
              if combat_match:
                try:
                  combat_data = json.loads(combat_match.group(1))
                  st.session_state.pending_combat = True
                  st.session_state.pending_enemy = {
                      "name": combat_data.get("name", "지하 쥐"),
                      "hp": combat_data.get("hp", 30),
                      "max_hp": combat_data.get("hp", 30),
                      "atk": combat_data.get("atk", 8),
                  }
                except Exception:
                  pass

              # 2. 스탯 업데이트 감지 ([JSON_UPDATE])
              match = re.search(
                  r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]", bot_response, re.DOTALL
              )
              stats_updated = False
              if match:
                try:
                  updated_data = json.loads(match.group(1))
                  for k, v in updated_data.items():
                    if k in st.session_state.stats:
                      if st.session_state.stats[k] != v:
                        st.session_state.stats[k] = v
                        stats_updated = True
                except Exception:
                  pass

              # 태그를 제외한 순수 텍스트 출력
              clean_bot_response = re.sub(
                  r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]",
                  "",
                  bot_response,
                  flags=re.DOTALL,
              )
              clean_bot_response = re.sub(
                  r"\[START_COMBAT:\s*(\{.*?\})\s*\]",
                  "",
                  clean_bot_response,
                  flags=re.DOTALL,
              ).strip()
              st.markdown(clean_bot_response)

              st.session_state.messages.append(
                  {"role": "assistant", "content": bot_response}
              )

              with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state.messages, f, ensure_ascii=False)

              if combat_match or stats_updated:
                st.rerun()

            except Exception as e:
              error_str = str(e)
              if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                warning_msg = (
                    "⚠️ **[API 사용량 한도 초과]** 무료 티어 요청 제한에"
                    f" 도달했습니다. (모델: {selected_model})\n"
                    "안내된 대기 시간(약 15~30초) 후 다시 시도해 주세요!"
                )
                st.warning(warning_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": warning_msg,
                })
              else:
                err_msg = f"❌ 오류가 발생했습니다: {e}"
                st.error(err_msg)

  except Exception as e:
    st.error(
        f"❌ 초기화 중 오류가 발생했습니다. API 키를 확인해 주세요. (상세 에러:"
        f" {e})"
    )
