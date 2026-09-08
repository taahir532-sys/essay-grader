import streamlit as st
from groq import Groq

st.set_page_config(page_title="TEFL Grader Pro", page_icon="🎓", layout="centered")

st.markdown("""
<style>
.stButton>button {background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;}
</style>
""", unsafe_allow_html=True)

# --- PAYWALL COUNTER ---
if "uses" not in st.session_state:
    st.session_state.uses = 0

st.title("🎓 TEFL Essay Grader Pro")
st.caption("CEFR grading in 5 seconds • Built for TEFL teachers")

essay = st.text_area("Paste Student Essay:", height=200, placeholder="I go to market yesterday...")
level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"])

if st.button("GRADE ESSAY →"):
    # Paywall: 1 free grade only
    if st.session_state.uses >= 1:
        st.error("🔒 Free limit reached!")
        st.info("You used your 1 free grade. Unlock unlimited for R49/mo or get PDF correction for R30.")
        st.stop()

    if not essay.strip():
        st.warning("Paste an essay first")
        st.stop()

    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        with st.spinner("Grading..."):
            prompt = f"You are a Cambridge TEFL examiner for {level}. Grade: {essay}. Return CEFR, Score/10, 2 Strengths, table Mistake|Correction|Why"
            res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}])
            st.session_state.uses += 1
            st.success(f"Free grades left: {1 - st.session_state.uses}")
            st.markdown(res.choices[0].message.content)
    except Exception as e:
        st.error(f"Error: {e}")

# --- MONEY BUTTONS ---
st.markdown("---")
st.markdown("### ❤️ Need more? Get Full Detailed Correction")
st.markdown("Pay **R30** via **Payshap to 0658006750 (Absa)** then click below"    
st.link_button("I Paid R30 - Send Essay on WhatsApp", "https://wa.me/27658006750?text=Hi!%20paid%20R30")

st.caption("TEFL Grader Pro • Cambridge CEFR Standard • Durban, SA")
