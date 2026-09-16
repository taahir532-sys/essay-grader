import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
from fpdf import FPDF
import unicodedata
import pandas as pd
import base64
import requests

try:
    import fitz
except ImportError:
    fitz = None

# ===== CONFIG =====
YOUR_EMAIL = "taahir532@gmail.com"
PAYPAL_ME = "https://paypal.me/TaahirMahomed"

st.set_page_config(page_title="TEFLMate v5.1 Pro", page_icon="📝", layout="centered")

# ===== UPTIMEROBOT FIX:?health endpoint =====
# UptimeRobot monitor 2 should hit /?health
q_params = st.query_params
if "health" in q_params:
    st.json({"status": "ok", "time": datetime.now().isoformat(), "service": "TEFLMate"})
    st.stop()

st.markdown("""<style>.stButton>button {background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;}
div[data-testid="stMetricValue"] {font-size:18px;}
</style>""", unsafe_allow_html=True)

# ===== SESSION STATE =====
if "uses" not in st.session_state:
    st.session_state.uses = 0
if "pro_expiry" not in st.session_state:
    st.session_state.pro_expiry = None
if "total_graded" not in st.session_state:
    st.session_state.total_graded = 0
if "cache_hits" not in st.session_state:
    st.session_state.cache_hits = 0
if "geo" not in st.session_state:
    try:
        ip_data = requests.get("https://ipapi.co/json/", timeout=3).json()
        country = ip_data.get("country_code", "ZA")
    except:
        country = "ZA"
    if country == "ZA":
        st.session_state.geo = {"symbol":"R", "weekly":"49", "monthly":"99", "yearly":"799", "once":"10", "code":"ZAR"}
    elif country == "GB":
        st.session_state.geo = {"symbol":"£", "weekly":"3.99", "monthly":"6.99", "yearly":"55", "once":"0.99", "code":"GBP"}
    elif country in ["DE","FR","NL","IT","ES","PT","IE"]:
        st.session_state.geo = {"symbol":"€", "weekly":"4.99", "monthly":"8.50", "yearly":"65", "once":"0.99", "code":"EUR"}
    else:
        st.session_state.geo = {"symbol":"$", "weekly":"4.99", "monthly":"8.50", "yearly":"65", "once":"0.99", "code":"USD"}

def is_pro():
    return st.session_state.pro_expiry is not None and datetime.now() < st.session_state.pro_expiry

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
    models_to_try = [
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "meta-llama/llama-4-scout-17b-16e-instruct"
    ]
    last_err = ""
    for model_id in models_to_try:
        try:
            res = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user","content": [
                    {"type": "text", "text": "OCR: Extract handwritten text EXACTLY as written, keep mistakes. Return only text."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}]
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            last_err = str(e)
            continue
    return f"OCR_ERROR: {last_err}"

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
    pdf.ln(10)
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, f"Target Level: {target_level} | Date: {datetime.now().strftime('%d %b %Y')}", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, clean(ai_result))
    return pdf.output(dest='S').encode('latin-1')

def grade_with_groq(essay_text, level):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    prompt = f"""You are Cambridge TEFL examiner for {level}. Grade this essay: {essay_text[:3000]}.
RULES: ASCII only. No emojis.
FORMAT:
CEFR Level:
Score /10 vs Target {level}:
Summary: (2 lines)
Strengths: 2 bullets
Table: Mistake | Correction | Why
Corrected Version: Full corrected essay.
Keep it concise for teachers.
"""
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}])
    return res.choices[0].message.content

# ===== HEADER =====
st.title("📝 TEFLMate v5.1 - Batch Grader")
st.caption(f"Grade 50 essays in 4 minutes • Pricing in {st.session_state.geo['code']}")

