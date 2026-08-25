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

# 📊 [캐릭터 종합 스탯 초기화]
if "stats" not in st.session_state:
    st.session_state.stats = {
        "hp": 60,
        "max_hp": 60,
        "mp": 30,
        "max_mp": 30,
        "gold": 50,
        "level": 1,
        "reputation": {"인간": 0, "엘프": 0, "드워프": 0, "오크": 0},
        "equipment": {"무기": "낡은 철검", "갑옷": "여행자 가죽옷", "장신구": "없음"},
        "inventory": ["체력 포션 (소)", "체력 포션 (소)", "건포도 빵"],
        "skills": ["기본 베기"],
    }

# ⚙️ [좌측 사이드바: 게임 설정 및 모델 선택]
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

            // 1. Element.prototype.scrollIntoView 완전 차단
            if (pWin.Element && !pWin.Element.prototype._scrollBlocker) {{
                pWin.Element.prototype._scrollBlocker = true;
                pWin.Element.prototype.scrollIntoView = function() {{}};
            }}

            // 2. 메인 컨테이너 스크롤 위치 저장 및 복원
            function initScrollLock() {{
                const mainEl = pDoc.querySelector('.main') || pDoc.documentElement;
                if (!mainEl) return;

                if (pWin._savedScrollPos === undefined) {{
                    pWin._savedScrollPos = mainEl.scrollTop;
                }}

                // 수동 스크롤 시 위치 감지 및 저장
                mainEl.addEventListener('scroll', function() {{
                    pWin._savedScrollPos = mainEl.scrollTop;
                }}, {{ passive: true }});

                const restorePos = function() {{
                    if (pWin._savedScrollPos !== undefined && Math.abs(mainEl.scrollTop - pWin._savedScrollPos) > 10) {{
                        mainEl.scrollTop = pWin._savedScrollPos;
                    }}
                }};

                // DOM 변경 감지(답변 생성 및 rerun 시 원래 위치로 고정)
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

# 모델 목록 설정
default_models = [
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
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
    "Gemini 모델 선택",
    options=available_models,
    index=default_index,
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 캐릭터 상태창")

stats = st.session_state.stats
st.sidebar.metric(label="❤️ 체력 (HP)", value=f"{stats['hp']} / {stats['max_hp']}")
st.sidebar.metric(label="💙 마나 (MP)", value=f"{stats['mp']} / {stats['max_mp']}")
st.sidebar.metric(label="💰 보유 골드", value=f"{stats['gold']} G")
st.sidebar.metric(label="⭐ 레벨", value=f"Lv. {stats['level']}")

st.sidebar.markdown("##### 🤝 종족별 평판")
if "reputation" in stats:
    for race, rep in stats["reputation"].items():
        st.sidebar.write(f"- **{race}**: {rep}")

st.sidebar.markdown("##### 🎒 인벤토리")
st.sidebar.write(f"{', '.join(stats['inventory']) if stats['inventory'] else '없음'}")

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


# ⚔️ [자동 전투 시뮬레이션 함수]
def run_automatic_combat(enemy_data):
    player = st.session_state.stats
    enemy = {
        "name": enemy_data.get("name", "적 정찰병"),
        "hp": enemy_data.get("hp", 40),
        "max_hp": enemy_data.get("hp", 40),
        "atk": enemy_data.get("atk", 10),
    }
    combat_logs = [f"🚨 **[교전 발생]** 적 세력 **{enemy['name']}**(HP: {enemy['hp']})과 전투가 시작되었습니다!"]

    turn = 1
    while enemy["hp"] > 0 and player["hp"] > 0 and turn <= 12:
        combat_logs.append(f"\n--- [전투 턴 {turn}] ---")

        if player["hp"] < (player["max_hp"] * 0.4) and "체력 포션 (소)" in player["inventory"]:
            player["inventory"].remove("체력 포션 (소)")
            heal = 30
            player["hp"] = min(player["max_hp"], player["hp"] + heal)
            combat_logs.append(f"🧪 포션을 마셔 HP가 {heal} 회복되었습니다! (현재 HP: {player['hp']}/{player['max_hp']})")
        elif player["mp"] >= 8 and player["skills"]:
            player["mp"] -= 8
            dmg = random.randint(20, 32)
            enemy["hp"] = max(0, enemy["hp"] - dmg)
            combat_logs.append(f"✨ 기술 발동! **{enemy['name']}**에게 {dmg}의 피해를 입혔습니다. (적 남은 HP: {enemy['hp']}/{enemy['max_hp']})")
        else:
            dmg = random.randint(8, 16)
            enemy["hp"] = max(0, enemy["hp"] - dmg)
            combat_logs.append(f"⚔️ 기본 공격! **{enemy['name']}**에게 {dmg}의 피해를 입혔습니다. (적 남은 HP: {enemy['hp']}/{enemy['max_hp']})")

        if enemy["hp"] <= 0:
            break

        enemy_dmg = random.randint(max(2, enemy["atk"] - 2), enemy["atk"] + 4)
        player["hp"] = max(0, player["hp"] - enemy_dmg)
        combat_logs.append(f"💥 **{enemy['name']}**의 반격! {enemy_dmg}의 피해를 입었습니다. (내 남은 HP: {player['hp']}/{player['max_hp']})")

        turn += 1

    result_text = "\n".join(combat_logs)
    if enemy["hp"] <= 0:
        reward_gold = random.randint(15, 35)
        player["gold"] += reward_gold
        result_text += f"\n\n🎉 **[전투 승리!]** 적을 제압하고 {reward_gold} 골드를 전리품으로 획득했습니다."
        return result_text, True, reward_gold
    else:
        player["hp"] = max(10, player["max_hp"] // 4)
        result_text += "\n\n💀 **[전투 패배]** 적에게 부상을 입고 후퇴했습니다. 인근 마을 여관으로 간신히 후송되었습니다."
        return result_text, False, 0


# 🖥️ [채팅 인터페이스 처리]
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
                "당신은 4대 종족(인간 제국, 엘프 고대숲 연합, 드워프 산악요새, 오크 부족연맹)이 대륙의 영토 확장을 두고 "
                "대규모 패권 전쟁을 벌이는 '에델가르드 대륙'의 게임 마스터(GM)입니다.\n"
                "주인공은 단순한 던전 소탕에만 매몰되지 않으며, 마을과 영지를 방문하고, 여관에서 휴식을 취하거나, 정세 소식을 듣고, "
                "무역/퀘스트/외교/국경 분쟁에 개입하며 착실히 세력과 명성을 키워나가는 대서사시의 주인공입니다.\n"
                "스토리 진행 지침:\n"
                "1. 플레이어가 전투만 하지 않도록 영지 방문, 여관 휴식(골드로 HP/MP 회복), 상점 거래, 영지 정찰, 외교 접선 등 다채로운 선택지를 제시하세요.\n"
                "2. 몬스터나 적대 종족과 교전이 발생할 때만 답변 본문 마지막 줄에 "
                '[START_COMBAT: {"name": "적 이름", "hp": 40, "atk": 10}] '
                "태그를 출력하세요.\n"
                "3. 스탯, 골드, 인벤토리, 평판 변동 발생 시 답변 맨 마지막 줄에 단독으로 "
                '[JSON_UPDATE: {"hp": 숫자, "max_hp": 숫자, "mp": 숫자, "max_mp": 숫자, "gold": 숫자, "level": 숫자, "reputation": {"인간": 숫자, "엘프": 숫자, "드워프": 숫자, "오크": 숫자}, "equipment": {...}, "inventory": [...], "skills": [...]}] '
                "태그를 남기세요.\n"
                "4. 플레이어가 선택할 수 있는 행동 옵션을 항상 2~5가지 생성하여 맨 마지막 줄에 단독으로 "
                '[CHOICES: ["선택지1", "선택지2", "선택지3"]] 태그로 출력하세요.'
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
                        temperature=0.85,
                    ),
                )
                with st.spinner("에델가르드 대륙의 정세와 교차로 마을 서막을 생성 중입니다..."):
                    initial_prompt = (
                        "에델가르드 대륙은 현재 인간 제국, 엘프 연합, 드워프 요새, 오크 연맹의 영토 확장 전쟁으로 솟구치고 있습니다. "
                        "플레이어는 4대 종족의 세력이 교차하는 국경의 중립 도시 '크로스로드'의 여관에서 눈을 떴습니다. "
                        "현재 대륙 정세와 주인공의 신분(방랑 용병, 몰락 기사, 학자 등 선택 유도)을 설명하고, "
                        "마을에서 취할 수 있는 다양한 행동(여관 휴식, 영주 길드 방문, 상점 들르기, 소문 듣기 등) 선택지 4가지를 제시해 주세요."
                    )
                    try:
                        response = st.session_state.chat_session.send_message(initial_prompt)
                        bot_response = response.text
                    except Exception as e:
                        bot_response = f"세계 생성 중 오류가 발생했습니다: {e}"

                    st.session_state.messages = [{
                        "role": "assistant",
                        "content": f"🌍 **[에델가르드 패권전 서막]**\n\n{bot_response}",
                    }]

                    with open(SAVE_FILE, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.messages, f, ensure_ascii=False)
            else:
                api_history = []
                for msg in st.session_state.messages:
                    r = "model" if msg["role"] == "assistant" else ("user" if msg["role"] == "user" else None)
                    if r:
                        api_history.append(
                            types.Content(role=r, parts=[types.Part.from_text(text=msg["content"])])
                        )

                st.session_state.chat_session = st.session_state.client.chats.create(
                    model=selected_model,
                    history=api_history if api_history else None,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.85,
                    ),
                )

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
                choices_match = re.search(r"\[CHOICES:\s*(\[.*?\])\s*\]", last_msg["content"], re.DOTALL)
                if choices_match:
                    try:
                        current_choices = json.loads(choices_match.group(1))
                    except Exception:
                        current_choices = []

        selected_button_prompt = None
        if current_choices:
            st.markdown("##### 🎯 행동 선택 (원하는 선택지를 클릭하세요)")
            for idx, choice in enumerate(current_choices):
                if st.button(f"👉 {choice}", key=f"btn_{len(st.session_state.messages)}_{idx}", use_container_width=True):
                    selected_button_prompt = choice

        chat_input_prompt = st.chat_input("또는 직접 행동을 작성하세요...")
        user_prompt = selected_button_prompt or chat_input_prompt

        # 💬 [사용자 프롬프트 전송 및 처리]
        if user_prompt:
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                with st.spinner("게임 마스터가 정세를 계산 중입니다..."):
                    try:
                        cur_stats = st.session_state.stats
                        augmented_prompt = (
                            f"[현재 상태 - HP: {cur_stats['hp']}/{cur_stats['max_hp']}, "
                            f"MP: {cur_stats['mp']}/{cur_stats['max_mp']}, 골드: {cur_stats['gold']}G, "
                            f"레벨: {cur_stats['level']}, 평판: {json.dumps(cur_stats.get('reputation', {}), ensure_ascii=False)}, "
                            f"인벤토리: {json.dumps(cur_stats['inventory'], ensure_ascii=False)}]\n"
                            f"플레이어 행동: {user_prompt}"
                        )

                        response = st.session_state.chat_session.send_message(augmented_prompt)
                        bot_response = response.text
                        final_output = bot_response

                        # 1. 전투 발생 체크
                        combat_match = re.search(r"\[START_COMBAT:\s*(\{.*?\})\s*\]", bot_response, re.DOTALL)
                        if combat_match:
                            try:
                                combat_data = json.loads(combat_match.group(1))
                                combat_log_text, victory, reward_gold = run_automatic_combat(combat_data)

                                base_story = clean_tags(bot_response)
                                updated_stats = st.session_state.stats

                                post_prompt = (
                                    f"전투 결과: {'승리' if victory else '패배'}, 보상 골드: {reward_gold}G. "
                                    f"[현재 실제 상태 - HP: {updated_stats['hp']}/{updated_stats['max_hp']}, 골드: {updated_stats['gold']}G]. "
                                    "전투 직후 현장 상황을 생생히 묘사하고, 휴식/이동/영지 방문 등 다음 행동 선택지를 제시해 주세요."
                                )
                                post_response = st.session_state.chat_session.send_message(post_prompt)
                                post_text_clean = clean_tags(post_response.text)

                                authoritative_json = json.dumps({
                                    "hp": updated_stats["hp"],
                                    "max_hp": updated_stats["max_hp"],
                                    "mp": updated_stats["mp"],
                                    "max_mp": updated_stats["max_mp"],
                                    "gold": updated_stats["gold"],
                                    "level": updated_stats["level"],
                                    "reputation": updated_stats.get("reputation", {}),
                                    "equipment": updated_stats["equipment"],
                                    "inventory": updated_stats["inventory"],
                                    "skills": updated_stats["skills"],
                                }, ensure_ascii=False)

                                post_choices_match = re.search(r"\[CHOICES:\s*(\[.*?\])\s*\]", post_response.text, re.DOTALL)
                                post_choices_str = post_choices_match.group(0) if post_choices_match else '[CHOICES: ["여관으로 가서 휴식", "마을 길드로 이동"]]'

                                final_output = f"{base_story}\n\n---\n{combat_log_text}\n---\n\n{post_text_clean}\n\n[JSON_UPDATE: {authoritative_json}]\n{post_choices_str}"
                            except Exception as e:
                                final_output += f"\n\n(전투 처리 중 오류: {e})"

                        # 2. 스탯 반영
                        matches = re.findall(r"\[JSON_UPDATE:\s*(\{.*?\})\s*\]", final_output, re.DOTALL)
                        if matches:
                            try:
                                updated_data = json.loads(matches[-1])
                                for k, v in updated_data.items():
                                    if k in st.session_state.stats:
                                        st.session_state.stats[k] = v
                            except Exception:
                                pass

                        st.markdown(clean_tags(final_output))
                        st.session_state.messages.append({"role": "assistant", "content": final_output})

                        with open(SAVE_FILE, "w", encoding="utf-8") as f:
                            json.dump(st.session_state.messages, f, ensure_ascii=False)

                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ 오류가 발생했습니다: {e}")

    except Exception as e:
        st.error(f"❌ 초기화 오류: {e}")
