import json
import os
import random
import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI
from pydantic import BaseModel, Field

st.set_page_config(page_title="판타지 추리 RPG: 모험의 시작", page_icon="🗺️", layout="wide")

# 📋 [AI 동적 퀘스트 생성 스키마]
class DynamicDeductionQuest(BaseModel):
    title: str = Field(description="추리 퀘스트의 흥미로운 제목")
    description: str = Field(description="마법서 도난, 길드장 암살, 밀수 등 플레이어가 추리해야 할 사건 개요")
    npc_1_name: str = Field(description="첫 번째 NPC 이름 (예: 상인 밥)")
    npc_1_dialogue: str = Field(description="첫 번째 NPC의 초기 진술 (정직하거나 거짓)")
    npc_1_is_liar: bool = Field(description="첫 번째 NPC의 거짓말쟁이 여부 (True/False)")
    npc_1_clue: str = Field(description="이 NPC를 통해 얻는 단서 또는 모순점")
    
    npc_2_name: str = Field(description="두 번째 NPC 이름 (예: 경비병 톰)")
    npc_2_dialogue: str = Field(description="두 번째 NPC의 초기 진술")
    npc_2_is_liar: bool = Field(description="두 번째 NPC의 거짓말쟁이 여부")
    npc_2_clue: str = Field(description="이 NPC를 통해 얻는 단서 또는 모순점")
    
    correct_culprit: str = Field(description="진범의 이름 (npc_1_name 또는 npc_2_name 중 하나)")
    reward_stat_name: str = Field(description="상승시킬 능력치 종류 (예: '힘', '민첩', '지능', '체력스탯')")
    reward_stat_boost: int = Field(description="능력치 상승량 (밸런스 유지를 위해 5 또는 10으로 설정)")
    reward_gear: str = Field(description="점진적으로 좋아진 무기 또는 방어구 이름")
    reward_skill: str = Field(description="보상으로 획득하는 신규 마법 또는 기술")


# 💾 [세션 초기화]
if "location" not in st.session_state:
    st.session_state.location = "orphanage" # orphanage, town, hunting, quest_board, active_quest, shop

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

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 내 정보 요약")
st.sidebar.text(f"레벨: Lv.{st.session_state.level} (EXP: {st.session_state.exp}/{st.session_state.max_exp})")
st.sidebar.text(f"소지 골드: 🪙 {st.session_state.gold}G")
st.sidebar.text(f"장비: {st.session_state.gear}")


# 🤖 [AI 퀘스트 생성 함수]
def generate_ai_quest(player_level, stats):
    system_instruction = (
        "당신은 판타지 추리 RPG의 게임 마스터입니다.\n"
        "플레이어의 레벨과 능력치에 맞춰 마을에서 발생한 미스터리 사건을 1개 생성하세요.\n"
        "보상 능력치 상승량(reward_stat_boost)은 5 또는 10으로 제한하여 밸런스를 유지하세요."
    )
    prompt = f"현재 플레이어 레벨: {player_level}, 능력치: {stats}. 새로운 추리 사건을 생성해주세요."

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


# ==========================================
# 🗺️ 1. 고아원 오프닝 씬 (시작점)
# ==========================================
if st.session_state.location == "orphanage":
    st.title("🏡 가난한 고아원의 문 앞")
    st.markdown("---")
    st.write("당신은 오늘로 **18살**이 되었습니다. 오직 낡은 단검 하나와 누더기 옷을 걸친 채, 원장 수녀님의 따뜻한 배웅을 뒤로하고 드넓은 판타지 세계로 첫걸음을 내딛습니다.")
    st.write("세상은 냉혹합니다. 거친 야수가 도사리는 **사냥터**로 갈 수도 있고, 생필품을 파는 **마을**로 향할 수도 있습니다.")
    
    if st.button("🎒 배낭을 메고 판타지 마을 '루멘'으로 향한다!", use_container_width=True):
        st.session_state.location = "town"
        st.rerun()


# ==========================================
# 🏘️ 2. 판타지 마을 '루멘' (허브)
# ==========================================
elif st.session_state.location == "town":
    st.title("🏘️ 판타지 마을: 루멘 (Lumen)")
    st.markdown("모험가들이 거쳐 가는 평화롭고도 비밀이 많은 마을입니다. 이곳에서 장비를 정비하거나, 주민들과 대화하여 사건을 파악할 수 있습니다.")
    st.markdown("---")
    
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        if st.button("🪙 상점 방문하기", use_container_width=True):
            st.session_state.location = "shop"
            st.rerun()
    with col_t2:
        if st.button("🗣️ 마을 주민들과 대화 및 수사", use_container_width=True):
            st.session_state.location = "quest_board"
            st.rerun()
    with col_t3:
        if st.button("🌲 사냥터로 나가기", use_container_width=True):
            st.session_state.location = "hunting"
            st.rerun()
    with col_t4:
        if st.button("📜 내 상태 및 인벤토리", use_container_width=True):
            st.session_state.location = "status"
            st.rerun()

    st.markdown("---")
    st.info("💡 **마을 사람의 조언:** \"여기 상점에서는 낡은 포션이나 초보용 방패 같은 기본적인 것밖에 안 팔아. 정말 강해지고 싶다면 마을 광장에서 사람들과 대화하며 **사건(추리 퀘스트)**을 해결해 보게나! 진정한 힘은 거기서 얻을 수 있네.\'")


