import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
from fpdf import FPDF
import unicodedata
import pandas as pd
import base64

try:
    import fitz
except ImportError:
    fitz = None

YOUR_EMAIL = "taahir532@gmail.com"

st.set_page_config(page_title="TEFLMate v4 Pro", page_icon="📝", layout="centered")

st.markdown("""<style>.stButton>button {background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;}</style>""", unsafe_allow_html=True)

if "uses" not in st.session_state:
    st.session_state.uses = 0
if "pro_expiry" not in st.session_state:
    st.session_state.pro_expiry = None

def is_pro():
    return st.session_state.pro_expiry and datetime.now() < st.session_state.pro_expiry

def get_status():
    if is_pro():
        days = (st.session_state.pro_expiry - datetime.now()).days
        return f"PRO ACTIVE - {days+1} days left"
    else:
        return f"FREE - {3 - st.session_state.uses} left"

def clean(text):
    return unicodedata.normalize('NFKD', text or "").encode('ascii', 'ignore').decode('ascii')

def extract_text_from_image(image_bytes):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    # Groq current working vision model is qwen/qwen3.6-27b, scout is deprecated but still serving
    models_to_try = [
        "qwen/qwen3.6-27b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "qwen/qwen3-32b"
    ]
    last_error = ""
    for model_id in models_to_try:
        try:
            res = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user","content": [
                    {"type": "text", "text": "OCR: Extract handwritten text EXACTLY as written, keep mistakes. Return only text."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}]
            )
            return res.choices[0].message.content
        except Exception as e:
            last_error = str(e)
            continue
    return f"OCR_ERROR: {last_error}"

def extract_text_from_pdf(pdf_bytes):
    if not fitz:
        return "Add PyMuPDF to requirements.txt"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join([p.get_text() for p in doc[:3]])
        if len(text.strip()) < 30 and len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=200)
            text = extract_text_from_image(pix.tobytes("jpeg"))
        return text
    except Exception as e:
        return f"PDF_ERROR: {e}"

def create_branded_pdf(original_essay, ai_result, target_level):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(17, 24, 39)
    pdf.rect(0, 0, 210, 32, 'F')
    pdf.set_y(7)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(255,255,255)
    pdf.cell(0, 8, "Mr Mahomed | Essay Grader Report", align='C', ln=True)
    pdf.set_font("Arial", '', 8)
    pdf.set_text_color(200,200,200)
    pdf.cell(0, 5, "beacons.ai/mr_mahomed | TEFLMate v4.7", align='C', ln=True)
    pdf.ln(10)
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, f"Target Level: {target_level} | Date: {datetime.now().strftime('%d %b %Y')}", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, clean(ai_result))
    pdf.ln(4)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 7, "Original:", ln=True)
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(0, 6, clean(original_essay[:3000]))
    return pdf.output(dest='S').encode('latin-1')

def grade_with_groq(essay_text, level):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    prompt = f"You are Cambridge TEFL examiner for {level}. Grade: {essay_text}. ASCII only. Include CEFR Level, Score/10 vs Target {level}, Summary, 2 Strengths, Table Mistake|Correction|Why, Then corrected version."
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}])
    return res.choices[0].message.content

st.title("📝 TEFLMate v4.7 Pro")
st.caption("Photo + PDF + Batch + Guide")

with st.sidebar:
    st.info(get_status())
    st.markdown("**Fair SA:** FREE 3 | R10 +10 | R49 Week | R99 Month | R799 Year")
    code = st.text_input("Code?", type="password").strip().upper()
    if st.button("Unlock"):
        now = datetime.now()
        maps = {"TEACH10": lambda: setattr(st.session_state, 'uses', max(0, st.session_state.uses - 10)),
                "WEEK49": lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=7)),
                "MONTH99": lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=30)),
                "YEAR799": lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=365))}
        if code in maps:
            maps[code](); st.success("Unlocked!"); st.rerun()
        else: st.error("Invalid")
    st.link_button("💳 Pay Beacons", "https://beacons.ai/mr_mahomed")
    st.caption("Payshap: 0658006750")

tab1, tab2, tab3, tab4 = st.tabs(["Single Essay", "Batch 50 (PRO)", "📸 Photo / PDF", "📘 Target Levels Guide"])

with tab1:
    essay = st.text_area("Paste Essay:", height=180, key="s_essay")
    level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="s_level")
    if st.button("GRADE ESSAY ->", key="s_btn"):
        if not is_pro() and st.session_state.uses >= 3:
            st.error("Free limit"); st.stop()
        with st.spinner("Grading..."):
            result = grade_with_groq(essay, level)
            if not is_pro(): st.session_state.uses += 1
            st.markdown(result)
            st.download_button("📄 Download PDF", create_branded_pdf(essay, result, level), file_name=f"Report_{level}.pdf")