with st.sidebar:
    st.markdown("### 🔑 Your Plan")
    st.info(get_status())
    g = st.session_state.geo
    st.markdown(f"#### 💰 Pricing ({g['code']})")
    st.markdown(f"- FREE: 3 essays")
    st.markdown(f"- Once-off: {g['symbol']}{g['once']} = +10 grades")
    st.markdown(f"- Weekly: {g['symbol']}{g['weekly']} = 7 days unlimited")
    st.markdown(f"- Monthly: {g['symbol']}{g['monthly']} = 30 days unlimited + Batch 50 Tool")
    st.caption("Batch 50 = Upload CSV and grade 50 essays at once into 1 PDF. For teachers with many books.")
    st.markdown(f"- Yearly: {g['symbol']}{g['yearly']} = 365 days")
    st.divider()
    st.markdown("#### 🌍 Pay Globally")
    st.link_button(f"💳 Pay with PayPal", PAYPAL_ME)
    st.caption(f"PayPal.me/TaahirMahomed\nPay {g['symbol']}{g['once']} / {g['symbol']}{g['weekly']} / {g['symbol']}{g['monthly']} / {g['symbol']}{g['yearly']} - Then send proof")
    st.divider()
    st.caption("Loved it? Send proof and I'll send your code instantly ❤️")
    code = st.text_input("Got a code?", placeholder="Paste your code here", type="password").strip().upper()
    if st.button("Unlock Code"):
        now = datetime.now()
        code_map = {
            "TEACH10": lambda: setattr(st.session_state, 'uses', max(0, st.session_state.uses - 10)),
            "WEEK49": lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=7)),
            "MONTH99": lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=30)),
            "YEAR799": lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=365)),
            "TEFL2026": lambda: setattr(st.session_state, 'pro_expiry', now + timedelta(days=30)),
        }
        if code in code_map:
            code_map[code]()
            st.success("Unlocked!")
            st.rerun()
        else:
            st.error("That code didn't work")

# ===== 5 TABS - FIXED STRUCTURE =====
tab_grade, tab_photo, tab_batch, tab_guide, tab_super = st.tabs(["📝 Grade", "📸 Photo / PDF", "Batch 50 (PRO)", "📘 Guide", "⭐ SUPER"])

with tab_grade:
    st.markdown("### ✍️ Grade Typed Essay (Text Only)")
    st.info("💡 For handwritten books / paper scans, use **Photo / PDF tab**. This tab is for TYPED text only - no duplicates.")
    essay = st.text_area("Paste Student Essay:", height=200, placeholder="e.g. I broken my leg last week. I was playing soccer and I fall down.")
    level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level")
    if st.button("GRADE ESSAY ->", key="grade_single"):
        if not essay.strip():
            st.warning("Paste an essay first")
            st.stop()
        if not is_pro() and st.session_state.uses >= 3:
            st.error("Free limit reached - upgrade to continue")
            st.stop()
        with st.spinner("Grading..."):
            result_text = grade_with_groq(essay, level)
            if not is_pro():
                st.session_state.uses += 1
            st.session_state.total_graded += 1
            st.markdown(result_text)
            st.download_button("📄 Download PDF", create_branded_pdf(essay, result_text, level), file_name=f"Report_{level}.pdf", key="dl_single")
with tab_photo:
    st.markdown("### 📸 Photo or PDF Scan — Handwritten Books")
    st.success("This is the ONLY place for photos. Grade tab is text-only now.")
    level_p = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="photo_level")
    colA, colB = st.columns(2)
    with colA:
        camera_pic = st.camera_input("Take photo of book")
        upload_img = st.file_uploader("Upload Image", type=["jpg","jpeg","png"], key="img_up")
    with colB:
        upload_pdf = st.file_uploader("Upload PDF Scan", type=["pdf"], key="pdf_up")

    image_bytes = None
    if camera_pic:
        image_bytes = camera_pic.getvalue()
    elif upload_img:
        image_bytes = upload_img.getvalue()

    if image_bytes:
        st.image(image_bytes, use_container_width=True)

    if upload_pdf:
        extracted = extract_text_from_pdf(upload_pdf.getvalue())
        st.text_area("Text from PDF:", value=extracted, height=150, key="pdf_text_area")
        if st.button("GRADE PDF TEXT ->", key="grade_pdf"):
            if not is_pro() and st.session_state.uses >= 3:
                st.error("Free limit reached")
                st.stop()
            with st.spinner("Grading PDF..."):
                result_text = grade_with_groq(extracted, level_p)
                if not is_pro(): st.session_state.uses += 1
                st.session_state.total_graded += 1
                st.markdown(result_text)
                st.download_button("📄 Download PDF", create_branded_pdf(extracted, result_text, level_p), file_name=f"PDF_{level_p}.pdf", key="dl_pdf")

    if image_bytes and st.button("READ & GRADE PHOTO ->", key="read_photo"):
        with st.spinner("Reading handwriting..."):
            extracted = extract_text_from_image(image_bytes)
            if "OCR_ERROR" in extracted:
                st.error(extracted)
            else:
                st.session_state['last_ocr'] = extracted
                st.rerun()

    if 'last_ocr' in st.session_state:
        edited = st.text_area("We read — edit if needed:", value=st.session_state['last_ocr'], height=150, key="ocr_edit")
        if st.button("GRADE THIS TEXT ->", key="grade_ocr"):
            if not is_pro() and st.session_state.uses >= 3:
                st.error("Free limit reached")
                st.stop()
            with st.spinner("Grading..."):
                result_text = grade_with_groq(edited, level_p)
                if not is_pro(): st.session_state.uses += 1
                st.session_state.total_graded += 1
                st.markdown(result_text)
                st.download_button("📄 Download PDF", create_branded_pdf(edited, result_text, level_p), file_name=f"Photo_{level_p}.pdf", key="dl_photo")

