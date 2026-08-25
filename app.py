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
st.title("⚔️ 판타지 텍스트 RPG 게임 마스터")
st.markdown(
    "몬스터 조우 시 자동 전투가 수행되며, 모바일 환경에 최적화된 선택지 버튼 클릭으로 손쉽게 플레이할 수 있습니다."
)

# 📊 [캐릭터 종합 스탯 초기화]
if "stats" not in st.session_state:
    st.session_state.stats = {
        "hp": 50,
        "max_hp": 50,
        "mp": 20,
        "max_mp": 20,
        "gold": 10,
        "level": 1,
        "equipment": {"무기": "녹슨 단검", "갑옷": "누더기 옷", "장신구": "없음"},
        "inventory": ["녹슨 단검", "체력 포션 (소)", "체력 포션 (소)"],
        "skills": ["소환술1단계", "약한 회복"],
    }

# ⚙️ [좌측 사이드바: 게임 설정 및 모델 선택 드롭다운]
st.sidebar.header("⚙️ 게임 설정 및 관리")

api_key_input = st.sidebar.text_input(
    "Google Gemini API 키 입력",
    value=DEFAULT_API_KEY,
    type="password",
    help="Google AI Studio에서 발급받은 API 키를 입력하세요.",
)

# 📱 [폰트 크기 및 화면 설정]
st.sidebar.markdown("---")
st.sidebar.subheader("📱 화면 및 글자 설정")
font_size = st.sidebar.slider(
    "🔤 글자 크기 조절 (px)",
    min_value=12,
    max_value=26,
    value=16,
    step=1,
    help="모바일 등 작은 화면에서 글자가 너무 작거나 클 때 조절하세요.",
)