with tab2:
    st.markdown("Upload CSV (col `essay`) or TXT. PRO only.")
    level_b = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="b_level")
    uploaded = st.file_uploader("Upload", type=["csv","txt"], key="b_file")
    if st.button("GRADE BATCH 50 ->", key="b_btn"):
        if not is_pro(): st.error("Needs PRO"); st.stop()
        essays = []
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded); col = "essay" if "essay" in df.columns else df.columns[0]
            essays = df[col].dropna().astype(str).tolist()[:50]
        else:
            essays = [e.strip() for e in uploaded.read().decode("utf-8", errors="ignore").split("\n") if e.strip()][:50]
        results = []; prog = st.progress(0)
        for i, es in enumerate(essays):
            results.append({"Essay": es[:100], "Result": grade_with_groq(es[:2000], level_b)}); prog.progress((i+1)/len(essays))
        st.dataframe(pd.DataFrame(results))
        pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15)
        for idx, r in enumerate(results):
            pdf.add_page(); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, f"Essay {idx+1} - {level_b}", ln=True)
            pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 6, clean(r["Result"]))
        st.download_button("📄 Download All 50", pdf.output(dest='S').encode('latin-1'), file_name="Batch_50.pdf")

with tab3:
    st.markdown("### 📸 Photo or PDF Scan")
    level_p = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="p_level")
    c1, c2 = st.columns(2)
    with c1:
        cam = st.camera_input("Take photo"); img_up = st.file_uploader("Upload Image", type=["jpg","jpeg","png"], key="p_img")
    with c2:
        pdf_up = st.file_uploader("Upload PDF", type=["pdf"], key="p_pdf")
    ibytes = None
    if cam: ibytes = cam.getvalue()
    elif img_up: ibytes = img_up.getvalue()
    if ibytes: st.image(ibytes, use_container_width=True)
    if pdf_up:
        extracted = extract_text_from_pdf(pdf_up.getvalue())
        st.text_area("Text from PDF:", value=extracted, height=150, key="pdf_txt")
        if st.button("GRADE PDF TEXT ->", key="pdf_btn"):
            res = grade_with_groq(extracted, level_p); st.markdown(res)
            st.download_button("📄 Download PDF", create_branded_pdf(extracted, res, level_p), file_name=f"PDF_{level_p}.pdf")
    if ibytes and st.button("READ & GRADE PHOTO ->", key="ph_btn"):
        with st.spinner("Reading..."):
            ext = extract_text_from_image(ibytes)
            if "OCR_ERROR" in ext: st.error(ext)
            else: st.session_state['last_ocr'] = ext; st.rerun()
    if 'last_ocr' in st.session_state:
        edited = st.text_area("We read — edit if needed:", value=st.session_state['last_ocr'], height=150, key="ocr_edit")
        if st.button("GRADE THIS TEXT ->", key="ocr_grade"):
            res = grade_with_groq(edited, level_p); st.markdown(res)
            st.download_button("📄 Download PDF", create_branded_pdf(edited, res, level_p), file_name=f"Photo_{level_p}.pdf")

with tab4:
    st.markdown("## 📘 How Target Levels Work")
    st.info("Target Level = The level you WANT the student to reach. We grade AGAINST that level. So if you pick B2, we will be strict like Matric marker.")
    st.markdown("""
    ### 🎯 Pick Like This:
    **A1 Beginner (Grade 1-3)**
    - Can write: "I am happy. My name is..."
    - Use for: Very weak learners, ABET Level 1
    - We check: Capital letters, full stop, basic spelling

    **A2 Elementary (Grade 4-6)**
    - Can write: "Yesterday I went to shop. It was fun because..."
    - Use for: Primary school, ESL beginners
    - We check: Past tense was/were, and/but/because

    **B1 Intermediate (Grade 7-9)**
    - Can write: 4 paragraphs, 120-150 words, linking words
    - Use for: Grade 7-9 CAPS, high school
    - We check: Paragraphs, however/therefore/firstly, tenses

    **B2 Upper-Intermediate (Grade 10-12 / Matric)**
    - Can write: 180-250 words, essay structure, argument
    - Use for: Matric, College, IELTS 5.5-6.5, TVET
    - We check: Cohesion, vocabulary range, complex sentences

    **C1 Advanced (University)**
    - Can write: 250-300 words academic, less grammar errors
    - Use for: University, IELTS 7+, business English
    - We check: Academic vocab, hedging, referencing

    **C2 Mastery (Teacher / IELTS 8+)**
    - Can write: Near native, nuanced, almost no errors
    - Use for: Teachers, IELTS 8+, proofreading staff emails
    - We check: Everything - we are very strict

    ### 💡 Pro Tip:
    If student is A2 but you want them to reach B1, **pick B1**.
    The report will show GAP: what they miss to get to B1.

    ### 📸 Photo/PDF Tip:
    That note you uploaded: "INTERACTIONS... CONTRIBUTING TO A CULTURE..."
    That is **C1 business English**. So pick C1 or B2 to grade it.
    """)
    st.success("Set Target Level BEFORE you click Grade. The level changes how strict the AI is.")

st.divider()
st.caption("TEFLMate v4.7 • Fixed PDF + Vision • Built by Mr Taahir Mahomed")
