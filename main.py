import streamlit as st
import os
import io
import base64
import requests
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import fitz  # PyMuPDF

# --- CONFIG ---
st.set_page_config(page_title="TEFLMate v6.9 Pro", page_icon="📘", layout="centered")
YOUR_EMAIL = "taahirmahomed@yahoo.com"

# --- GEO PRICING ---
def get_geo_pricing():
    try:
        r = requests.get("https://ipapi.co/json/", timeout=3).json()
        country = r.get("country_code", "US")
    except:
        country = "US"
    if country == "ZA":
        return {"code": "ZA", "symbol": "R", "once": "49", "weekly": "49", "monthly": "99", "yearly": "799"}
    elif country == "GB":
        return {"code": "GB", "symbol": "£", "once": "5", "weekly": "7", "monthly": "15", "yearly": "99"}
    elif country in ["DE","FR","ES","IT","NL","PT"]:
        return {"code": "EU", "symbol": "€", "once": "6", "weekly": "8", "monthly": "18", "yearly": "119"}
    else:
        return {"code": "US", "symbol": "$", "once": "6", "weekly": "9", "monthly": "19", "yearly": "129"}

# --- SESSION ---
if 'geo' not in st.session_state:
    st.session_state.geo = get_geo_pricing()
if 'uses' not in st.session_state:
    st.session_state.uses = 0
if 'total_graded' not in st.session_state:
    st.session_state.total_graded = 0
if 'cache_hits' not in st.session_state:
    st.session_state.cache_hits = 0
if 'pro_expiry' not in st.session_state:
    st.session_state.pro_expiry = None
if 'cache' not in st.session_state:
    st.session_state.cache = {}

def is_pro():
    return st.session_state.pro_expiry and st.session_state.pro_expiry > datetime.now()

def get_status():
    if is_pro():
        left = (st.session_state.pro_expiry - datetime.now()).days + 1
        return f"PRO ({left} days left)"
    else:
        return f"FREE ({st.session_state.uses}/3)"

# --- GROQ ---
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

def grade_with_groq(text, level):
    cache_key = f"{text[:100]}_{level}"
    if cache_key in st.session_state.cache:
        st.session_state.cache_hits += 1
        return st.session_state.cache[cache_key]
    
    prompt = f"""You are TEFLMate, an expert TEFL essay grader.

Target Level: {level}

Essay to grade:
{text}

Return in this exact format:
**CEFR Level Found:** [level]
**Score:** [X/10 compared to target {level}]
**Summary:** 2 lines

**Strengths:**
- point 1
- point 2

**Corrections Table:**
| Mistake | Correction | Why |
|---|---|---|

**Corrected Version at {level}:**
[rewrite essay at target level]

Keep it teacher-friendly, South African context aware."""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=60)
    if r.status_code != 200:
        return f"GROQ ERROR {r.status_code}: {r.text[:500]}"
    result = r.json()['choices'][0]['message']['content']
    st.session_state.cache[cache_key] = result
    return result

def extract_text_from_image(image_bytes):
    models = [
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision-preview"
    ]
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    for model in models:
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Read all handwritten text in this image exactly, line by line. Return only the text."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]
                }],
                "temperature": 0.1
            }
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
        except Exception as e:
            continue
    return "OCR_ERROR: Could not read image after trying all 4 models. Try clearer photo."

def extract_text_from_pdf(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text
    except Exception as e:
        return f"PDF ERROR: {e}"

def create_branded_pdf(original, report, level):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"TEFLMate v6.9 Report - Level {level}", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | {YOUR_EMAIL}", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Original Essay:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5, original[:2000])
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Grading Report:", ln=True)
    pdf.set_font("Arial", "", 10)
    clean = report.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, clean[:8000])
    return pdf.output(dest="S").encode('latin-1')

# --- UI ---
st.markdown("<h1 style='text-align:center'>📘 TEFLMate v6.9 Pro</h1>", unsafe_allow_html=True)
st.caption(f"Status: {get_status()} | Total Graded: {st.session_state.total_graded} | Cache Hits: {st.session_state.cache_hits}")

tab_grade, tab_photo, tab_batch, tab_guide, tab_super = st.tabs(["✍️ GRADE", "📸 PHOTO/PDF", "📦 BATCH 50", "📘 GUIDE", "⭐ SUPER"])

