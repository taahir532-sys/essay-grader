import streamlit as st
from groq import Groq

st.set_page_config(page_title="TEFL Grader - Durban")
st.title("📄 TEFL AI Essay Grader - Durban Edition")
st.write("Paste student essay -> Get CEFR level, score, and fixes in 5 seconds")

# --- This part now works BOTH locally and online ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    api_key = ""

if not api_key:
    api_key = st.text_input("Enter your Groq API Key (gsk_...)", type="password")

if not api_key:
    st.stop()

client = Groq(api_key=api_key)

essay = st.text_area("Student essay:", height=200)

if st.button("Grade Essay"):
    if not essay.strip():
        st.warning("Please paste an essay first")
    else:
        with st.spinner("Grading..."):
            prompt = f"""You are a TEFL teacher in Durban. Grade this essay:

Essay: {essay}

Give:
1. CEFR Level (A1-C2)
2. Score /10
3. 3 strengths
4. 3 fixes with examples
5. Corrected version

Be concise and helpful."""

            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": prompt}]
            )
            st.success("Graded!")
            st.markdown(response.choices[0].message.content)