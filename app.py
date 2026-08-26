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
    page_title="에델가르드 패권전 - 판타지 RPG", page_icon="⚔️", layout="wide"
)
st.title("⚔️ 에델가르드: 4대 종족 대륙 패권전")
st.markdown(
    "오크, 인간, 엘프, 드워프가 대륙의 영토를 두고 다투는 역사의 소용돌이 속에서"
    " 마을을 방문하고 휴식을 취하며 착실히 세력을 키워나가세요."
)


# 💾 [세이브 파일 통합 저장 함수]
def save_game():
  data = {
      "stats": st.session_state.get("stats", {}),
      "messages": st.session_state.get("messages", []),
  }
  with open(SAVE_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)


# 🧹 [스킬 구조화 및 규격 정화 함수 (임의 변경 방지 고정)]
def normalize_skills(skills_list):
  # 플레이어 스킬은 시스템에 정의된 고정 구조 유지
  normalized = []
  for item in skills_list:
    if isinstance(item, dict):
      normalized.append({
          "name": item.get("name", "기본 공격"),
          "effect": item.get("effect", "기본 기술"),
          "power": item.get("power", 15),
          "mp_cost": item.get("mp_cost", 0),
      })
  return normalized


# 🧠 [한글/영문 키 자동 변환 및 증감 처리 스마트 스탯 업데이트 함수 (스킬 변경 원천 차단)]
def smart_update_stats(updated_data):
  key_map = {
      "지능": "int",
      "intelligence": "int",
      "int": "int",
      "힘": "str",
      "strength": "str",
      "str": "str",
      "체력스탯": "con",
      "체력": "con",
      "constitution": "con",
      "con": "con",
      "민첩": "agi",
      "agility": "agi",
      "agi": "agi",
      "골드": "gold",
      "Gold": "gold",
      "gold": "gold",
      "G": "gold",
      "체력(HP)": "hp",
      "HP": "hp",
      "hp": "hp",
      "최대체력": "max_hp",
      "max_hp": "max_hp",
      "마나": "mp",
      "MP": "mp",
      "mp": "mp",
      "최대마나": "max_mp",
      "max_mp": "max_mp",
      "레벨": "level",
      "level": "level",
      "경험치": "exp",
      "exp": "exp",
      "최대경험치": "max_exp",
      "max_exp": "max_exp",
      "인벤토리": "inventory",
      "inventory": "inventory",
      "장비": "equipment",
      "equipment": "equipment",
      # 주의: 'skills'는 LLM이 임의로 건드리지 못하도록 key_map에서 제외하여 스킬 고정 유지
      "종족": "race",
      "race": "race",
      "직업": "class_name",
      "class_name": "class_name",
      "평판": "reputation",
      "reputation": "reputation",
  }

  stats = st.session_state.stats
  for raw_k, v in updated_data.items():
    target_key = key_map.get(raw_k, raw_k)
    if target_key in stats:
      if target_key in ["str", "int", "con", "agi"]:
        if isinstance(v, (int, float)) and abs(v) <= 5:
          diff = int(v)
          stats[target_key] += diff
          if target_key == "con":
            hp_gain = diff * 2
            stats["max_hp"] += hp_gain
            stats["hp"] = min(stats["max_hp"], stats["hp"] + hp_gain)
          elif target_key == "int":
            mp_gain = diff * 2
            stats["max_mp"] += mp_gain
            stats["mp"] = min(stats["max_mp"], stats["mp"] + mp_gain)
        elif isinstance(v, str) and (v.startswith("+") or v.startswith("-")):
          try:
            diff = int(v)
            stats[target_key] += diff
            if target_key == "con":
              hp_gain = diff * 2
              stats["max_hp"] += hp_gain
              stats["hp"] = min(stats["max_hp"], stats["hp"] + hp_gain)
            elif target_key == "int":
              mp_gain = diff * 2
              stats["max_mp"] += mp_gain
              stats["mp"] = min(stats["max_mp"], stats["mp"] + mp_gain)
          except ValueError:
            pass
        else:
          new_val = int(v)
          if target_key == "con":
            diff = new_val - stats["con"]
            hp_gain = diff * 2
            stats["max_hp"] += hp_gain
            stats["hp"] = min(stats["max_hp"], stats["hp"] + hp_gain)
          elif target_key == "int":
            diff = new_val - stats["int"]
            mp_gain = diff * 2
            stats["max_mp"] += mp_gain
            stats["mp"] = min(stats["max_mp"], stats["mp"] + mp_gain)
          stats[target_key] = new_val
      elif target_key == "gold":
        if isinstance(v, str) and (v.startswith("+") or v.startswith("-")):
          try:
            stats["gold"] += int(v)
          except ValueError:
            pass
        else:
          stats["gold"] = int(v)
      else:
        stats[target_key] = v
  save_game()