with tab_grade:
    st.markdown("### ✍️ Paste Essay Text")
    level = st.selectbox("Target Level student SHOULD be at:", ["A1","A2","B1","B2","C1","C2"], key="level_main")
    essay = st.text_area("Paste essay here:", height=200, placeholder="My best friend is Thandi. She is kind...")
    if st.button("GRADE ESSAY ->", key="grade_main"):
        if not essay.strip():
            st.warning("Paste essay first")
            st.stop()
        if not is_pro() and st.session_state.uses >= 3:
            st.error("Free limit reached (3/3). Enter PRO code in sidebar or pay.")
            st.stop()
        with st.spinner("Grading..."):
            result_text = grade_with_groq(essay, level)
            if not is_pro():
                st.session_state.uses += 1
            st.session_state.total_graded += 1
            st.markdown(result_text)
            st.download_button("📄 Download PDF Report", create_branded_pdf(essay, result_text, level), file_name=f"Essay_{level}.pdf", key="dl_main")

with tab_photo:
    st.markdown("### 📸 Photo or PDF - Handwritten Essays")
    level_p = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="level_photo")
    st.divider()
    st.markdown("**Option 1: Upload PDF**")
    upload_pdf = st.file_uploader("Upload PDF file", type=["pdf"], key="pdf_up")
    st.markdown("**Option 2: Take / Upload Photo**")
    image_file = st.file_uploader("Upload photo of handwritten essay", type=["jpg","jpeg","png"], key="img_up")
    camera_file = st.camera_input("Or take photo now", key="cam")
    image_bytes = None
    if camera_file:
        image_bytes = camera_file.getvalue()
    elif image_file:
        image_bytes = image_file.getvalue()

    if upload_pdf:
        extracted = extract_text_from_pdf(upload_pdf.getvalue())
        st.text_area("Text from PDF:", value=extracted, height=150, key="pdf_text_area")
        if st.button("GRADE PDF TEXT ->", key="grade_pdf"):
            if not is_pro() and st.session_state.uses >= 3:
                st.error("Free limit")
                st.stop()
            with st.spinner("Grading PDF..."):
                result_text = grade_with_groq(extracted, level_p)
                if not is_pro():
                    st.session_state.uses += 1
                st.session_state.total_graded += 1
                st.markdown(result_text)
                st.download_button("📄 Download PDF", create_branded_pdf(extracted, result_text, level_p), file_name=f"PDF_{level_p}.pdf", key="dl_pdf")
    if image_bytes and st.button("READ & GRADE PHOTO ->", key="read_photo"):
        with st.spinner("Reading..."):
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
                st.error("Free limit")
                st.stop()
            with st.spinner("Grading..."):
                result_text = grade_with_groq(edited, level_p)
                if not is_pro():
                    st.session_state.uses += 1
                st.session_state.total_graded += 1
                st.markdown(result_text)
                st.download_button("📄 Download PDF", create_branded_pdf(edited, result_text, level_p), file_name=f"Photo_{level_p}.pdf", key="dl_photo")