# 🎨 [동적 CSS 및 자동 스크롤 방지 JS 주입]
st.markdown(
    f"""
    <style>
        /* 채팅 메시지 글자 크기 및 줄간격 설정 */
        .stChatMessage p, .stChatMessage div {{
            font-size: {font_size}px !important;
            line-height: 1.6 !important;
        }}
        /* 선택지 버튼 글자 크기 설정 */
        .stButton button p {{
            font-size: {font_size + 1}px !important;
            font-weight: bold !important;
        }}
        /* 상태창 메트릭 글자 크기 설정 */
        [data-testid="stMetricValue"] {{
            font-size: {font_size + 4}px !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: {font_size - 1}px !important;
        }}
    </style>

    <script>
        // Streamlit이 답변 생성 및 rerun 시 화면을 맨 아래로 강제 스크롤하는 동작 차단
        if (window.parent && window.parent.Element) {{
            window.parent.Element.prototype.scrollIntoView = function() {{}};
        }}
    </script>
    """,
    unsafe_allow_html=True,
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


# 🧹 [시스템 제어 태그 제거 공통 함수]
def clean_tags(text):
    text = re.sub(r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[START_COMBAT:\s*(\{.*?\})\s*\]", "", text, flags=re.DOTALL)
    text = re.sub(r"\[CHOICES:\s*(\[.*?\])\s*\]", "", text, flags=re.DOTALL)
    return text.strip()


# ⚔️ [자동 전투 시뮬레이션 처리 함수]
def run_automatic_combat(enemy_data):
    player = st.session_state.stats
    enemy = {
        "name": enemy_data.get("name", "지하 쥐"),
        "hp": enemy_data.get("hp", 30),
        "max_hp": enemy_data.get("hp", 30),
        "atk": enemy_data.get("atk", 8),
    }
    combat_logs = [
        f"🚨 **[긴급 전투 발생]** 강력한 적 **{enemy['name']}**(HP:"
        f" {enemy['hp']})과(와) 조우하여 자동으로 전투를 시작합니다!"
    ]

    turn = 1
    while enemy["hp"] > 0 and player["hp"] > 0 and turn <= 12:
        combat_logs.append(f"\n--- [전투 턴 {turn}] ---")

        # 1. 체력이 40% 미만이고 인벤토리에 포션이 있으면 자동 사용
        if (
            player["hp"] < (player["max_hp"] * 0.4)
            and "체력 포션 (소)" in player["inventory"]
        ):
            player["inventory"].remove("체력 포션 (소)")
            heal = 25
            player["hp"] = min(player["max_hp"], player["hp"] + heal)
            combat_logs.append(
                f"🧪 위급 상황! 체력 포션을 마셔 HP가 {heal} 회복되었습니다! (현재"
                f" HP: {player['hp']}/{player['max_hp']})"
            )
        # 2. 마나가 충분하면(>=8) 스킬 사용, 아니면 기본 공격
        elif player["mp"] >= 8 and player["skills"]:
            player["mp"] -= 8
            dmg = random.randint(18, 30)
            enemy["hp"] = max(0, enemy["hp"] - dmg)
            combat_logs.append(
                f"✨ 필살기 발동! **{enemy['name']}**에게 강력한 {dmg}의 피해를"
                f" 입혔습니다. (적 남은 HP: {enemy['hp']}/{enemy['max_hp']})"
            )
        else:
            dmg = random.randint(6, 14)
            enemy["hp"] = max(0, enemy["hp"] - dmg)
            combat_logs.append(
                f"⚔️ 기본 공격! **{enemy['name']}**에게 {dmg}의 피해를 입혔습니다."
                f" (적 남은 HP: {enemy['hp']}/{enemy['max_hp']})"
            )

        # 적이 쓰러졌으면 종료
        if enemy["hp"] <= 0:
            break

        # 3. 적의 반격
        enemy_dmg = random.randint(max(2, enemy["atk"] - 2), enemy["atk"] + 4)
        player["hp"] = max(0, player["hp"] - enemy_dmg)
        combat_logs.append(
            f"💥 **{enemy['name']}**의 반격! 주인공에게 {enemy_dmg}의 피해를"
            f" 입혔습니다. (내 남은 HP: {player['hp']}/{player['max_hp']})"
        )

        turn += 1

    # 전투 결과 판정
    result_text = "\n".join(combat_logs)
    if enemy["hp"] <= 0:
        reward_gold = random.randint(5, 15)
        player["gold"] += reward_gold
        result_text += (
            f"\n\n🎉 **[전투 승리!]** {enemy['name']}을(를) 격파했습니다! (보상:"
            f" {reward_gold} 골드 획득)"
        )
        return result_text, True, reward_gold
    else:
        player["hp"] = max(5, player["max_hp"] // 4)
        result_text += "\n\n💀 **[전투 패배]** 적의 공세를 견디지 못하고 정신을 잃었습니다... 간신히 목숨을 건졌습니다."
        return result_text, False, 0


# 🖥️ [메인 화면: 채팅 인터페이스]
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
                "당신은 몰입감 있는 정통 판타지 텍스트 RPG의 게임 마스터(GM)입니다. 휴먼.오크.엘프.드워프가 각자 자신들의 영토확장을 위해 싸우는 것이 스토리의 큰 흐름 입니다. 주인공은 랜덤으로 각종족 의 고아로 태어나 성장합니다"
                "주인공은 현재 초라하고 매우 약한 상태에서 시작합니다. 레벨업은 적을 죽일일때 얻는 경험치가 충족되면 합니다."
                "절대로 플레이어를 과도하게 띄워주거나 쉽게 이기게 만들지 말고, 밸런스를 엄격하게 유지하세요. "
                "예상치 못한 불행, 자원 부족, 위기 상황이 가끔 찾아오며, 때로는 극적인 행운이 찾아옵니다. "
                "직업은 전사, 마법사, 성직자, 궁수, 도적 중에서 선택할 수 있으며 각 직업별로 전문적인 스킬을 배우고 발전시킬 수 있습니다.\n"
                "매 프롬프트마다 전송되는 [현재 내 상태 정보]를 최우선 기준으로 삼아 스토리를 전개하고, 몬스터와 조우하여 "
                "**전투가 벌어지면**, 답변 본문 마지막 줄에 단독으로 "
                '[START_COMBAT: {"name": "초급 몬스터이름", "hp": 30, "atk": 8}] 형식의 JSON을 출력하여 자동 전투를 가동시키세요.\n'
                "주의사항: 답변 본문에는 [상태: ...] 같은 텍스트 상태창을 절대 출력하지 마십시오. "
                "스탯 변동이 발생할 경우 반드시 답변 맨 마지막 줄에 단독으로 "
                '[JSON_UPDATE: {"hp": 숫자, "max_hp": 숫자, "mp": 숫자, "max_mp": 숫자, "gold": 숫자, "level": 숫자, "equipment": {"무기": "...", "갑옷": "..."}, "inventory": ["..."], "skills": ["..."]}] '
                "형식의 JSON 데이터를 남겨주세요.\n"
                "또한, 플레이어가 고를 수 있는 2~5가지 선택지를 항상 생성하여 답변 맨 마지막 줄에 단독으로 "
                '[CHOICES: ["선택지1 내용", "선택지2 내용", "선택지3 내용"]] 형식으로 반드시 출력하세요.'
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
                st.session_state.chat_session = (
                    st.session_state.client.chats.create(
                        model=selected_model,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.8,
                        ),
                    )
                )
                with st.spinner(
                    f"[{selected_model}] 모델로 새로운 게임 세계를 생성하는"
                    " 중입니다..."
                ):
                    initial_prompt = (
                        "눈을 떠보니 음산한 기운이 감도는 고대 던전의 지하"
                        " 감옥입니다. 몸은 쇠약하고 쥐새끼가 울부짖는 최악의"
                        " 환경입니다. 먼저 플레이어에게 어떤 직업(전사, 마법사,"
                        " 성직자, 궁수, 도적 중 택1)을 선택할 것인지 묻고,"
                        " 앞으로 펼쳐질 고난도 생존 모험의 서막을 열어주세요."
                    )
                    try:
                        response = st.session_state.chat_session.send_message(
                            initial_prompt
                        )
                        bot_response = response.text
                    except Exception as e:
                        bot_response = (
                            f"세계 생성 중 API 에러가 발생했습니다. (선택"
                            f" 모델: {selected_model})\n에러: {e}"
                        )

                    st.session_state.messages = [{
                        "role": "assistant",
                        "content": (
                            f"🏰 **[생존 모험이 시작되었습니다"
                            f" ({selected_model})]**\n\n{bot_response}"
                        ),
                    }]

                    with open(SAVE_FILE, "w", encoding="utf-8") as f:
                        json.dump(
                            st.session_state.messages, f, ensure_ascii=False
                        )
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
                                role=r,
                                parts=[types.Part.from_text(text=msg["content"])],
                            )
                        )

                st.session_state.chat_session = (
                    st.session_state.client.chats.create(
                        model=selected_model,
                        history=api_history if api_history else None,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.8,
                        ),
                    )
                )

        # 📖 [채팅 히스토리 렌더링]
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    clean_content = clean_tags(message["content"])
                    st.markdown(clean_content)
                else:
                    st.markdown(message["content"])

        # 🎯 [최신 선택지 태그 추출 및 버튼 인터페이스 생성]
        current_choices = []
        if st.session_state.messages:
            last_message = st.session_state.messages[-1]
            if last_message["role"] == "assistant":
                choices_match = re.search(
                    r"\[CHOICES:\s*(\[.*?\])\s*\]",
                    last_message["content"],
                    re.DOTALL,
                )
                if choices_match:
                    try:
                        current_choices = json.loads(choices_match.group(1))
                    except Exception:
                        current_choices = []

        selected_button_prompt = None
        if current_choices:
            st.markdown("##### 🎯 행동 선택 (버튼을 터치하세요)")
            for idx, choice in enumerate(current_choices):
                if st.button(
                    f"👉 {choice}",
                    key=f"btn_{len(st.session_state.messages)}_{idx}",
                    use_container_width=True,
                ):
                    selected_button_prompt = choice

        # 💬 [사용자 입력 처리 - 버튼 선택 또는 직접 입력]
        chat_input_prompt = st.chat_input("또는 행동을 직접 입력하세요...")
        user_prompt = selected_button_prompt or chat_input_prompt

        if user_prompt:
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
                            f"[현재 내 상태 정보 - HP:"
                            f" {current_stats['hp']}/{current_stats['max_hp']},"
                            f" MP: {current_stats['mp']}/{current_stats['max_mp']},"
                            f" 골드: {current_stats['gold']}G, 레벨:"
                            f" {current_stats['level']}, 인벤토리:"
                            f" {json.dumps(current_stats['inventory'], ensure_ascii=False)}]\n플레이어"
                            f" 행동: {user_prompt}"
                        )

                        response = st.session_state.chat_session.send_message(
                            augmented_prompt
                        )
                        bot_response = response.text

                        final_output = bot_response
                        combat_occurred = False

                        # 1. 전투 시작 트리거 감지 ([START_COMBAT])
                        combat_match = re.search(
                            r"\[START_COMBAT:\s*(\{.*?\})\s*\]",
                            bot_response,
                            re.DOTALL,
                        )
                        if combat_match:
                            try:
                                combat_data = json.loads(combat_match.group(1))
                                combat_log_text, victory, reward_gold = (
                                    run_automatic_combat(combat_data)
                                )
                                combat_occurred = True

                                base_story = clean_tags(bot_response)

                                updated_stats = st.session_state.stats
                                post_prompt = (
                                    f"전투가 종료되었습니다. (결과:"
                                    f" {'승리' if victory else '패배'}, 보상"
                                    f" 골드: {reward_gold}). [현재 내 실제"
                                    f" 상태 정보 - HP:"
                                    f" {updated_stats['hp']}/{updated_stats['max_hp']},"
                                    f" MP:"
                                    f" {updated_stats['mp']}/{updated_stats['max_mp']},"
                                    f" 골드: {updated_stats['gold']}G,"
                                    " 인벤토리:"
                                    f" {json.dumps(updated_stats['inventory'], ensure_ascii=False)}]."
                                    " 이 직후의 현장 상황을 생생하게"
                                    " 묘사하세요."
                                )
                                post_response = (
                                    st.session_state.chat_session.send_message(
                                        post_prompt
                                    )
                                )
                                post_text_clean = clean_tags(post_response.text)

                                authoritative_json = json.dumps(
                                    {
                                        "hp": updated_stats["hp"],
                                        "max_hp": updated_stats["max_hp"],
                                        "mp": updated_stats["mp"],
                                        "max_mp": updated_stats["max_mp"],
                                        "gold": updated_stats["gold"],
                                        "level": updated_stats["level"],
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
                                    else '[CHOICES: ["다음 구역 탐색", "휴식 취하기"]]'
                                )

                                final_output = (
                                    f"{base_story}\n\n---\n{combat_log_text}\n---\n\n{post_text_clean}\n\n[JSON_UPDATE:"
                                    f" {authoritative_json}]\n{post_choices_str}"
                                )
                            except Exception as e:
                                final_output += (
                                    f"\n\n(자동 전투 처리 중 오류 발생: {e})"
                                )

                        # 2. 스탯 업데이트 감지 ([JSON_UPDATE])
                        matches = re.findall(
                            r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]",
                            final_output,
                            re.DOTALL,
                        )
                        stats_updated = False
                        if matches:
                            try:
                                updated_data = json.loads(matches[-1])
                                for k, v in updated_data.items():
                                    if k in st.session_state.stats:
                                        if st.session_state.stats[k] != v:
                                            st.session_state.stats[k] = v
                                            stats_updated = True
                            except Exception:
                                pass

                        clean_output = clean_tags(final_output)
                        st.markdown(clean_output)

                        st.session_state.messages.append(
                            {"role": "assistant", "content": final_output}
                        )

                        with open(SAVE_FILE, "w", encoding="utf-8") as f:
                            json.dump(
                                st.session_state.messages,
                                f,
                                ensure_ascii=False,
                            )

                        st.rerun()

                    except Exception as e:
                        error_str = str(e)
                        if (
                            "429" in error_str
                            or "RESOURCE_EXHAUSTED" in error_str
                        ):
                            warning_msg = (
                                "⚠️ **[API 사용량 한도 초과]** 무료 티어 요청"
                                f" 제한에 도달했습니다. (모델: {selected_model})\n잠시"
                                " 후 다시 시도해 주세요!"
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
            "❌ 초기화 중 오류가 발생했습니다. API 키를 확인해 주세요."
            f" (상세 에러: {e})"
        )
