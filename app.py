import json
import os
import random
import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI
from pydantic import BaseModel, Field

SAVE_FILE = "progressive_rpg_save.json"

st.set_page_config(page_title="점진적 성장 추리 RPG", page_icon="📈", layout="wide")
st.markdown("상점은 초보자용 장비만 판매합니다. 필드 사냥의 한계를 극복하려면 **AI가 동적으로 생성하는 추리 퀘스트**를 해결하여 능력치와 장비를 단계적으로 성장시켜야 합니다!")

# 📋 [AI 동적 퀘스트 생성 스키마]
class DynamicDeductionQuest(BaseModel):
    title: str = Field(description="추리 퀘스트의 흥미로운 제목")
    description: str = Field(description="마법서 도난, 길드장 암살, 밀수 등 플레이어가 추리해야 할 사건 개요")
    npc_1_name: str = Field(description="첫 번째 NPC 이름 (예: 사서 벤)")
    npc_1_dialogue: str = Field(description="첫 번째 NPC의 초기 진술 (정직하거나 거짓)")
    npc_1_is_liar: bool = Field(description="첫 번째 NPC의 거짓말쟁이 여부 (True/False)")
    npc_1_clue: str = Field(description="이 NPC를 통해 얻는 단서 또는 모순점")
    
    npc_2_name: str = Field(description="두 번째 NPC 이름 (예: 부회장 로이)")
    npc_2_dialogue: str = Field(description="두 번째 NPC의 초기 진술")
    npc_2_is_liar: bool = Field(description="두 번째 NPC의 거짓말쟁이 여부")
    npc_2_clue: str = Field(description="이 NPC를 통해 얻는 단서 또는 모순점")
    
    correct_culprit: str = Field(description="진범의 이름 (npc_1_name 또는 npc_2_name 중 하나)")
    reward_stat_name: str = Field(description="상승시킬 능력치 종류 (예: '힘', '민첩', '지능', '체력스탯')")
    reward_stat_boost: int = Field(description="능력치 상승량 (밸런스 유지를 위해 5 또는 10으로 설정)")
    reward_gear: str = Field(description="점진적으로 좋아진 무기 또는 방어구 이름")
    reward_skill: str = Field(description="보상으로 획득하는 신규 마법 또는 기술")


# 💾 [세션 초기화]
if "level" not in st.session_state:
    st.session_state.level = 1
    st.session_state.exp = 0
    st.session_state.max_exp = 100
    st.session_state.hp = 100
    st.session_state.max_hp = 100
    st.session_state.mp = 30
    st.session_state.stats = {"힘": 10, "체력스탯": 10, "지능": 10, "민첩": 10}
    st.session_state.gold = 50
    st.session_state.gear = "낡은 단검 / 누더기 옷"
    st.session_state.skills = ["기본 공격", "탐색"]
    st.session_state.active_quest = None
    st.session_state.quest_history = []


# ⚙️ [사이드바 설정]
st.sidebar.header("🤖 AI 및 API 설정")
ai_provider = st.sidebar.selectbox("AI 제공자", ["Google Gemini", "Groq"])
api_key = st.sidebar.text_input(f"{ai_provider} API 키", type="password")
selected_model = st.sidebar.text_input("모델명 입력", value="gemini-2.5-flash" if ai_provider=="Google Gemini" else "llama-3.1-8b-instant")


# 🤖 [AI 퀘스트 생성 함수]
def generate_ai_quest(player_level, stats):
    system_instruction = (
        "당신은 단계별 성장형 추리 RPG의 게임 마스터입니다.\n"
        "플레이어의 현재 레벨과 능력치에 맞춰, 너무 과하지 않게 점진적인 성장을 보상으로 주는 추리 퀘스트를 1개 생성하세요.\n"
        "보상 능력치 상승량(reward_stat_boost)은 반드시 5 또는 10으로 제한하여 게임 밸런스가 급격히 깨지지 않도록 하세요."
    )
    prompt = f"현재 플레이어 레벨: {player_level}, 능력치: {stats}. 새로운 추리 퀘스트를 생성해주세요."

    if ai_provider == "Google Gemini":
        try:
            client = genai.Client(api_key=api_key)
            res = client.models.generate_content(
                model=selected_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=DynamicDeductionQuest,
                    temperature=0.7,
                ),
            )
            return json.loads(res.text)
        except Exception as e:
            st.error(f"Gemini API 오류: {e}")
            return None
    else:
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            res = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_instruction + "\n반드시 JSON 형식으로만 응답하세요."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e:
            st.error(f"Groq API 오류: {e}")
            return None


