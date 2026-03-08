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
def load_system_prompt():
    if not REFERENCE_DIR.exists():
        return SYSTEM_PROMPT_HEADER + "현재 참고 자료가 없습니다.", []
    parts = [SYSTEM_PROMPT_HEADER]
    names = []
    for md_file in sorted(REFERENCE_DIR.glob("*.md")):
        parts.append(f"# {md_file.stem}\n\n{md_file.read_text(encoding='utf-8')}")
        names.append(md_file.stem)
    return "\n\n---\n\n".join(parts), names


def main():
    st.set_page_config(page_title="아파트 리뷰 Q&A", page_icon="🏠")

    api_key = st.secrets.get("CLAUDE_API_KEY", "")
    if not api_key:
        st.error("CLAUDE_API_KEY가 설정되지 않았습니다.")
        return

    system_prompt, ref_names = load_system_prompt()

    with st.sidebar:
        st.header("로드된 단지")
        if ref_names:
            for name in ref_names:
                st.success(f"✓ {name}")
        else:
            st.warning("참고 자료 없음")

    st.title("🏠 아파트 리뷰 Q&A")
    st.caption("입주민 리뷰 데이터를 기반으로 매수 관점에서 답변합니다.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("질문하세요 (예: 삼성래미안 층간소음 어때요?)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

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
