import json
import os
import streamlit as st
import streamlit.components.v1 as components 
from google import genai
from google.genai import types
from openai import OpenAI
from pydantic import BaseModel, Field

# 🔑 [API 키 및 파일 설정]
SAVE_FILE = "rpg_sync_text_save.json"
LOG_FILE = "rpg_story_log.txt"  # 전체 AI 서사 기록용 TXT 파일

st.set_page_config(
    page_title="텍스트 RPG", page_icon="⚔️", layout="wide"
)
st.title("⚔️ 텍스트 실시간 RPG")
st.markdown(
    "AI가 매 턴마다 갱신하는 캐릭터 상태 정보 블록을 좌측 슬라이드바에 그대로 반영하는 판타지 RPG입니다. Gemini와 Groq 모델을 자유롭게 전환하여 사용할 수 있습니다."
)

# 🎨 [스크롤 위치 복원 JS]
st.markdown(
    """
    <script>
        (function() {
            const pWin = window.parent || window;
            const pDoc = pWin.document;
            const SCROLL_KEY = 'rpg_sync_text_scroll';
            function getScrollContainer() {
                return pDoc.querySelector('[data-testid="stAppViewContainer"]') || pDoc.querySelector('.main') || pWin;
            }
            const container = getScrollContainer();
            const savePos = function() {
                const pos = (container !== pWin) ? container.scrollTop : (pWin.pageYOffset || pDoc.documentElement.scrollTop);
                pWin.sessionStorage.setItem(SCROLL_KEY, pos);
            };
            if (container !== pWin) { container.addEventListener('scroll', savePos, { passive: true }); }
            else { pWin.addEventListener('scroll', savePos, { passive: true }); }
            function restoreScroll() {
                const saved = pWin.sessionStorage.getItem(SCROLL_KEY);
                if (saved !== null) {
                    const targetPos = parseInt(saved, 10);
                    const cont = getScrollContainer();
                    if (cont !== pWin) { cont.scrollTop =수정하실 **원본 코드**가 질문에 누락되어 있습니다. 정확한 위치에 원하시는 기능을 구현하려면 현재 작성 중이신 코드를 먼저 확인해야 합니다. 

요청하신 기능은 일반적으로 다음과 같은 로직으로 추가됩니다.

* **게임 컨셉 입력창:** 우측 슬라이드 패널 HTML에 `<textarea>`를 배치하고, 사용자가 입력한 컨셉 텍스트를 변수에 저장합니다. 이후 AI(LLM) API를 호출할 때 시스템 프롬프트(System Prompt)에 해당 컨셉을 주입하여 스토리의 방향성을 강제합니다.
* **선택지 음성 듣기(TTS):** 자바스크립트의 기본 기능인 Web Speech API(`speechSynthesis.speak`)를 활용합니다. 선택지 UI 옆에 스피커 아이콘을 추가하고, 클릭 시 해당 선택지의 텍스트를 읽어주도록 이벤트를 연결합니다.

작업 중이신 전체 코드(HTML, CSS, JS 또는 파이썬 코드 등)를 복사해서 붙여넣어 주시겠어요? 코드를 확인하는 대로 즉시 요청하신 세 가지 기능이 모두 작동하도록 수정해 드리겠습니다.