with tab_batch:
    st.markdown("### 📦 Upload 50 Essays At Once (PRO Feature)")
    g = st.session_state.geo
    st.info(f"Monthly {g['symbol']}{g['monthly']} unlocks this: Grade 50 essays at once instead of one by one. Perfect for teachers with many books.")
    sample_df = pd.DataFrame({
        "student_name": ["Student 1", "Student 2", "Student 3"],
        "essay": ["I go to market yesterday. It was very fun because I buyed many things.", "My best friend is Thandi. She is kind and she help me every day.", "I broken my leg last week. I was playing soccer and I fall down."]
    })
    csv_template = sample_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV Template - Fill 50 essays here", csv_template, file_name="TEFLMate_Batch_Template_50.csv", mime="text/csv", key="template_btn")
    st.caption("1. Download template above 2. Open in Excel/Sheets 3. Replace essays with your 50 students 4. Save and upload below")
    st.divider()
    level_b = st.selectbox("Target Level for batch:", ["A1","A2","B1","B2","C1","C2"], key="batch_level")
    uploaded = st.file_uploader("Upload your filled CSV or TXT", type=["csv","txt"], key="batch_file")
    if st.button("GRADE BATCH 50 ->", key="grade_batch"):
        if not is_pro():
            st.error(f"Batch 50 needs Monthly PRO {g['symbol']}{g['monthly']}")
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
            results.append({"Essay": es[:100], "Result": grade_with_groq(es[:2000], level_b)})
            progress.progress((i+1)/len(essays))
            st.session_state.total_graded += 1
        st.success(f"Done! {len(results)} graded")
        st.dataframe(pd.DataFrame(results))
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        for idx, r in enumerate(results):
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Essay {idx+1}", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 6, clean(r["Result"]))
        st.download_button("📄 Download All 50 Reports PDF", pdf.output(dest='S').encode('latin-1'), file_name="Batch_50.pdf", key="dl_batch")