# ==========================================
# 🪙 3. 초보자 상점
# ==========================================
elif st.session_state.location == "shop":
    st.title("🪙 루멘 마을 초보자 상점")
    st.markdown("상점 주인: *\"어서 와라, 모험가 양반. 여기는 초보자용 기초 장비랑 포션만 판다네. 더 좋은 걸 찾으려면 마을에서 사건을 해결해봐!\"*")
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("**체력 포션 (소)** - 가격: 10G (효과: 체력 회복)")
        if st.button("포션 구매"):
            if st.session_state.gold >= 10:
                st.session_state.gold -= 10
                st.success("체력 포션 구매 완료!")
            else:
                st.error("골드가 부족합니다!")
    with c2:
        st.write("**초보자용 가죽 모자** - 가격: 30G (효과: 기본 방어)")
        if st.button("모자 구매"):
            if st.session_state.gold >= 30:
                st.session_state.gold -= 30
                st.success("모자 구매 완료!")
            else:
                st.error("골드가 부족합니다!")
                
    st.markdown("---")
    if st.button("🏠 마을 광장으로 돌아가기"):
        st.session_state.location = "town"
        st.rerun()


# ==========================================
# 📜 4. 내 상태 및 정보 확인
# ==========================================
elif st.session_state.location == "status":
    st.title("📜 모험가 정보 노트")
    st.markdown("---")
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.metric("레벨", f"Lv. {st.session_state.level}", f"EXP: {st.session_state.exp}/{st.session_state.max_exp}")
        st.metric("체력(HP)", f"{st.session_state.hp} / {st.session_state.max_hp}")
        st.metric("소지 골드", f"🪙 {st.session_state.gold}G")
        st.write(f"**현재 장착 장비:** {st.session_state.gear}")
    with c_s2:
        st.write("**능력치 스탯**")
        for k, v in st.session_state.stats.items():
            st.text(f"- {k}: {v}")
        st.markdown(f"**보유 기술 및 마법:** {', '.join(st.session_state.skills)}")

    st.markdown("---")
    if st.button("🏠 마을 광장으로 돌아가기"):
        st.session_state.location = "town"
        st.rerun()


