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

YOUR_EMAIL = "taahir532@gmail.com"
PAYPAL_ME = "https://paypal.me/TaahirMahomed"
st.set_page_config(page_title="TEFLMate v5.1 Pro", page_icon="📝", layout="centered")
st.markdown("""<style>.stButton>button {background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;}</style>""", unsafe_allow_html=True)

if "uses" not in st.session_state:
    st.session_state.uses = 0
if "pro_expiry" not in st.session_state:
    st.session_state.pro_expiry = None
if "pay_links" not in st.session_state:
    st.session_state.pay_links = {}
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

def init_paystack(email, amount_kobo, plan_code):
    try:
        secret = st.secrets["PAYSTACK_SECRET_KEY"]
        callback = st.secrets.get("PAYSTACK_CALLBACK_URL", "https://essay-grader-3a1bxqeqdfpdh9huwezx57.streamlit.app")
        url = "https://api.paystack.co/transaction/initialize"
        headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
        data = {
            "email": email,
            "amount": int(amount_kobo),
            "callback_url": callback,
            "metadata": {"plan": plan_code}
        }
        r = requests.post(url, json=data, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"status": False, "message": str(e)}

def verify_paystack(reference):
    try:
        secret = st.secrets["PAYSTACK_SECRET_KEY"]
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {secret}"}
        r = requests.get(url, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"status": False, "message": str(e)}

def extract_text_from_image(image_bytes):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    try:
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user","content": [
                {"type": "text", "text": "OCR: Extract handwritten text EXACTLY as written, keep mistakes. Return only text."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]}]
        )
        txt = res.choices[0].message.content
        if "</think>" in txt:
            txt = txt.split("</think>")[-1].strip()
        return txt.strip()
    except Exception as e:
        return f"OCR_ERROR: {e}"

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
    prompt = f"You are Cambridge TEFL examiner for {level}. Grade: {essay_text}. ASCII only. Include CEFR Level, Score/10 vs Target {level}, Summary, 2 Strengths, Table Mistake|Correction|Why, Then corrected version."
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}])
    return res.choices[0].message.content

query_params = st.query_params
if "reference" in query_params:
    ref = query_params["reference"]
    verify = verify_paystack(ref)
    if verify.get("status") and verify.get("data", {}).get("status") == "success":
        data = verify["data"]
        amount = data.get("amount", 0)
        plan = data.get("metadata", {}).get("plan", "")
        now = datetime.now()
        if amount == 1000 or plan == "ONCE10":
            st.session_state.uses = max(0, st.session_state.uses - 10)
            st.success("R10 received! +10 grades added ✅")
            st.balloons()
        elif amount == 4900 or plan == "WEEK49":
            st.session_state.pro_expiry = now + timedelta(days=7)
            st.success("R49 Weekly PRO activated - 7 days ✅")
            st.balloons()
        elif amount == 9900 or plan == "MONTH99":
            st.session_state.pro_expiry = now + timedelta(days=30)
            st.success("R99 Monthly PRO activated - 30 days + Batch 50 ✅")
            st.balloons()
        elif amount == 79900 or plan == "YEAR799":
            st.session_state.pro_expiry = now + timedelta(days=365)
            st.success("R799 Yearly PRO activated - 365 days ✅")
            st.balloons()
        st.query_params.clear()

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
    st.caption("Batch 50 = Upload CSV and grade 50 essays at once.")
    st.markdown(f"- Yearly: {g['symbol']}{g['yearly']} = 365 days")
    st.divider()
    if g['code'] == "ZAR":
        st.markdown("#### 🇿🇦 Pay with Card / EFT (Instant)")
        email_for_pay = st.text_input("Email for receipt:", value=YOUR_EMAIL, key="paystack_email")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if st.button(f"Once R{g['once']}", key="pay_once"):
                res = init_paystack(email_for_pay, 1000, "ONCE10")
                if res.get("status"):
                    st.session_state.pay_links["ONCE10"] = res["data"]["authorization_url"]
                else:
                    st.error(f"Paystack error: {res.get('message')}")
            if "ONCE10" in st.session_state.pay_links:
                st.link_button("Pay R10 Now →", st.session_state.pay_links["ONCE10"])
            if st.button(f"Monthly R{g['monthly']} ⭐", key="pay_month"):
                res = init_paystack(email_for_pay, 9900, "MONTH99")
                if res.get("status"):
                    st.session_state.pay_links["MONTH99"] = res["data"]["authorization_url"]
                else:
                    st.error(f"Paystack error: {res.get('message')}")
            if "MONTH99" in st.session_state.pay_links:
                st.link_button("Pay R99 Now →", st.session_state.pay_links["MONTH99"])
        with col_p2:
            if st.button(f"Weekly R{g['weekly']}", key="pay_week"):
                res = init_paystack(email_for_pay, 4900, "WEEK49")
                if res.get("status"):
                    st.session_state.pay_links["WEEK49"] = res["data"]["authorization_url"]
                else:
                    st.error(f"Paystack error: {res.get('message')}")
            if "WEEK49" in st.session_state.pay_links:
                st.link_button("Pay R49 Now →", st.session_state.pay_links["WEEK49"])
            if st.button(f"Yearly R{g['yearly']}", key="pay_year"):
                res = init_paystack(email_for_pay, 79900, "YEAR799")
                if res.get("status"):
                    st.session_state.pay_links["YEAR799"] = res["data"]["authorization_url"]
                else:
                    st.error(f"Paystack error: {res.get('message')}")
            if "YEAR799" in st.session_state.pay_links:
                st.link_button("Pay R799 Now →", st.session_state.pay_links["YEAR799"])
        st.caption("Card / EFT / Capitec Pay - Auto unlock")
        st.divider()
    st.markdown("#### 🌍 Pay Globally")
    st.link_button(f"💳 Pay with PayPal", PAYPAL_ME)
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