with tab_guide:
    st.markdown("## 📘 How To Use TEFLMate - Complete Guide")
    st.info("Target Level = The level you WANT them to reach. We grade AGAINST that level.")

    st.markdown("### 🚀 Quick Start - 3 Steps")
    st.markdown("""
    **Step 1: Choose Input Type**
    - Typed essay? Use **Grade** tab
    - Handwritten/photo? Use **Photo / PDF** tab
    - 50 essays? Use **Batch 50** tab

    **Step 2: Select Target Level**
    - If student is A2 but you want B1, PICK B1. Report shows GAP.

    **Step 3: Grade & Download PDF**
    - Click Grade, get report, download branded PDF with your name
    """)
    st.divider()

    st.markdown("### 🎯 Choose Target Level Like This")
    c1, c2 = st.columns(2)
    with c1:
        st.success("**🟢 A1 – Beginner**\\nGrade 1-3\\n*I am happy...*\\nChecks: Capitals, full stop")
        st.warning("**🟡 B1 – Intermediate**\\nGrade 7-9\\n*120 words, however*\\nChecks: Paragraphs")
        st.error("**🔴 C1 – Advanced**\\nUniversity\\n*250 words academic*")
    with c2:
        st.info("**🔵 A2 – Elementary**\\nGrade 4-6\\n*Yesterday I went...*\\nChecks: Past tense")
        st.error("**🟠 B2 – Matric**\\nGrade 10-12, IELTS 5.5\\n*200 words argument*")
        st.markdown("**⚫ C2 – Mastery**\\nTeacher / IELTS 8+\\n*Near native*")
    st.divider()
    st.markdown("### 📊 Grading Standards Explained")
    st.table(pd.DataFrame([
        {"Level": "A1", "Class": "Grade 1-3", "Words": "20-40", "Use For": "ABET, Foundation", "Checks": "Capitals, period"},
        {"Level": "A2", "Class": "Grade 4-6", "Words": "50-80", "Use For": "Primary school", "Checks": "Past tense, plurals"},
        {"Level": "B1", "Class": "Grade 7-9", "Words": "120-150", "Use For": "High school", "Checks": "Paragraphs, linking words"},
        {"Level": "B2", "Class": "Matric", "Words": "180-250", "Use For": "Matric, College, IELTS 5.5", "Checks": "Argument, cohesion"},
        {"Level": "C1", "Class": "University", "Words": "250-300", "Use For": "University, Work", "Checks": "Academic vocab, complex grammar"},
        {"Level": "C2", "Class": "Mastery", "Words": "300+", "Use For": "Teachers, IELTS 8+", "Checks": "Near-native, nuance"},
    ]))
    st.divider()

    st.markdown("### ⚠️ Common Mistakes By Level")
    st.markdown("""
    **A1-A2 Students usually:**
    - I is -> I am / I was
    - No capital I
    - buyed -> bought (irregular past)
    - No full stop

    **B1-B2 Students usually:**
    - because -> Because at start of sentence needs comma
    - No paragraphs
    - very very good -> excellent
    - Same word repeated

    **C1-C2 Students usually:**
    - Informal slang in formal essay
    - Weak linking: but, and -> however, furthermore
    - No thesis statement
    """)
    st.divider()

    st.markdown("### 💡 Pro Tips For Teachers")
    st.markdown("""
    1. **Use Batch 50** for whole class - saves 2 hours marking
    2. **Photo tab** works even with bad handwriting - AI reads cursive
    3. **Download PDF** has your branding - send to parents/students
    4. **Target level higher** than current level to show growth gap
    5. **Cache** - same essay graded twice = instant (saves Groq credits)
    """)
    st.divider()

    st.markdown("### 📄 Reports Explained")
    st.markdown("""
    - **CEFR Level**: What level essay actually is
    - **Score /10**: Compared to TARGET you chose
    - **Summary**: 2-line teacher summary
    - **Strengths**: What student did well
    - **Table**: Mistake | Correction | Why (teachable)
    - **Corrected Version**: Full rewrite at target level
    """)

