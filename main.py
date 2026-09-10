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

st.markdown("""
<style>
.stButton>button {background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;}
</style>
""", unsafe_allow_html=True)

if "uses" not in st.session_state:
    st.session_state.uses = 0
if "pro_expiry" not in st.session_state:
    st.session_state.pro_expiry = None

def is_pro():
    if st.session_state.pro_expiry is None:
        return False
    return datetime.now() < st.session_state.pro_expiry

def get_status():
    if is_pro():
        days = (st.session_state.pro_expiry - datetime.now()).days
        return f"PRO ACTIVE - {days+1} days left"
    else:
        return f"FREE - {3 - st.session_state.uses} left"

def clean(text):
    if not text:
        return ""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

def extract_text_from_image(image_bytes):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    models_to_try = [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "qwen/qwen3-32b",
        "qwen/qwen3.6-27b",
        "llava-v1.5-7b-4096-preview"
    ]
    last_error = ""
    for model_id in models_to_try:
        try:
            res = client.chat.completions.create(
                model=model_id,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "You are OCR. Extract the handwritten or printed essay text EXACTLY as written, including all spelling mistakes. Do not correct. Return only the essay text."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]
                }]
            )
            return res.choices[0].message.content
        except Exception as e:
            last_error = str(e)
            continue
    return f"OCR_ERROR: {last_error}"

def extract_text_from_pdf(pdf_bytes):
    text = ""
    if fitz:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc[:3]:
                text += page.get_text() + "\n"
            if len(text.strip()) < 30 and len(doc) > 0:
                pix = doc[0].get_pixmap(dpi=200)
                img_bytes = pix.tobytes("jpeg")
                text = extract_text_from_image(img_bytes)
        except Exception as e:
            text = f"PDF_ERROR: {e}"
    else:
        text = "Add PyMuPDF to requirements.txt"
    return text

st.title("📝 TEFLMate v4 - Batch Grader")
st.caption("Grade 50 essays in 4 minutes • Fair Price SA")

with st.expander("📘 How to Use & Choose Target Level (Read This)", expanded=True):
    st.markdown("### 3 Steps:")
    st.markdown("1. **Paste** text OR **Photo/PDF** of homework")
    st.markdown("2. **Pick Target Level** = level you WANT them to reach")
    st.markdown("3. **Click GRADE** = score + mistakes + corrected + PDF")
    st.divider()
    st.markdown("**A1** Grade 1-3 simple | **A2** Grade 4-6 basic past | **B1** Grade 7-9 4 paragraphs | **B2** Matric/College IELTS 5.5-6.5 | **C1** University IELTS 7+ | **C2** Teacher IELTS 8+")
    st.info("📸 Photo = handwritten book | 📄 PDF = WhatsApp scans — now auto-reads!")

