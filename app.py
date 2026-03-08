import streamlit as st
from pathlib import Path
import anthropic

# --- 설정 ---
REFERENCE_DIR = Path(".claude/skills/apt-review/reference")

SYSTEM_PROMPT_HEADER = """당신은 아파트 입주민 리뷰 데이터를 기반으로 매수 관점에서 답변하는 전문 상담사입니다.

아래는 각 아파트 단지의 입주민 리뷰를 주제별로 요약한 참고 자료입니다. 이 자료를 바탕으로 질문에 답변하세요.

답변 시 유의사항:
- 리뷰 데이터에 없는 내용은 추측하지 말고 "해당 정보는 리뷰에 없습니다"라고 말하세요.
- 단지명을 명시하여 비교 답변을 제공하세요.
- 매수 관점에서 실질적이고 솔직하게 답변하세요.
- 답변은 간결하게 핵심만 전달하세요. 불필요한 서론/마무리 문장은 생략하세요.
- 동 번호(예: 201동, 205동)는 숫자 앞뒤에 특수문자 없이 그대로 쓰세요. 물결표(~)나 취소선 마크다운 문법은 절대 사용하지 마세요.

---

"""


@st.cache_data
def load_all_references():
    if not REFERENCE_DIR.exists():
        return {}
    return {
        md_file.stem: md_file.read_text(encoding='utf-8')
        for md_file in sorted(REFERENCE_DIR.glob("*.md"))
    }


def build_system_prompt(refs: dict, selected: list[str]) -> str:
    parts = [SYSTEM_PROMPT_HEADER]
    for name in selected:
        parts.append(f"# {name}\n\n{refs[name]}")
    if len(parts) == 1:
        parts.append("현재 선택된 단지가 없습니다.")
    return "\n\n---\n\n".join(parts)


def main():
    st.set_page_config(page_title="아파트 리뷰 Q&A", page_icon="🏠")

    api_key = st.secrets.get("CLAUDE_API_KEY", "")
    if not api_key:
        st.error("CLAUDE_API_KEY가 설정되지 않았습니다.")
        return

    all_refs = load_all_references()

    with st.sidebar:
        st.header("단지 선택")
        if not all_refs:
            st.warning("참고 자료 없음")
            selected = []
        else:
            col1, col2 = st.columns(2)
            if col1.button("전체 선택", use_container_width=True):
                st.session_state.selected = list(all_refs.keys())
            if col2.button("전체 해제", use_container_width=True):
                st.session_state.selected = []

            if "selected" not in st.session_state:
                st.session_state.selected = list(all_refs.keys())

            selected = []
            for name in all_refs:
                checked = st.checkbox(name, value=name in st.session_state.selected, key=f"chk_{name}")
                if checked:
                    selected.append(name)
            st.session_state.selected = selected

        if selected:
            st.caption(f"{len(selected)}개 단지 선택됨")

    st.title("🏠 아파트 리뷰 Q&A")
    st.caption("입주민 리뷰 데이터를 기반으로 아파트 매수 희망 관점에서 답변합니다.")

    if selected:
        st.info(f"대상: {' · '.join(selected)}", icon="🏘️")
    else:
        st.warning("사이드바에서 단지를 선택해주세요.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("질문하세요 (예: 층간소음 어때요?)"):
        if not selected:
            st.warning("먼저 사이드바에서 단지를 선택해주세요.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        system_prompt = build_system_prompt(all_refs, selected)

        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    system=system_prompt,
                    messages=st.session_state.messages,
                )
                answer = response.content[0].text

            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