# 📱 [메인 레이아웃 탭]
tab1, tab2, tab3 = st.tabs(["⚔️ 캐릭터 및 필드 사냥", "🔍 AI 추리 퀘스트 수행", "🪙 초보자 상점"])

with tab1:
    st.subheader("🛡️ 플레이어 상태")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("레벨", f"Lv. {st.session_state.level}", f"EXP: {st.session_state.exp}/{st.session_state.max_exp}")
        st.metric("체력(HP)", f"{st.session_state.hp} / {st.session_state.max_hp}")
    with c2:
        st.metric("골드", f"🪙 {st.session_state.gold}G")
        st.metric("장착 장비", st.session_state.gear)
    with c3:
        st.write("**능력치 스탯**")
        for k, v in st.session_state.stats.items():
            st.text(f"- {k}: {v}")
    
    st.markdown(f"**보유 기술 및 마법:** {', '.join(st.session_state.skills)}")

    st.markdown("---")
    st.subheader("🌲 필드 사냥터 (난이도 벽 시스템)")
    st.markdown("사냥을 통해 경험치를 얻을 수 있지만, 레벨과 장비가 부족하면 강한 몬스터에게 패배합니다. **상위 사냥터로 가려면 반드시 추리 퀘스트로 장비와 스탯을 올려야 합니다!**")

    # 사냥 난이도 계산 (스탯과 장비 기반)
    power_score = sum(st.session_state.stats.values()) + (st.session_state.level * 10)
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown("#### 🟢 초급 사냥터 (슬라임, 고블린)")
        if st.button("사냥하기 (권장 전투력: 40 이상)", use_container_width=True):
            st.session_state.exp += 30
            st.session_state.gold += 15
            st.success("사냥 성공! 경험치 +30, 골드 +15G 획득")
            if st.session_state.exp >= st.session_state.max_exp:
                st.session_state.level += 1
                st.session_state.exp = 0
                st.session_state.max_exp = int(st.session_state.max_exp * 1.5)
                st.balloons()
                st.success(f"🎉 레벨 업! 현재 Lv. {st.session_state.level}")
            st.rerun()

    with col_h2:
        st.markdown("#### 🔴 중급 사냥터 (오크 워리어, 정예 마물)")
        st.markdown("*주의: 추리 퀘스트를 통해 장비와 스탯(+10 이상)을 충분히 올리지 않으면 사냥할 수 없습니다!*")
        if st.button("중급 사냥 도전하기 (요구 전투력: 70 이상)", use_container_width=True):
            if power_score >= 70:
                st.session_state.exp += 70
                st.session_state.gold += 40
                st.success("중급 사냥 승리! 대량의 경험치와 골드를 획득했습니다.")
                if st.session_state.exp >= st.session_state.max_exp:
                    st.session_state.level += 1
                    st.session_state.exp = 0
                    st.session_state.max_exp = int(st.session_state.max_exp * 1.5)
                    st.balloons()
                st.rerun()
            else:
                st.error("❌ 전투력이 부족하여 사냥에 실패했습니다! '추리 퀘스트'를 통해 장비와 스탯을 먼저 업그레이드하세요.")