# 📊 [세이브 데이터 로드 및 캐릭터 종합 스탯 초기화]
saved_stats = None
loaded_messages = []

if os.path.exists(SAVE_FILE):
  try:
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
      save_content = json.load(f)
      if isinstance(save_content, dict):
        saved_stats = save_content.get("stats")
        loaded_messages = save_content.get("messages", [])
      elif isinstance(save_content, list):
        loaded_messages = save_content
  except Exception:
    pass

if "stats" not in st.session_state:
  if saved_stats:
    st.session_state.stats = saved_stats
  else:
    st.session_state.stats = {
        "race": "미정",
        "class_name": "미정",
        "hp": 60,
        "max_hp": 60,
        "mp": 30,
        "max_mp": 30,
        "gold": 50,
        "level": 1,
        "exp": 0,
        "max_exp": 100,
        "str": 10,
        "int": 10,
        "con": 10,
        "agi": 10,
        "stat_points": 0,
        "reputation": {"인간": 0, "엘프": 0, "드워프": 0, "오크": 0},
        "equipment": {"무기": "초보자의 무기", "갑옷": "여행자 가죽옷", "장신구": "없음"},
        "inventory": ["체력 포션 (소)", "체력 포션 (소)", "건포도 빵"],
        "skills": [],
    }

if "messages" not in st.session_state:
  st.session_state.messages = loaded_messages

# ⚙️ [좌측 사이드바: 게임 설정 및 상태창]
st.sidebar.header("⚙️ 게임 설정 및 상태창")

api_key_input = st.sidebar.text_input(
    "Google Gemini API 키 입력",
    value=DEFAULT_API_KEY,
    type="password",
    help="Google AI Studio에서 발급받은 API 키를 입력하세요.",
)

# 📱 [폰트 크기 조절]
st.sidebar.markdown("---")
st.sidebar.subheader("📱 화면 및 글자 설정")
font_size = st.sidebar.slider(
    "🔤 글자 크기 조절 (px)",
    min_value=12,
    max_value=26,
    value=16,
    step=1,
)

# 🎨 [동적 CSS 및 강력한 자동 스크롤 방지 JS 주입]
st.markdown(
    f"""
    <style>
        .stChatMessage p, .stChatMessage div {{
            font-size: {font_size}px !important;
            line-height: 1.6 !important;
        }}
        .stButton button p {{
            font-size: {font_size + 1}px !important;
            font-weight: bold !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: {font_size + 3}px !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: {font_size - 1}px !important;
        }}
    </style>

    <script>
        (function() {{
            const pWin = window.parent || window;
            const pDoc = pWin.document;

            if (pWin.Element && !pWin.Element.prototype._scrollBlocker) {{
                pWin.Element.prototype._scrollBlocker = true;
                pWin.Element.prototype.scrollIntoView = function() {{}};
            }}

            function initScrollLock() {{
                const mainEl = pDoc.querySelector('.main') || pDoc.documentElement;
                if (!mainEl) return;

                if (pWin._savedScrollPos === undefined) {{
                    pWin._savedScrollPos = mainEl.scrollTop;
                }}

                mainEl.addEventListener('scroll', function() {{
                    pWin._savedScrollPos = mainEl.scrollTop;
                }}, {{ passive: true }});

                const restorePos = function() {{
                    if (pWin._savedScrollPos !== undefined && Math.abs(mainEl.scrollTop - pWin._savedScrollPos) > 10) {{
                        mainEl.scrollTop = pWin._savedScrollPos;
                    }}
                }};

                const observer = new MutationObserver(function() {{
                    restorePos();
                }});

                observer.observe(mainEl, {{ childList: true, subtree: true }});
                restorePos();
                setTimeout(restorePos, 100);
                setTimeout(restorePos, 300);
            }}

            if (pDoc.readyState === 'complete' || pDoc.readyState === 'interactive') {{
                initScrollLock();
            }} else {{
                pDoc.addEventListener('DOMContentLoaded', initScrollLock);
            }}
        }})();
    </script>
    """,
    unsafe_allow_html=True,
)

# 📌 모델 설정
default_models = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
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
if "gemini-3.1-flash-lite" in available_models:
  default_index = available_models.index("gemini-3.1-flash-lite")