tab1, tab2, tab3, tab4 = st.tabs(["Single Essay", "Batch 50 (PRO)", "📸 Photo / PDF NEW", "📘 Target Levels Guide"])
with tab1:
    essay = st.text_area("Paste Student Essay:", height=180, placeholder="I broken my leg")
    level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level")
    if st.button("GRADE ESSAY ->"):
        if not is_pro() and st.session_state.uses >= 3:
            st.error("Free limit reached - Pay via Paystack in sidebar")
            st.stop()
        with st.spinner("Grading..."):
            result_text = grade_with_groq(essay, level)
            if not is_pro(): st.session_state.uses += 1
            st.markdown(result_text)
            st.download_button("📄 Download PDF", create_branded_pdf(essay, result_text, level), file_name=f"Report_{level}.pdf")
with tab2:
    st.markdown("### Upload 50 Essays At Once")
    st.info(f"Monthly {g['symbol']}{g['monthly']} unlocks this")
    sample_df = pd.DataFrame({
        "student_name": ["Student 1", "Student 2", "Student 3"],
        "essay": ["I go to market yesterday.", "My best friend is Thandi.", "I broken my leg last week."]
    })
    csv_template = sample_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV Template", csv_template, file_name="TEFLMate_Batch_Template_50.csv", mime="text/csv", key="template_btn")
    level_b = st.selectbox("Target Level for batch:", ["A1","A2","B1","B2","C1","C2"], key="batch_level")
    uploaded = st.file_uploader("Upload your filled CSV or TXT", type=["csv","txt"], key="batch_file")
    if st.button("GRADE BATCH 50 ->"):
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
        results = []; progress = st.progress(0)
        for i, es in enumerate(essays):
            results.append({"Essay": es[:100], "Result": grade_with_groq(es[:2000], level_b)})
            progress.progress((i+1)/len(essays))
        st.success(f"Done! {len(results)} graded")
        st.dataframe(pd.DataFrame(results))
        pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15)
        for idx, r in enumerate(results):
            pdf.add_page(); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, f"Essay {idx+1}", ln=True)
            pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 6, clean(r["Result"]))
        st.download_button("📄 Download All 50 Reports PDF", pdf.output(dest='S').encode('latin-1'), file_name="Batch_50.pdf")
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
    if camera_pic: image_bytes = camera_pic.getvalue()
    elif upload_img: image_bytes = upload_img.getvalue()
    if image_bytes: st.image(image_bytes, use_container_width=True)
    if upload_pdf:
        extracted = extract_text_from_pdf(upload_pdf.getvalue())
        st.text_area("Text from PDF:", value=extracted, height=150, key="pdf_text_area")
        if st.button("GRADE PDF TEXT ->"):
            result_text = grade_with_groq(extracted, level_p)
            if not is_pro(): st.session_state.uses += 1
            st.markdown(result_text)
            st.download_button("📄 Download PDF", create_branded_pdf(extracted, result_text, level_p), file_name=f"PDF_{level_p}.pdf")
    if image_bytes and st.button("READ & GRADE PHOTO ->"):
        with st.spinner("Reading..."):
            extracted = extract_text_from_image(image_bytes)
            if "OCR_ERROR" in extracted: st.error(extracted)
            else: st.session_state['last_ocr'] = extracted; st.rerun()
    if 'last_ocr' in st.session_state:
        edited = st.text_area("We read — edit if needed:", value=st.session_state['last_ocr'], height=150)
        if st.button("GRADE THIS TEXT ->"):
            result_text = grade_with_groq(edited, level_p)
            if not is_pro(): st.session_state.uses += 1
            st.markdown(result_text)
            st.download_button("📄 Download PDF", create_branded_pdf(edited, result_text, level_p), file_name=f"Photo_{level_p}.pdf")
with tab4:
    st.markdown("## 📘 How Target Levels Work")
    st.info("Target Level = The level you WANT them to reach.")
    st.table(pd.DataFrame([
        {"Level": "A1", "Class": "Grade 1-3", "Words": "20-40", "Use For": "ABET"},
        {"Level": "A2", "Class": "Grade 4-6", "Words": "50-80", "Use For": "Primary"},
        {"Level": "B1", "Class": "Grade 7-9", "Words": "120-150", "Use For": "High school"},
        {"Level": "B2", "Class": "Matric", "Words": "180-250", "Use For": "Matric, College"},
        {"Level": "C1", "Class": "University", "Words": "250-300", "Use For": "University, Work"},
        {"Level": "C2", "Class": "Mastery", "Words": "300+", "Use For": "Teachers"},
    ]))
st.divider()
st.markdown("### ❤️ Payshap 0658006750 | PayPal: paypal.me/TaahirMahomed")
col1, col2, col3 = st.columns(3)
with col1:
    st.link_button("💬 WhatsApp Proof", "https://wa.me/27658006750?text=Hi%20I%20paid%20for%20TEFLMate")
with col2:
    st.link_button(f"📧 Email proof", f"mailto:{YOUR_EMAIL}?subject=TEFLMate Payment Proof")
with col3:
    st.link_button(f"💳 Pay with PayPal", PAYPAL_ME)
st.caption("TEFLMate v5.1 • Durban, SA • Built by Mr Taahir Mahomed • Worldwide 🌍")
