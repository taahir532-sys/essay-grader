import streamlit as st
from groq import Groq

st.set_page_config(page_title="TEFL Grader Pro", page_icon="📝", layout="centered")

st.markdown("""
<style>
.stButton>button {background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;}
</style>
""", unsafe_allow_html=True)

# -- PAYWALL COUNTER ---
if "uses" not in st.session_state:
    st.session_state.uses = 0

st.title("📝 TEFL Essay Grader Pro")
st.caption("CEFR grading in 5 seconds • Built for TEFL Teachers")

# --- V3 NEW: CEFR GRADING LEVELS SUMMARY ---
with st.expander("📘 What do the levels mean? (A1 to C2)", expanded=False):
    st.markdown("""
    **A1 - Beginner:** Can use simple phrases like "My name is...". Lots of basic grammar mistakes expected.
    **A2 - Elementary:** Can write about daily routines. Uses simple past but with errors.
    **B1 - Intermediate:** Can write connected paragraphs. Tells a story or gives reasons. Grammar mostly correct.
    **B2 - Upper-Intermediate:** Can argue a point clearly with good vocabulary. Understands complex texts.
    **C1 - Advanced:** Can write complex, well-structured essays. Almost native grammar.
    **C2 - Mastery:** Near-native level. Precise, fluent, academic/professional.

    *How this grader works: We compare the essay to your Target Level. If you set Target B1 but the essay is A2, we will flag it.*
    """)

essay = st.text_area("Paste Student Essay:", height=200, placeholder="I go to market yesterday...")
level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"])

if st.button("GRADE ESSAY →"):
    # Paywall: 1 free grade only
    if st.session_state.uses >= 1:
        st.error("🚫 Free limit reached!")
        st.info("You used your 1 free grade. Unlock unlimited for R49/mo or get PDF correction for R30.")
        st.stop()

    if not essay.strip():
        st.warning("Paste an essay first")
        st.stop()

    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        with st.spinner(f"Grading as {level} examiner..."):
            prompt = f"""You are a Cambridge TEFL examiner for level {level}.
            Grade this essay: {essay}
            Return EXACTLY:
            **CEFR Level:** [A1/A2/B1/B2/C1/C2] - [Level Name]
            **Score:** [X/10] vs Target {level}
            **Summary:** 1 sentence about why this level.
            **Strengths:**
            1....
            2....
            | Mistake | Correction | Why |
            |---|---|---|
            |... |... |... |
            Keep it short, teacher-friendly.
            """
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}])

        st.session_state.uses += 1
        st.success(f"Free grades left: {1 - st.session_state.uses}")
        st.markdown(res.choices[0].message.content)

        # --- MONEY SECTION - EXACT AS YOUR IMAGE ---
        st.divider()
        st.markdown("### ❤️ Need more? Get Full Detailed Correction")
        st.markdown("Pay **R30 via **Payshap to 0658006750** then click below")
        st.link_button("I Paid R30 - Send Essay on WhatsApp", "https://wa.me/27658006750?text=Hi%20I%20paid%20R30%20-%20Send%20Essay")

        st.caption("TEFL Grader Pro • Cambridge CEFR Standard • Durban, SA • Built by Mr Taahir Mahomed")

    except Exception as e:
        st.error(f"Error: {e}")

# Footer always visible
st.markdown("---")
st.caption("TEFL Grader Pro • Cambridge CEFR Standard • Durban, SA • Built by Mr Taahir Mahomed")