selected_model = st.sidebar.selectbox(
    "Gemini 모델 선택",
    options=available_models,
    index=default_index,
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 캐릭터 상태창")

stats = st.session_state.stats

st.sidebar.markdown(
    f"👤 **종족**: `{stats['race']}` | **직업**: `{stats['class_name']}`"
)
st.sidebar.metric(label="⭐ 레벨", value=f"Lv. {stats['level']}")
st.sidebar.metric(
    label="✨ 경험치 (EXP)", value=f"{stats['exp']} / {stats['max_exp']}"
)
st.sidebar.metric(
    label="❤️ 체력 (HP)", value=f"{stats['hp']} / {stats['max_hp']}"
)
st.sidebar.metric(
    label="💙 마나 (MP)", value=f"{stats['mp']} / {stats['max_mp']}"
)
st.sidebar.metric(label="💰 보유 골드", value=f"{stats['gold']} G")

attack_power = stats["str"] * 1
evasion_rate = stats["agi"] * 1

st.sidebar.markdown("##### 📊 캐릭터 능력치")
st.sidebar.write(f"- 💪 **힘**: {stats['str']} (공격력: +{attack_power})")
st.sidebar.write(
    f"- 🧠 **지능**: {stats['int']} (마나: {stats['mp']}/{stats['max_mp']})"
)
st.sidebar.write(
    f"- ❤️ **체력 스탯**: {stats['con']} (체력: {stats['hp']}/{stats['max_hp']})"
)
st.sidebar.write(f"- ⚡ **민첩**: {stats['agi']} (회피율: {evasion_rate}%)")

# ⬆️ [스탯 포인트 투자 UI]
if stats.get("stat_points", 0) > 0:
  st.sidebar.success(f"🎉 **스탯 포인트**: {stats['stat_points']} P 남음")
  st.sidebar.caption("원하는 능력치를 클릭하면 **+5** 증가합니다:")
  col_s1, col_s2 = st.sidebar.columns(2)
  with col_s1:
    if st.sidebar.button("💪 힘 +5", key="btn_add_str", use_container_width=True):
      stats["str"] += 5
      stats["stat_points"] -= 5
      save_game()
      st.rerun()
    if st.sidebar.button(
        "❤️ 체력 +5", key="btn_add_con", use_container_width=True
    ):
      stats["con"] += 5
      hp_gain = 5 * 2
      stats["max_hp"] += hp_gain
      stats["hp"] = min(stats["max_hp"], stats["hp"] + hp_gain)
      stats["stat_points"] -= 5
      save_game()
      st.rerun()
  with col_s2:
    if st.sidebar.button(
        "🧠 지능 +5", key="btn_add_int", use_container_width=True
    ):
      stats["int"] += 5
      mp_gain = 5 * 2
      stats["max_mp"] += mp_gain
      stats["mp"] = min(stats["max_mp"], stats["mp"] + mp_gain)
      stats["stat_points"] -= 5
      save_game()
      st.rerun()
    if st.sidebar.button(
        "⚡ 민첩 +5", key="btn_add_agi", use_container_width=True
    ):
      stats["agi"] += 5
      stats["stat_points"] -= 5
      save_game()
      st.rerun()

# ⚔️ [보유 스킬 정보창 및 자동전투 pre-set 설정 (기본 스킬 1개 + 직업 특성 스킬 1개 고정)]
st.sidebar.markdown("---")
st.sidebar.subheader("✨ 보유 스킬 및 전투 설정 (총 2개 고정)")

st.session_state.stats["skills"] = normalize_skills(
    st.session_state.stats.get("skills", [])
)
skills_data = st.session_state.stats["skills"]

if skills_data:
  for sk in skills_data:
    st.sidebar.markdown(
        f"🗡️ **{sk['name']}**  \n"
        f"- **효과**: {sk['effect']}  \n"
        f"- **위력**: {sk['power']} | **MP 소모**: {sk['mp_cost']} MP"
    )
else:
  st.sidebar.write("보유한 스킬이 없습니다.")

st.sidebar.markdown("---")
st.sidebar.markdown("🎯 **[자동전투 사용 스킬 설정]**")
skill_options = (
    [sk["name"] for sk in skills_data] if skills_data else ["기본 공격"]
)

auto_s1 = st.sidebar.selectbox(
    "1순위 우선 스킬", options=skill_options, index=0, key="select_auto_skill_1"
)
auto_s2 = st.sidebar.selectbox(
    "2순위 차선 스킬",
    options=skill_options,
    index=min(1, len(skill_options) - 1),
    key="select_auto_skill_2",
)

st.sidebar.markdown("---")
st.sidebar.markdown("##### 🤝 종족별 평판")
if "reputation" in stats:
  for race, rep in stats["reputation"].items():
    st.sidebar.write(f"- **{race}**: {rep}")

st.sidebar.markdown("##### 🎒 인벤토리")
st.sidebar.write(
    f"{', '.join(stats['inventory']) if stats['inventory'] else '없음'}"
)

st.sidebar.markdown("---")
st.sidebar.subheader("💾 세이브 관리")

if os.path.exists(SAVE_FILE):
  with open(SAVE_FILE, "r", encoding="utf-8") as f:
    save_data_str = f.read()
  st.sidebar.download_button(
      label="📥 세이브 백업 (다운로드)",
      data=save_data_str,
      file_name="rpg_save.json",
      mime="application/json",
  )

uploaded_save = st.sidebar.file_uploader("📂 세이브 파일 불러오기", type=["json"])
if uploaded_save is not None:
  try:
    uploaded_bytes = uploaded_save.read()
    json.loads(uploaded_bytes.decode("utf-8"))
    with open(SAVE_FILE, "wb") as f:
      f.write(uploaded_bytes)
    st.sidebar.success("✅ 로드 완료!")
    st.rerun()
  except Exception as e:
    st.sidebar.error(f"로드 실패: {e}")

if st.sidebar.button("🔄 새 게임 시작"):
  if os.path.exists(SAVE_FILE):
    os.remove(SAVE_FILE)
  for key in list(st.session_state.keys()):
    del st.session_state[key]
  st.rerun()


# 🧹 [태그 정화 함수]
def clean_tags(text):
  text = re.sub(r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]", "", text, flags=re.DOTALL)
  text = re.sub(r"\[START_COMBAT:\s*(\{.*?\})\s*\]", "", text, flags=re.DOTALL)
  text = re.sub(r"\[CHOICES:\s*(\[.*?\])\s*\]", "", text, flags=re.DOTALL)
  return text.strip()


# 📈 [경험치 추가 및 레벨업 함수]
def add_exp(amount):
  player = st.session_state.stats
  player["exp"] += amount
  leveled_up = False
  while player["exp"] >= player["max_exp"]:
    player["exp"] -= player["max_exp"]
    player["level"] += 1
    player["max_exp"] = int(player["max_exp"] * 1.5)
    player["stat_points"] += 5
    hp_gain = 5 * 2
    mp_gain = 5 * 2
    player["max_hp"] += hp_gain
    player["hp"] = player["max_hp"]
    player["max_mp"] += mp_gain
    player["mp"] = player["max_mp"]
    leveled_up = True
  save_game()
  return leveled_up


# ⚔️ [자동 전투 시뮬레이션 함수 - 성직자 치유 및 스킬 고정 적용]
def run_automatic_combat(enemy_data):
  player = st.session_state.stats
  enemy = {
      "name": enemy_data.get("name", "적 정찰병"),
      "hp": enemy_data.get("hp", 40),
      "max_hp": enemy_data.get("hp", 40),
      "atk": enemy_data.get("atk", 10),
  }
  combat_logs = [
      f"🚨 **[교전 발생]** 적 세력 **{enemy['name']}**(HP:"
      f" {enemy['hp']})과 전투가 시작되었습니다!"
  ]

  skills_map = {
      sk["name"]: sk for sk in normalize_skills(player.get("skills", []))
  }
  s1_obj = skills_map.get(auto_s1)
  s2_obj = skills_map.get(auto_s2)

  def process_skill_turn(sk_obj):
    player["mp"] -= sk_obj["mp_cost"]
    base_pow = sk_obj.get("power", 20)

    # 성직자의 '치유' 스킬인 경우: 공격력 없음, 자신만 치유
    if sk_obj["name"] == "치유":
      heal_amount = base_pow + (player["int"] // 2)
      player["hp"] = min(player["max_hp"], player["hp"] + heal_amount)
      combat_logs.append(
          f"✨ **{sk_obj['name']}** 발동! ({sk_obj['effect']}) "
          f"HP가 **+{heal_amount}** 회복되었습니다! (내 HP:"
          f" {player['hp']}/{player['max_hp']})"
      )
    else:
      attack_power = player["str"]
      dmg = (
          random.randint(max(1, base_pow - 3), base_pow + 5)
          + attack_power
          + (player["int"] // 3)
      )
      enemy["hp"] = max(0, enemy["hp"] - dmg)
      combat_logs.append(
          f"✨ **{sk_obj['name']}** 발동! ({sk_obj['effect']}) "
          f"**{enemy['name']}**에게 {dmg}의 피해를 입혔습니다! (적 남은 HP:"
          f" {enemy['hp']}/{enemy['max_hp']})"
      )

  turn = 1
  while enemy["hp"] > 0 and player["hp"] > 0 and turn <= 12:
    combat_logs.append(f"\n--- [전투 턴 {turn}] ---")

    if (
        player["hp"] < (player["max_hp"] * 0.4)
        and "체력 포션 (소)" in player["inventory"]
    ):
      player["inventory"].remove("체력 포션 (소)")
      heal = 30
      player["hp"] = min(player["max_hp"], player["hp"] + heal)
      combat_logs.append(
          f"🧪 포션을 마셔 HP가 {heal} 회복되었습니다! (현재 HP:"
          f" {player['hp']}/{player['max_hp']})"
      )

    elif s1_obj and player["mp"] >= s1_obj["mp_cost"]:
      process_skill_turn(s1_obj)

    elif s2_obj and player["mp"] >= s2_obj["mp_cost"]:
      process_skill_turn(s2_obj)

    else:
      attack_power = player["str"]
      dmg = random.randint(8, 16) + attack_power
      enemy["hp"] = max(0, enemy["hp"] - dmg)
      combat_logs.append(
          f"⚔️ 기본 공격! **{enemy['name']}**에게 {dmg}의 피해를 입혔습니다. (적 남은"
          f" HP: {enemy['hp']}/{enemy['max_hp']})"
      )

    if enemy["hp"] <= 0:
      break

    evasion_rate = player["agi"] * 1
    if random.randint(1, 100) <= evasion_rate:
      combat_logs.append(
          f"💨 **[회피 성공!]** 민첩한 몸놀림으로 **{enemy['name']}**의 공격을"
          " 피해냈습니다!"
      )
    else:
      enemy_dmg = max(
          1,
          random.randint(enemy["atk"] - 2, enemy["atk"] + 4)
          - (player["con"] // 5),
      )
      player["hp"] = max(0, player["hp"] - enemy_dmg)
      combat_logs.append(
          f"💥 **{enemy['name']}**의 반격! {enemy_dmg}의 피해를 입었습니다. (내"
          f" 남은 HP: {player['hp']}/{player['max_hp']})"
      )

    turn += 1

  result_text = "\n".join(combat_logs)
  if enemy["hp"] <= 0:
    reward_gold = random.randint(15, 35)
    reward_exp = random.randint(40, 70)
    player["gold"] += reward_gold
    leveled = add_exp(reward_exp)

    result_text += (
        f"\n\n🎉 **[전투 승리!]** 적을 제압했습니다! (보상: {reward_gold}G,"
        f" {reward_exp} EXP 획득)"
    )
    if leveled:
      result_text += (
          f"\n🎊 **[레벨 업!]** Lv.{player['level']} 달성! 좌측 사이드바에서 스탯"
          " 포인트(5P)를 분배하세요!"
      )
    save_game()
    return result_text, True, reward_gold
  else:
    player["hp"] = max(10, player["max_hp"] // 4)
    result_text += (
        "\n\n💀 **[전투 패배]** 부상을 입고 후퇴했습니다. 인근 마을 여관에서"
        " 간신히 치료를 받았습니다."
    )
    save_game()
    return result_text, False, 0


# 🖥️ [채팅 인터페이스 및 캐릭터 생성 단계]
if not api_key_input:
  st.warning("⚠️ 좌측 사이드바에 **Google Gemini API 키**를 입력해 주세요.")
else:
  # 🌟 [1단계: 종족 선택 인터페이스]
  if st.session_state.stats["race"] == "미정":
    st.info(
        "🌍 **[캐릭터 생성 - 1단계/2단계]** 에델가르드 대륙에 오신 것을"
        " 환영합니다. 먼저 당신의 **종족**을 선택해 주세요."
    )

    col_r1, col_r2 = st.columns(2)
    with col_r1:
      if st.button("👑 인간 (Imperials)", use_container_width=True):
        st.session_state.stats["race"] = "인간"
        save_game()
        st.rerun()
      if st.button("🌿 엘프 (High Elves)", use_container_width=True):
        st.session_state.stats["race"] = "엘프"
        save_game()
        st.rerun()
    with col_r2:
      if st.button("⚒️ 드워프 (Mountain Dwarves)", use_container_width=True):
        st.session_state.stats["race"] = "드워프"
        save_game()
        st.rerun()
      if st.button("🪓 오크 (War Hordes)", use_container_width=True):
        st.session_state.stats["race"] = "오크"
        save_game()
        st.rerun()

  # 🌟 [2단계: 직업 선택 인터페이스 (기본스킬 1개 + 특성스킬 1개 총 2개 고정 부여)]
  elif st.session_state.stats["class_name"] == "미정":
    st.info(
        f"✨ **[캐릭터 생성 - 2단계/2단계]** 선택하신 종족:"
        f" **{st.session_state.stats['race']}**  \n아래에서 모험에서 정진할"
        " **직업**을 선택해 주세요."
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    chosen_class = None
    if c1.button("⚔️ 전사", use_container_width=True):
      chosen_class = "전사"
    elif c2.button("🔮 마법사", use_container_width=True):
      chosen_class = "마법사"
    elif c3.button("🏹 궁수", use_container_width=True):
      chosen_class = "궁수"
    elif c4.button("🗡️ 도적", use_container_width=True):
      chosen_class = "도적"
    elif c5.button("✨ 성직자", use_container_width=True):
      chosen_class = "성직자"

    if chosen_class:
      st.session_state.stats["class_name"] = chosen_class

      if chosen_class == "전사":
        st.session_state.stats["equipment"]["무기"] = "강철 단검"
        st.session_state.stats["skills"] = [
            {
                "name": "기본 베기",
                "effect": "마나 소모가 없는 근접 기본 물리 타격",
                "power": 15,
                "mp_cost": 0,
            },
            {
                "name": "강력한 일격",
                "effect": "급소를 겨냥한 강력한 물리 강타",
                "power": 30,
                "mp_cost": 8,
            },
        ]
      elif chosen_class == "마법사":
        st.session_state.stats["equipment"]["무기"] = "수습 마법봉"
        st.session_state.stats["skills"] = [
            {
                "name": "마력 화살",
                "effect": "마나 소모가 없는 기본 원거리 마법 타격",
                "power": 15,
                "mp_cost": 0,
            },
            {
                "name": "화염구",
                "effect": "강력한 화염 속성 마법 타격",
                "power": 35,
                "mp_cost": 12,
            },
        ]
      elif chosen_class == "궁수":
        st.session_state.stats["equipment"]["무기"] = "목재 단궁"
        st.session_state.stats["skills"] = [
            {
                "name": "정밀 사격",
                "effect": "마나 소모가 없는 원거리 관통 사격",
                "power": 15,
                "mp_cost": 0,
            },
            {
                "name": "연사",
                "effect": "빠른 속도의 연속 화살 사격",
                "power": 32,
                "mp_cost": 9,
            },
        ]
      elif chosen_class == "도적":
        st.session_state.stats["equipment"]["무기"] = "쌍 단검"
        st.session_state.stats["skills"] = [
            {
                "name": "기습",
                "effect": "마나 소모가 없는 허점 찌르기 공격",
                "power": 15,
                "mp_cost": 0,
            },
            {
                "name": "독침 베기",
                "effect": "독을 바른 단검으로 물리 타격",
                "power": 33,
                "mp_cost": 10,
            },
        ]
      elif chosen_class == "성직자":
        st.session_state.stats["equipment"]["무기"] = "나무 메이스"
        st.session_state.stats["skills"] = [
            {
                "name": "신성한 타격",
                "effect": "마나 소모가 없는 신력 기반 물리 공격",
                "power": 15,
                "mp_cost": 0,
            },
            {
                "name": "치유",
                "effect": "공격력 없이 자신의 체력만 회복하는 특성 기술",
                "power": 35,
                "mp_cost": 10,
            },
        ]
      save_game()
      st.rerun()

  # 🌟 [본격 게임 시작: Gemini API 연결]
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
            "당신은 4대 종족(인간, 엘프, 드워프, 오크)이 대륙 패권을 다투는"
            " '에델가르드 대륙'의 게임 마스터(GM)입니다.\n주인공은 전투뿐만"
            " 아니라 마을/영지 방문, 여관 휴식, 상점 이용(아이템/스탯 상품"
            " 거래), 정세 파악, 무역/퀘스트를 진행하며 성장합니다.\n\n📍 [절대"
            " 엄수 규칙 - 스킬 임의 변경 금지]:\n플레이어의 스킬 목록은"
            " **마나 소모 없는 기본 스킬 1개와 직업 특성 스킬 1개(총 2개)**로"
            " 영구 고정되어 있습니다. 게임 마스터는 절대 임의로 새로운 스킬을"
            " 만들거나 부여하거나 기존 스킬을 수정할 수 없습니다.\n\n📍 [상점 및"
            " 스탯/골드 거래 필수 지침]:\n플레이어가 상점에서 아이템이나 스탯"
            " 상승 상품을 구매/판매하거나 골드를 소모할 경우, 차감 또는 추가된"
            " 골드(gold)와 변경된 스탯(int, str, con, agi, hp, max_hp, mp,"
            " max_mp)의 **최종 계산 수치** 또는 증가치를 반드시"
            " [JSON_UPDATE] 태그에 출력하세요.\n\n📍 [태그 출력 규칙]:\n1. 교전"
            " 시: [START_COMBAT: {\"name\": \"적 이름\", \"hp\": 40, \"atk\":"
            " 10}]\n2. 상태/스탯 변동 시: [JSON_UPDATE: {\"str\": 숫자, \"int\":"
            " 숫자, \"con\": 숫자, \"agi\": 숫자, \"gold\": 숫자, \"hp\": 숫자,"
            " \"max_hp\": 숫자, \"mp\": 숫자, \"max_mp\": 숫자, \"inventory\":"
            " [...]}]\n3. 행동 선택지: [CHOICES: [\"선택지1\", \"선택지2\","
            " \"선택지3\"]]"
        )

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
                temperature=0.85,
            ),
        )

        if not st.session_state.messages:
          with st.spinner(
              f"[{selected_model}] 에델가르드 대륙의 세력 정세를 생성하는"
              " 중입니다..."
          ):
            p_race = st.session_state.stats["race"]
            p_class = st.session_state.stats["class_name"]
            initial_prompt = (
                f"플레이어는 **{p_race}** 종족의 **{p_class}** 직업으로 캐릭터를"
                " 완성했습니다.\n에델가르드 대륙은 인간 제국, 엘프 고대숲,"
                " 드워프 요새, 오크 연맹의 4대 세력전으로 소용돌이치고"
                " 있습니다. 주인공은 국경 중립 도시 '크로스로드' 여관에서 눈을"
                " 떴습니다.\n주인공의 종족과 직업적 분위기를 고려한 입체적인"
                " 몰입 서막을 열어주고, 마을에서 취할 수 있는 자율 선택지"
                " 4가지를 태그 [CHOICES: ...]로 제시해 주세요."
            )
            try:
              response = st.session_state.chat_session.send_message(
                  initial_prompt
              )
              bot_response = response.text
            except Exception as e:
              bot_response = f"세계 생성 중 오류가 발생했습니다: {e}"

            st.session_state.messages = [{
                "role": "assistant",
                "content": (
                    f"🌍 **[에델가르드 패권전 서막 - {p_race}"
                    f" {p_class}]**\n\n{bot_response}"
                ),
            }]
            save_game()

      # 📖 [채팅 히스토리 렌더링]
      for message in st.session_state.messages:
        with st.chat_message(message["role"]):
          if message["role"] == "assistant":
            st.markdown(clean_tags(message["content"]))
          else:
            st.markdown(message["content"])

      # 🎯 [선택지 버튼 UI 생성]
      current_choices = []
      if st.session_state.messages:
        last_msg = st.session_state.messages[-1]
        if last_msg["role"] == "assistant":
          choices_match = re.search(
              r"\[CHOICES:\s*(\[.*?\])\s*\]", last_msg["content"], re.DOTALL
          )
          if choices_match:
            try:
              current_choices = json.loads(choices_match.group(1))
            except Exception:
              current_choices = []

      selected_button_prompt = None
      if current_choices:
        st.markdown("##### 🎯 행동 선택 (버튼을 클릭하세요)")
        for idx, choice in enumerate(current_choices):
          if st.button(
              f"👉 {choice}",
              key=f"btn_{len(st.session_state.messages)}_{idx}",
              use_container_width=True,
          ):
            selected_button_prompt = choice

      # 💡 [선택지 아래 여백 추가]
      st.markdown(
          "<br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True
      )

      chat_input_prompt = st.chat_input("또는 직접 행동을 작성하세요...")
      user_prompt = selected_button_prompt or chat_input_prompt

      # 💬 [사용자 프롬프트 전송 및 처리]
      if user_prompt:
        st.session_state.messages.append(
            {"role": "user", "content": user_prompt}
        )
        with st.chat_message("user"):
          st.markdown(user_prompt)

        with st.chat_message("assistant"):
          with st.spinner("게임 마스터가 다음 상황을 계산 중입니다..."):
            try:
              cur_stats = st.session_state.stats
              augmented_prompt = (
                  f"[현재 캐릭터 스탯 - 종족: {cur_stats['race']}, 직업:"
                  f" {cur_stats['class_name']}, HP:"
                  f" {cur_stats['hp']}/{cur_stats['max_hp']}, MP:"
                  f" {cur_stats['mp']}/{cur_stats['max_mp']}, EXP:"
                  f" {cur_stats['exp']}/{cur_stats['max_exp']}, 골드:"
                  f" {cur_stats['gold']}G, 레벨: {cur_stats['level']},"
                  f" 힘:{cur_stats['str']}, 지능:{cur_stats['int']},"
                  f" 체력스탯:{cur_stats['con']}, 민첩:{cur_stats['agi']},"
                  f" 인벤토리:"
                  f" {json.dumps(cur_stats['inventory'], ensure_ascii=False)}]\n플레이어"
                  f" 행동: {user_prompt}"
              )

              response = st.session_state.chat_session.send_message(
                  augmented_prompt
              )
              bot_response = response.text
              final_output = bot_response

              # 1. 전투 발생 체크
              combat_match = re.search(
                  r"\[START_COMBAT:\s*(\{.*?\})\s*\]", bot_response, re.DOTALL
              )
              if combat_match:
                try:
                  combat_data = json.loads(combat_match.group(1))
                  combat_log_text, victory, reward_gold = (
                      run_automatic_combat(combat_data)
                  )

                  base_story = clean_tags(bot_response)
                  updated_stats = st.session_state.stats

                  post_prompt = (
                      f"전투 결과: {'승리' if victory else '패배'}, 보상"
                      f" 골드: {reward_gold}G. [현재 실제 스탯 - HP:"
                      f" {updated_stats['hp']}/{updated_stats['max_hp']}, 골드:"
                      f" {updated_stats['gold']}G, EXP:"
                      f" {updated_stats['exp']}/{updated_stats['max_exp']}]."
                      " 전투 직후 현장 상황을 생생히 묘사하고,"
                      " 휴식/이동/영지 방문 등 다음 행동 선택지를 제시해"
                      " 주세요."
                  )
                  post_response = st.session_state.chat_session.send_message(
                      post_prompt
                  )
                  post_text_clean = clean_tags(post_response.text)

                  authoritative_json = json.dumps(
                      {
                          "race": updated_stats["race"],
                          "class_name": updated_stats["class_name"],
                          "hp": updated_stats["hp"],
                          "max_hp": updated_stats["max_hp"],
                          "mp": updated_stats["mp"],
                          "max_mp": updated_stats["max_mp"],
                          "gold": updated_stats["gold"],
                          "level": updated_stats["level"],
                          "exp": updated_stats["exp"],
                          "max_exp": updated_stats["max_exp"],
                          "str": updated_stats["str"],
                          "int": updated_stats["int"],
                          "con": updated_stats["con"],
                          "agi": updated_stats["agi"],
                          "reputation": updated_stats.get("reputation", {}),
                          "equipment": updated_stats["equipment"],
                          "inventory": updated_stats["inventory"],
                          "skills": updated_stats["skills"],
                      },
                      ensure_ascii=False,
                  )

                  post_choices_match = re.search(
                      r"\[CHOICES:\s*(\[.*?\])\s*\]",
                      post_response.text,
                      re.DOTALL,
                  )
                  post_choices_str = (
                      post_choices_match.group(0)
                      if post_choices_match
                      else '[CHOICES: ["여관으로 가서 휴식", "마을 길드로 이동"]]'
                  )

                  final_output = (
                      f"{base_story}\n\n---\n{combat_log_text}\n---\n\n{post_text_clean}\n\n[JSON_UPDATE:"
                      f" {authoritative_json}]\n{post_choices_str}"
                  )
                except Exception as e:
                  final_output += f"\n\n(전투 처리 중 오류: {e})"

              # 2. 스탯 반영
              matches = re.findall(
                  r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]", final_output, re.DOTALL
              )
              if matches:
                try:
                  updated_data = json.loads(matches[-1])
                  smart_update_stats(updated_data)
                except Exception:
                  pass

              st.markdown(clean_tags(final_output))
              st.session_state.messages.append(
                  {"role": "assistant", "content": final_output}
              )
              save_game()

              st.rerun()

            except Exception as e:
              st.error(f"❌ 오류가 발생했습니다: {e}")

    except Exception as e:
      st.error(f"❌ 초기화 오류: {e}")