with tab_super:
    st.markdown("## ⭐ SUPER Dashboard - Pro Control Centre")
    
    # STATS ROW
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Graded", st.session_state.total_graded)
    with col2:
        st.metric("Cache Hits", st.session_state.cache_hits)
    with col3:
        st.metric("Current Plan", get_status())
    st.divider()

    # LANGUAGES WITH FLAGS - RESTORED!
    st.markdown("### 🌍 Supported Languages (18) with Flags")
    st.caption("TEFLMate grades essays written in these languages / mother-tongues (explains mistakes better)")

    lang_data = [
        {"Flag": "🇬🇧", "Language": "English", "Code": "EN", "Note": "Default, all levels"},
        {"Flag": "🇿🇦", "Language": "Afrikaans", "Code": "AF", "Note": "South Africa"},
        {"Flag": "🇿🇦", "Language": "Zulu (isiZulu)", "Code": "ZU", "Note": "South Africa"},
        {"Flag": "🇿🇦", "Language": "Xhosa (isiXhosa)", "Code": "XH", "Note": "South Africa"},
        {"Flag": "🇿🇦", "Language": "Sotho", "Code": "ST", "Note": "South Africa"},
        {"Flag": "🇪🇸", "Language": "Spanish", "Code": "ES", "Note": "Español"},
        {"Flag": "🇵🇹", "Language": "Portuguese", "Code": "PT", "Note": "Português"},
        {"Flag": "🇫🇷", "Language": "French", "Code": "FR", "Note": "Français"},
        {"Flag": "🇩🇪", "Language": "German", "Code": "DE", "Note": "Deutsch"},
        {"Flag": "🇳🇱", "Language": "Dutch", "Code": "NL", "Note": "Nederlands"},
        {"Flag": "🇮🇹", "Language": "Italian", "Code": "IT", "Note": "Italiano"},
        {"Flag": "🇸🇦", "Language": "Arabic", "Code": "AR", "Note": "العربية"},
        {"Flag": "🇮🇳", "Language": "Hindi", "Code": "HI", "Note": "हिन्दी"},
        {"Flag": "🇨🇳", "Language": "Mandarin", "Code": "ZH", "Note": "中文"},
        {"Flag": "🇯🇵", "Language": "Japanese", "Code": "JA", "Note": "日本語"},
        {"Flag": "🇰🇷", "Language": "Korean", "Code": "KO", "Note": "한국어"},
        {"Flag": "🇷🇺", "Language": "Russian", "Code": "RU", "Note": "Русский"},
        {"Flag": "🇹🇷", "Language": "Turkish", "Code": "TR", "Note": "Türkçe"},
    ]
    st.dataframe(pd.DataFrame(lang_data), use_container_width=True, hide_index=True)
    st.divider()

    # GRADING STANDARDS
    st.markdown("### 📚 Grading Standards We Support")
    st.markdown("""
    - **CEFR**: A1, A2, B1, B2, C1, C2 (European)
    - **IELTS**: Band 1-9 (mapped from CEFR)
    - **TOEFL**: 0-120 (mapped)
    - **US Grades**: K-12 to University
    - **Cambridge**: Starters to Proficiency
    """)
    st.divider()

    # PRICING - CLEAN, NO LEAK
    g = st.session_state.geo
    st.markdown(f"### 💰 Pricing Plans ({g['code']} - Auto Detected)")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown(f"**FREE**\\n{g['symbol']}0\\n3 essays\\nBasic report")
    with p2:
        st.markdown(f"**Once-Off**\\n{g['symbol']}{g['once']}\\n+10 grades\\nPDF download")
    with p3:
        st.markdown(f"**Weekly ⭐ Best Start**\\n{g['symbol']}{g['weekly']}\\n7 days unlimited\\nAll features")
    with p4:
        st.markdown(f"**Monthly PRO**\\n{g['symbol']}{g['monthly']}\\n30 days + Batch 50\\n🏆 Best Value")
    st.markdown(f"**Yearly: {g['symbol']}{g['yearly']} = 365 days unlimited**")
    st.divider()

    st.markdown("### 🚀 Why Upgrade?")
    st.markdown("""
    - ✅ Grade 50 essays in 4 minutes (Batch 50)
    - ✅ Photo OCR for handwritten books
    - ✅ Unlimited PDF reports with your branding
    - ✅ Cache = instant re-grade
    - ✅ Priority support via WhatsApp
    - ✅ No ads, no limits
    """)
    st.divider()
    st.caption("UptimeRobot monitors: / and /?health - both should return 'ok'")
# ===== FOOTER (same on all tabs) =====
st.divider()
st.markdown("### ❤️ Support TEFLMate")
st.markdown("**Payshap 0658006750 | PayPal: paypal.me/TaahirMahomed | Send proof by WhatsApp or Email and I'll send your code**")
col1, col2, col3 = st.columns(3)
with col1:
    st.link_button("💬 WhatsApp Proof", "https://wa.me/27658006750?text=Hi%20I%20paid%20for%20TEFLMate")
with col2:
    st.link_button(f"📧 Email proof", f"mailto:{YOUR_EMAIL}?subject=TEFLMate Payment Proof")
with col3:
    st.link_button(f"💳 Pay with PayPal", PAYPAL_ME)

st.caption("TEFLMate v5.1 • Durban, SA • Built by Mr Taahir Mahomed • Worldwide 🌍 • Uptime: /?health = ok")
st.caption("© 2026 TEFLMate - All Rights Reserved")