with st.sidebar:
    st.markdown("### 🔑 Your Plan")
    st.info(get_status())
    st.markdown("#### 💰 Fair SA Pricing")
    st.markdown("- FREE: 3 essays")
    st.markdown("- Once-off: **R10** = +10 grades")
    st.markdown("- Weekly: **R49** = 7 days unlimited")
    st.markdown("- Monthly: **R99** = 30 days + Batch 50")
    st.markdown("- Yearly: **R799** = 365 days")
    st.markdown("")
    code = st.text_input("Got a code?", placeholder="Paste code", type="password").strip().upper()
    if st.button("Unlock Code"):
        now = datetime.now()
        code_map = {
            "TEACH10": ("+10 grades", lambda: setattr(st.session_state, 'uses', max(0, st.session_state.uses - 10))),
            "WEEK49": ("Weekly Pro", lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=7))),
            "MONTH99": ("Monthly Pro", lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=30))),
            "YEAR799": ("Yearly Pro", lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=365))),
            "TEFL2026": ("Monthly Pro", lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=30))),
        }
        if code in code_map:
            label, action = code_map[code]
            action()
            st.success(f"Unlocked {label}!")
            st.rerun()
        else:
            st.error("Code didn't work — send proof and I'll help.")
    st.divider()
    st.link_button("💳 Pay on Beacons", "https://beacons.ai/mr_mahomed")
    st.caption("Payshap: 0658006750")
    st.link_button(f"📧 Email proof to {YOUR_EMAIL}", f"mailto:{YOUR_EMAIL}?subject=TEFLMate Payment Proof")

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
    pdf.cell(0, 5, "beacons.ai/mr_mahomed | TEFLMate v4", align='C', ln=True)
    pdf.ln(10)
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, f"Target Level: {target_level} | Date: {datetime.now().strftime('%d %b %Y')}", ln=True)
    pdf.ln(2)
    pdf.set_fill_color(240, 245, 255)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(30, 64, 175)
    pdf.multi_cell(0, 6, clean(ai_result[:700]), border=1, fill=True)
    pdf.ln(4)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(0,0,0)
    pdf.cell(0, 7, "Original Essay:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, clean(original_essay))
    pdf.ln(4)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(5, 122, 80)
    pdf.cell(0, 7, "Full Grading Result:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(40,40,40)
    pdf.multi_cell(0, 6, clean(ai_result))
    pdf.ln(8)
    pdf.set_fill_color(17, 24, 39)
    pdf.set_font("Arial", '', 8)
    pdf.set_text_color(255,255,255)
    pdf.cell(0, 10, " Generated by TEFLMate v4", fill=True, ln=True)
    return bytes(pdf.output())

def grade_with_groq(essay_text, level):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    prompt = f"You are a Cambridge TEFL examiner for {level}. Grade this: {essay_text}. Return plain ASCII only, no unicode, hyphen - only. Include CEFR Level, Score/10 vs Target {level}, Summary 1 sentence, 2 Strengths, Table Mistake|Correction|Why, Then corrected version."
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}])
    return res.choices[0].message.content

tab1, tab2, tab3 = st.tabs(["Single Essay", "Batch 50 (PRO)", "📸 Photo / PDF NEW"])

with tab1:
    essay = st.text_area("Paste Student Essay:", height=180, placeholder="I go to market yesterday...")
    level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level")
    if st.button("GRADE ESSAY ->", key="single_btn"):
        if not is_pro() and st.session_state.uses >= 3:
            st.error("You've used 3 free grades. R10 = +10 more!")
            st.stop()
        if not essay.strip():
            st.warning("Paste an essay first")
            st.stop()
        with st.spinner(f"Grading as {level}..."):
            result_text = grade_with_groq(essay, level)
            if not is_pro():
                st.session_state.uses += 1
            st.success(get_status())
            st.markdown(result_text)
            pdf_bytes = create_branded_pdf(essay, result_text, level)
            st.download_button("📄 Download Branded PDF", pdf_bytes, file_name=f"Report_{level}.pdf", mime="application/pdf")

with tab2:
    st.markdown("Upload CSV with column `essay` or TXT 1 per line. PRO only.")
    level_b = st.selectbox("Target Level for batch:", ["A1","A2","B1","B2","C1","C2"], key="batch_level")
    uploaded = st.file_uploader("Upload file", type=["csv","txt"], key="batch_file")
    if st.button("GRADE BATCH 50 ->", key="batch_btn"):
        if not is_pro():
            st.error("Batch needs Monthly PRO (R99).")
            st.stop()
        if not uploaded:
            st.warning("Upload file first")
            st.stop()
        essays = []
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
            col = "essay" if "essay" in df.columns else df.columns[0]
            essays = df[col].dropna().astype(str).tolist()[:50]
        else:
            content = uploaded.read().decode("utf-8", errors="ignore")
            essays = [e.strip() for e in content.split("\n") if e.strip()][:50]
        st.info(f"Grading {len(essays)} essays...")
        results = []
        progress = st.progress(0)
        for i, es in enumerate(essays):
            res = grade_with_groq(es[:2000], level_b)
            results.append({"Essay": es[:100], "Result": res})
            progress.progress((i+1)/len(essays))
        st.success(f"Done! {len(results)} graded")
        st.dataframe(pd.DataFrame(results))
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        for idx, r in enumerate(results):
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Essay {idx+1} - {level_b}", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 6, clean(r["Result"]))
        batch_pdf = bytes(pdf.output())
        st.download_button("📄 Download All 50 Reports PDF", batch_pdf, file_name="Batch_50_Reports.pdf", mime="application/pdf")