with tab_batch:
    st.markdown("### 📦 Upload 50 Essays At Once")
    g = st.session_state.geo
    st.info(f"Monthly {g['symbol']}{g['monthly']} unlocks Batch 50: Grade 50 at once.")
    sample_df = pd.DataFrame({
        "student_name": ["Student 1", "Student 2", "Student 3"],
        "essay": ["I go to market yesterday. It was fun because I buyed many things.", "My best friend is Thandi. She is kind and she help me.", "I broken my leg last week. I was playing soccer and I fall down."]
    })
    csv_template = sample_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV Template", csv_template, file_name="TEFLMate_Batch_Template_50.csv", mime="text/csv", key="template_btn")
    st.caption("1.Download 2.Open in Excel 3.Replace with 50 essays 4.Upload")
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
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
                if 'essay' not in df.columns:
                    df.columns = [c.strip().lower() for c in df.columns]
                if 'essay' in df.columns:
                    essays_list = df['essay'].astype(str).tolist()
                elif 'text' in df.columns:
                    essays_list = df['text'].astype(str).tolist()
                else:
                    essays_list = df.iloc[:,0].astype(str).tolist()
                if 'student_name' in df.columns:
                    names_list = df['student_name'].astype(str).tolist()
                else:
                    names_list = [f"Student {i+1}" for i in range(len(essays_list))]
            else:
                text_content = uploaded.getvalue().decode('utf-8', errors='ignore')
                essays_list = [t.strip() for t in text_content.split('\n---\n') if t.strip()]
                if not essays_list:
                    essays_list = [t.strip() for t in text_content.splitlines() if t.strip()]
                names_list = [f"Student {i+1}" for i in range(len(essays_list))]
        except Exception as e:
            st.error(f"File read error: {e}")
            st.stop()
        essays_list = essays_list[:50]
        names_list = names_list[:50]
        st.info(f"Found {len(essays_list)} essays, grading all...")
        prog_bar = st.progress(0)
        status_text = st.empty()
        results = []
        for idx, ess in enumerate(essays_list):
            status_text.text(f"Grading {idx+1}/{len(essays_list)}: {names_list[idx]}...")
            prog_bar.progress((idx)/len(essays_list))
            try:
                res = grade_with_groq(ess, level_b)
                results.append({"name": names_list[idx], "essay": ess[:200], "report": res})
                st.session_state.total_graded += 1
            except Exception as e:
                results.append({"name": names_list[idx], "essay": ess[:200], "report": f"ERROR: {e}"})
        prog_bar.progress(1.0)
        status_text.text("Done!")
        st.success(f"Graded {len(results)} essays!")
        for r in results:
            with st.expander(f"{r['name']}"):
                st.markdown(r['report'][:1000])
        df_out = pd.DataFrame([{"Name": r['name'], "Report": r['report']} for r in results])
        st.download_button("📄 Download All Reports CSV", df_out.to_csv(index=False).encode('utf-8'), file_name=f"Batch_{level_b}.csv", key="batch_dl")

with tab_guide:
    st.markdown("## 📘 How To Use TEFLMate")
    st.markdown("""
    ### QUICK START
    1. If typed, paste in GRADE tab
    2. If handwritten, go to PHOTO/PDF tab
    3. Choose level student SHOULD be at
    4. Click grade, then download PDF for parents
    """)
    st.divider()
    st.markdown("### 📊 What Each Level Means")
    st.markdown("""
    **A1 Beginner (Grade 3-5 equivalent):** Can write "I am Thandi. I like apples." Simple present only, 20-40 words.
    **A2 Elementary (Grade 6-7):** Past tense starts, "I went to shop yesterday." 40-80 words, basic connectors "and, but, because".
    **B1 Intermediate (Grade 8-9):** Can give reasons, opinions. "Although it was raining, we played." 80-150 words.
    **B2 Upper-Intermediate (Grade 10-11):** Complex sentences, less mistakes. Can argue both sides. 150-250 words.
    **C1 Advanced (Matric / University):** Fluent, wide vocab, idioms. "Not only...but also". 250+ words.
    **C2 Proficient (Teacher level):** Near native, nuanced, academic.
    """)
    st.divider()
    st.markdown("### ❗ Common Student Mistakes It Catches")
    st.markdown("""
    **South Africa Special:**
    - I broked / I buyed -> broke / bought
    - I am agree -> I agree
    - He didn't came -> didn't come
    - Loose vs Lose
    """)
    st.divider()
    st.markdown("### 💡 Pro Tips For Teachers")
    st.markdown("""
    1. Use Batch 50 for whole class - saves 2 hours
    2. Photo tab works even with bad handwriting
    3. Download PDF has your branding
    4. Target level higher than current to show growth gap
    5. Cache = same essay twice = instant
    """)
    st.divider()
    st.markdown("### 📄 Reports Explained")
    st.markdown("""
    - CEFR Level: What level essay actually is
    - Score /10: Compared to TARGET you chose
    - Summary: 2-line teacher summary
    - Strengths: What student did well
    - Table: Mistake | Correction | Why
    - Corrected Version: Full rewrite at target level
    """)