with tab2:
    st.subheader("🕵️ AI 동적 추리 퀘스트 보드")
    st.markdown("퀘스트를 통해 능력치가 **단계적으로 상승(+5 또는 +10)**하며, 상점에서 살 수 없는 강력한 무기와 스킬을 획득합니다.")

    if not api_key:
        st.warning("⚠️ 사이드바에 API 키를 입력해주세요.")
    else:
        if st.session_state.active_quest is None:
            if st.button("✨ 새로운 추리 사건 의뢰받기", use_container_width=True):
                with st.spinner("AI가 새로운 미스터리 사건과 점진적 보상을 생성하는 중..."):
                    q_data = generate_ai_quest(st.session_state.level, st.session_state.stats)
                    if q_data:
                        q_data["collected_clues"] = []
                        q_data["status"] = "진행중"
                        q_data["npc_1_fav"] = 10
                        q_data["npc_2_fav"] = 10
                        st.session_state.active_quest = q_data
                        st.rerun()
        
        if st.session_state.active_quest:
            q = st.session_state.active_quest
            st.info(f"📌 **현재 사건:** {q['title']}")
            st.write(f"**사건 개요:** {q['description']}")
            st.markdown("---")
            
            # NPC 1 심문
            c_n1, c_n2 = st.columns(2)
            with c_n1:
                st.write(f"**👤 {q['npc_1_name']}** (호감도: {q['npc_1_fav']})")
                st.write(f"진술: *\"{q['npc_1_dialogue']}\"*")
                if st.button(f"{q['npc_1_name']} 대화/심문", key="talk_1"):
                    q['npc_1_fav'] += 20
                    if q['npc_1_is_liar'] and q['npc_1_fav'] < 40:
                        st.warning(f"{q['npc_1_name']}: 경계하며 진실을 숨기고 있습니다.")
                    else:
                        if q['npc_1_clue'] not in q['collected_clues']:
                            q['collected_clues'].append(q['npc_1_clue'])
                        st.success(f"💡 단서 획득: {q['npc_1_clue']}")

            # NPC 2 심문
            with c_n2:
                st.write(f"**👤 {q['npc_2_name']}** (호감도: {q['npc_2_fav']})")
                st.write(f"진술: *\"{q['npc_2_dialogue']}\"*")
                if st.button(f"{q['npc_2_name']} 대화/심문", key="talk_2"):
                    q['npc_2_fav'] += 20
                    if q['npc_2_is_liar'] and q['npc_2_fav'] < 40:
                        st.warning(f"{q['npc_2_name']}: 입을 굳게 다물고 있습니다.")
                    else:
                        if q['npc_2_clue'] not in q['collected_clues']:
                            q['collected_clues'].append(q['npc_2_clue'])
                        st.success(f"💡 단서 획득: {q['npc_2_clue']}")

            st.markdown("---")
            st.markdown("#### 🔎 수집된 단서 노트")
            if q['collected_clues']:
                for clue in q['collected_clues']:
                    st.text(f"- {clue}")
            else:
                st.text("수집된 단서가 없습니다. NPC를 심문하세요.")

            st.markdown("---")
            st.markdown("#### ⚖️ 범인 지목 및 보상 획득")
            suspects = [q['npc_1_name'], q['npc_2_name']]
            chosen = st.selectbox("진범으로 의심되는 인물을 선택하세요", suspects)
            
            if st.button("🚨 이 사람을 범인으로 고발한다!", use_container_width=True):
                if chosen == q['correct_culprit']:
                    st.balloons()
                    st.success(f"🎯 정답입니다! 진범 {chosen}을(를) 검거했습니다.")
                    
                    # 점진적 스탯 상승 및 보상 적용
                    stat_name = q['reward_stat_name']
                    boost = q['reward_stat_boost']
                    if stat_name in st.session_state.stats:
                        st.session_state.stats[stat_name] += boost
                    else:
                        st.session_state.stats["힘"] += boost # 기본값
                        
                    st.session_state.gear = q['reward_gear']
                    if q['reward_skill'] not in st.session_state.skills:
                        st.session_state.skills.append(q['reward_skill'])
                        
                    st.info(f"✨ [성장 보상] {stat_name} +{boost} 상승! | 장비 갱신: {q['reward_gear']} | 신규 기술: {q['reward_skill']}")
                    
                    # 퀘스트 초기화
                    st.session_state.active_quest = None
                    st.rerun()
                else:
                    st.error("❌ 틀렸습니다! 무고한 사람을 지목했거나 증거가 부족합니다.")

with tab3:
    st.info("💡 상점에서는 오직 기초 소모품과 최하급 장비만 판매합니다. 본격적인 능력치와 상위 장비는 반드시 **추리 퀘스트**를 통해서만 얻을 수 있습니다.")
    st.subheader("🪙 초보자 상점")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.write("**체력 포션 (소)** - 가격: 10G")
        if st.button("포션 구매"):
            if st.session_state.gold >= 10:
                st.session_state.gold -= 10
                st.success("포션 구매 완료!")
            else:
                st.error("골드가 부족합니다!")
    with col_s2:
        st.write("**초보자용 가죽 모자** - 가격: 30G")
        if st.button("모자 구매"):
            if st.session_state.gold >= 30:
                st.session_state.gold -= 30
                st.success("모자 구매 완료!")
            else:
                st.error("골드가 부족합니다!")