with tab3:
    st.markdown("### 📸 Photo or PDF Scan")
    level_p = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="photo_level")
    colA, colB = st.columns(2)
    with colA:
        camera_pic = st.camera_input("Take photo")
        upload_img = st.file_uploader("Upload Image", type=["jpg","jpeg","png"], key="img_up")
    with colB:
        upload_pdf = st.file_uploader("Upload PDF Scan", type=["pdf"], key="pdf_up")

    image_bytes = None
    if camera_pic:
        image_bytes = camera_pic.getvalue()
        st.image(image_bytes, use_container_width=True)
    elif upload_img:
        image_bytes = upload_img.getvalue()
        st.image(image_bytes, use_container_width=True)

    if upload_pdf:
        st.info("Reading PDF...")
        pdf_bytes = upload_pdf.getvalue()
        extracted = extract_text_from_pdf(pdf_bytes)
        st.text_area("Text from PDF:", value=extracted, height=150, key="pdf_text_area")
        if st.button("GRADE PDF TEXT ->", key="grade_pdf_btn"):
            with st.spinner(f"Grading as {level_p}..."):
                result_text = grade_with_groq(extracted, level_p)
                if not is_pro():
                    st.session_state.uses += 1
                st.success(get_status())
                st.markdown(result_text)
                pdf_bytes_out = create_branded_pdf(extracted, result_text, level_p)
                st.download_button("📄 Download PDF", pdf_bytes_out, file_name=f"PDF_Report_{level_p}.pdf", mime="application/pdf")

    if image_bytes:
        if st.button("READ & GRADE PHOTO ->", key="photo_btn"):
            if not is_pro() and st.session_state.uses >= 3:
                st.error("You've used 3 free grades.")
                st.stop()
            with st.spinner("Reading handwriting..."):
                extracted = extract_text_from_image(image_bytes)
                if "OCR_ERROR" in extracted:
                    st.error(extracted)
                    st.stop()
                st.success("Read!")
                st.session_state['last_ocr'] = extracted
                st.rerun()

    if 'last_ocr' in st.session_state:
        edited = st.text_area("We read this — edit if needed:", value=st.session_state['last_ocr'], height=150, key="ocr_edit")
        if st.button("GRADE THIS TEXT ->", key="grade_ocr_btn"):
            with st.spinner(f"Grading as {level_p}..."):
                result_text = grade_with_groq(edited, level_p)
                if not is_pro():
                    st.session_state.uses += 1
                st.success(get_status())
                st.markdown(result_text)
                pdf_bytes_out = create_branded_pdf(edited, result_text, level_p)
                st.download_button("📄 Download PDF", pdf_bytes_out, file_name=f"Photo_Report_{level_p}.pdf", mime="application/pdf")

st.divider()
st.markdown("### ❤️ Payshap 0658006750 | Send proof by WhatsApp or Email and I'll send your code")
col1, col2 = st.columns(2)
with col1:
    st.link_button("💬 WhatsApp Proof", "https://wa.me/27658006750?text=Hi%20I%20paid%20for%20TEFLMate")
with col2:
    st.link_button("📧 Email Proof", f"mailto:{YOUR_EMAIL}?subject=TEFLMate Payment Proof")
st.caption("TEFLMate v4 • Durban, SA • Built by Mr Taahir Mahomed")