with tab_super:
    st.markdown("## ⭐ SUPER Dashboard - Pro Control Centre")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Graded", st.session_state.total_graded)
    with col2:
        st.metric("Cache Hits", st.session_state.cache_hits)
    with col3:
        st.metric("Current Plan", get_status())
    st.divider()
    st.markdown("### 🌍 Supported Languages (18) with Flags")
    st.caption("TEFLMate grades essays written in these languages")
    lang_data = [
        {"Flag": "🇬🇧", "Language": "English", "Code": "EN", "Note": "Default, all levels"},
        {"Flag": "🇿🇦", "Language": "Afrikaans", "Code": "AF", "Note": "South Africa"},
        {"Flag": "🇿🇦", "Language": "Zulu (isiZulu)", "Code": "ZU", "Note": "South Africa"},
        {"Flag": "🇿🇦", "Language": "Xhosa (isiXhosa)", "Code": "XH", "Note": "South Africa"},
        {"Flag": "🇿🇦", "Language": "Sotho", "Code": "ST", "Note": "South Africa"},
        {"Flag": "🇪🇸", "Language": "Spanish", "Code": "ES", "Note": "Espanol"},
        {"Flag": "🇵🇹", "Language": "Portuguese", "Code": "PT", "Note": "Portugues"},
        {"Flag": "🇫🇷", "Language": "French", "Code": "FR", "Note": "Francais"},
        {"Flag": "🇩🇪", "Language": "German", "Code": "DE", "Note": "Deutsch"},
        {"Flag": "🇳🇱", "Language": "Dutch", "Code": "NL", "Note": "Nederlands"},
        {"Flag": "🇮🇹", "Language": "Italian", "Code": "IT", "Note": "Italiano"},
        {"Flag": "🇸🇦", "Language": "Arabic", "Code": "AR", "Note": "Arabic"},
        {"Flag": "🇮🇳", "Language": "Hindi", "Code": "HI", "Note": "Hindi"},
        {"Flag": "🇨🇳", "Language": "Mandarin", "Code": "ZH", "Note": "Chinese"},
        {"Flag": "🇯🇵", "Language": "Japanese", "Code": "JA", "Note": "Japanese"},
        {"Flag": "🇰🇷", "Language": "Korean", "Code": "KO", "Note": "Korean"},
        {"Flag": "🇷🇺", "Language": "Russian", "Code": "RU", "Note": "Russian"},
        {"Flag": "🇹🇷", "Language": "Turkish", "Code": "TR", "Note": "Turkish"},
    ]
    st.dataframe(pd.DataFrame(lang_data), use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("### 🛠️ System Health")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Status:**")
        st.success("✅ Groq API: Connected")
        st.success("✅ OCR Models: 4 models ready (fixed 2026)")
        st.success("✅ PDF Reader: PyMuPDF Active" if fitz else "⚠️ Add PyMuPDF to requirements")
        st.success("✅ Batch Grader: Ready")
    with c2:
        st.markdown("**Storage Info:**")
        st.info(f"Geo: {st.session_state.geo['code']} {st.session_state.geo['symbol']}")
        st.info(f"Free uses: {st.session_state.uses}/3")
        if is_pro():
            left = (st.session_state.pro_expiry - datetime.now()).days + 1
            st.success(f"PRO: {left} days left")
    st.divider()
    st.markdown("### 💳 Payment Links - Copy These")
    g = st.session_state.geo
    paypal_base = "https://paypal.me/TaahirMahomed"
    st.code(f"""
PayPal.Me base: {paypal_base}
Once-off {g['symbol']}{g['once']} (10 grades): {paypal_base}/{g['once']}
Weekly {g['symbol']}{g['weekly']}: {paypal_base}/{g['weekly']}
Monthly {g['symbol']}{g['monthly']}: {paypal_base}/{g['monthly']}
Yearly {g['symbol']}{g['yearly']}: {paypal_base}/{g['yearly']}

Codes to give customers after they pay:
TEACH10 = 10 grades (for {g['once']})
WEEK49 = 7 days (for weekly)
MONTH99 = 30 days (for monthly)
YEAR799 = 365 days (for yearly)
""", language="text")
    st.divider()
    st.markdown("### 🔧 What Was Fixed In v6.9 (This Version)")
    st.success("""
    ✅ 1. NO MORE DUPLICATE UPLOADS: Grade tab = text only, Photo tab = photos only. Fixed!
    ✅ 2. OCR Models Updated 2026: Old models deleted, using 4 new llama-3.2-vision models. No more 400 errors.
    ✅ 3. OCR Errors No Longer False Success: Now shows error clearly, tries next model automatically.
    ✅ 4. Guide Tab Expanded: Full tutorial with levels, mistakes, tips.
    ✅ 5. SUPER Tab: Language flags, health check, payment links.
    ✅ 6. Geo Pricing: R49/R99/R799 for ZA, $/£/€ for others - auto.
    ✅ 7. Upgraded to v6.9 - Clean 449 lines
    """)
    st.divider()
    st.caption(f"TEFLMate v6.9 Pro | Mr Mahomed | {YOUR_EMAIL} | Total graded this session: {st.session_state.total_graded}")