# ==========================================
# 🗣️ 5. 마을 광장 & 추리 퀘스트 수주/진행
# ==========================================
elif st.session_state.location == "quest_board":
    st.title("🗣️ 마을 광장: 주민 대화 및 의뢰 게시판")
    st.markdown("주민들과 대화를 나누어 마을에 숨겨진 미스터리 사건을 파헤치고, 상점에서는 절대 구할 수 없는 강력한 장비와 마법을 획득하세요!")
    st.markdown("---")

    if not api_key:
        st.warning("⚠️ 사이드바에 AI API 키를 먼저 입력해주세요.")
        if st.button("🏠 마을 광장으로"):
            st.session_state.location = "town"
            st.rerun()
    else:
        if st.session_state.active_quest is None:
            if st.button("✨ 새로운 사건 의뢰받기 (마을 주민들과 대화 시작)", use_container_width=True):
                with st.spinner("AI가 새로운 미스터리 사건을 설계하는 중..."):
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
            st.info(f"📌 **현재 수사 중인 사건:** {q['title']}")
            st.write(f"**사건 개요:** {q['description']}")
            st.markdown("---")
            
            # NPC 1 심문
            c_n1, c_n2 = st.columns(2)
            with c_n1:
                st.write(f"**👤 {q['npc_1_name']}** (호감도: {q['npc_1_fav']})")
                st.write(f"진술: *\"{q['npc_1_dialogue']}\"*")
                if st.button(f"{q['npc_1_name']}에게 다가간다", key="talk_1"):
                    q['npc_1_fav'] += 20
                    if q['npc_1_is_liar'] and q['npc_1_fav'] < 40:
                        st.warning(f"{q['npc_1_name']}: \"왜 자꾸 저를 의심하시죠? 억울합니다!\" (호감도가 부족해 진실을 숨깁니다)")
                    else:
                        if q['npc_1_clue'] not in q['collected_clues']:
                            q['collected_clues'].append(q['npc_1_clue'])
                        st.success(f"💡 단서 획득: {q['npc_1_clue']}")

            # NPC 2 심문
            with c_n2:
                st.write(f"**👤 {q['npc_2_name']}** (호감도: {q['npc_2_fav']})")
                st.write(f"진술: *\"{q['npc_2_dialogue']}\"*")
                if st.button(f"{q['npc_2_name']}에게 다가간다", key="talk_2"):
                    q['npc_2_fav'] += 20
                    if q['npc_2_is_liar'] and q['npc_2_fav'] < 40:
                        st.warning(f"{q['npc_2_name']}: \"할 말 없습니다. 더 묻지 마세요.\" (입을 굳게 다물고 있습니다)")
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
                st.text("수집된 단서가 없습니다. 주민들과 적극적으로 대화해보세요.")

            st.markdown("---")
            st.markdown("#### ⚖️ 진범 지목 (추리 결판)")
            suspects = [q['npc_1_name'], q['npc_2_name']]
            chosen = st.selectbox("범인으로 의심되는 인물을 선택하세요", suspects)
            
            if st.button("🚨 이 사람을 범인으로 고발한다!", use_container_width=True):
                if chosen == q['correct_culprit']:
                    st.balloons()
                    st.success(f"🎯 정답입니다! 진범 {chosen}의 거짓말을 폭로하고 사건을 해결했습니다.")
                    
                    # 점진적 스탯 상승 및 보상 적용
                    stat_name = q['reward_stat_name']
                    boost = q['reward_stat_boost']
                    if stat_name in st.session_state.stats:
                        st.session_state.stats[stat_name] += boost
                    else:
                        st.session_state.stats["힘"] += boost
                        
                    st.session_state.gear = q['reward_gear']
                    if q['reward_skill'] not in st.session_state.skills:
                        st.session_state.skills.append(q['reward_skill'])
                        
                    st.info(f"✨ [퀘스트 보상] {stat_name} +{boost} 상승! | 신규 장비: {q['reward_gear']} | 신규 기술: {q['reward_skill']}")
                    
                    st.session_state.active_quest = None
                else:
                    st.error("❌ 틀렸습니다! 증거가 부족하거나 무고한 주민을 지목했습니다. 대화를 더 나눠보세요.")

        st.markdown("---")
        if st.button("🏠 마을 광장 메인으로 돌아가기"):
            st.session_state.location = "town"
            st.rerun()


# ==========================================
# 🌲 6. 사냥터 (필드 전투 및 성장)
# ==========================================
elif st.session_state.location == "hunting":
    st.title("🌲 사냥터: 루멘 외곽 숲")
    st.markdown("사냥을 통해 경험치와 골드를 얻을 수 있습니다. 하지만 장비와 스탯이 부족하면 강력한 몬스터에게 패배합니다!")
    st.markdown("---")

    power_score = sum(st.session_state.stats.values()) + (st.session_state.level * 10)
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown("#### 🟢 초급 사냥터 (슬라임, 포이즌 고블린)")
        if st.button("사냥 시작하기 (권장 전투력: 40 이상)", use_container_width=True):
            st.session_state.exp += 35
            st.session_state.gold += 20
            st.success("사냥 성공! 경험치 +35, 골드 +20G 획득")
            if st.session_state.exp >= st.session_state.max_exp:
                st.session_state.level += 1
                st.session_state.exp = 0
                st.session_state.max_exp = int(st.session_state.max_exp * 1.5)
                st.balloons()
                st.success(f"🎉 레벨 업! 현재 Lv. {st.session_state.level}")
            st.rerun()

    with col_h2:
        st.markdown("#### 🔴 중급 사냥터 (오크 약탈자, 섀도우 울프)")
        st.markdown("*주의: 추리 퀘스트를 해결하여 스탯과 장비를 강화하지 않으면 사냥할 수 없습니다!*")
        if st.button("중급 사냥 도전 (요구 전투력: 70 이상)", use_container_width=True):
            if power_score >= 70:
                st.session_state.exp += 75
                st.session_state.gold += 50
                st.success("중급 사냥 승리! 막대한 경험치와 골드를 획득했습니다.")
                if st.session_state.exp >= st.session_state.max_exp:
                    st.session_state.level += 1
                    st.session_state.exp = 0
                    st.session_state.max_exp = int(st.session_state.max_exp * 1.5)
                    st.balloons()
                st.rerun()
            else:
                st.error("❌ 전투력이 부족하여 몬스터에게 패배했습니다! 마을로 돌아가 '추리 퀘스트'를 해결하고 장비와 스탯을 키우세요.")

    st.markdown("---")
    if st.button("🏠 마을로 돌아가기"):
        st.session_state.location = "town"
        st.rerun()
