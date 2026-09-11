import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
from fpdf import FPDF
import unicodedata
import pandas as pd
import base64
import requests
import re
from io import BytesIO
try:
    import fitz
except ImportError:
    fitz = None

YOUR_EMAIL = "taahir532@gmail.com"
PAYPAL_ME = "https://paypal.me/TaahirMahomed"
st.set_page_config(page_title="TEFLMate v6.0.1 Pro - Phase 2", page_icon="📝", layout="centered")
st.markdown("""<style>.stButton>button {background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;} div[data-testid="stLinkButton"]>a{background:#111!important;color:white!important;border-radius:10px!important;height:45px!important;font-weight:bold!important;width:100%!important;display:flex!important;align-items:center!important;justify-content:center!important;}</style>""", unsafe_allow_html=True)

if "uses" not in st.session_state:
    st.session_state.uses = 0
if "pro_expiry" not in st.session_state:
    st.session_state.pro_expiry = None
if "active_plan" not in st.session_state:
    st.session_state.active_plan = None
if "pay_links" not in st.session_state:
    st.session_state.pay_links = {}
if "pay_refs" not in st.session_state:
    st.session_state.pay_refs = {}
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
        days = (st.session_state.pro_expiry - datetime.now()).days + 1
        plan = st.session_state.active_plan
        if plan == "WEEK49":
            return f"✅ R49 Weekly ACTIVE - {days} days left - Unlimited + Batch 50"
        elif plan == "MONTH99":
            return f"✅ R99 Monthly ACTIVE - {days} days left - Unlimited + Batch 50"
        elif plan == "YEAR799":
            return f"✅ R799 Yearly ACTIVE - {days} days left - Unlimited + Batch 50"
        else:
            return f"PRO ACTIVE - {days} days left - Unlimited + Batch 50"
    else:
        remaining = 3 - st.session_state.uses
        if remaining <= 0:
            return f"❌ FREE - 0 left (Pay to continue)"
        if st.session_state.active_plan == "ONCE10" and remaining > 3:
            return f"✅ R10 Active - {remaining} essays left (Once-off R10 - No Batch)"
        return f"FREE - {remaining} left"

def clean(text):
    return unicodedata.normalize('NFKD', text or "").encode('ascii', 'ignore').decode('ascii')

def extract_score_cefr(text):
    try:
        score_match = re.search(r'(\d+)\s*/\s*10', text)
        score = int(score_match.group(1)) if score_match else 0
        cefr_match = re.search(r'\b(A1|A2|B1|B2|C1|C2)\b', text)
        cefr = cefr_match.group(1) if cefr_match else "N/A"
        return score, cefr
    except:
        return 0, "N/A"

def init_paystack(email, amount_kobo, plan_code):
    try:
        secret = st.secrets["PAYSTACK_SECRET_KEY"]
        headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
        data = {"email": email, "amount": int(amount_kobo), "metadata": {"plan": plan_code}}
        r = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"status": False, "message": str(e)}

def verify_paystack(ref):
    try:
        secret = st.secrets["PAYSTACK_SECRET_KEY"]
        r = requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers={"Authorization": f"Bearer {secret}"}, timeout=10)
        return r.json()
    except Exception as e:
        return {"status": False, "message": str(e)}

def unlock_paystack(v):
    if not v.get("status"): return False
    d=v.get("data",{})
    if d.get("status")!="success": return False
    amt=d.get("amount",0); plan=d.get("metadata",{}).get("plan",""); now=datetime.now()
    if amt==1000 or plan=="ONCE10":
        st.session_state.uses -= 10; st.session_state.active_plan = "ONCE10"
        st.success(f"R10 received! You now have {3 - st.session_state.uses} essays left ✅"); st.balloons(); return True
    elif amt==4900 or plan=="WEEK49":
        st.session_state.pro_expiry=now+timedelta(days=7); st.session_state.active_plan="WEEK49"
        st.success("R49 Weekly PRO - 7 days + Batch 50 ✅"); st.balloons(); return True
    elif amt==9900 or plan=="MONTH99":
        st.session_state.pro_expiry=now+timedelta(days=30); st.session_state.active_plan="MONTH99"
        st.success("R99 Monthly PRO - 30 days + Batch 50 ✅"); st.balloons(); return True
    elif amt==79900 or plan=="YEAR799":
        st.session_state.pro_expiry=now+timedelta(days=365); st.session_state.active_plan="YEAR799"
        st.success("R799 Yearly PRO - 365 days + Batch 50 ✅"); st.balloons(); return True
    return False

def verify_all_refs():
    for ref in list(st.session_state.pay_refs.values()):
        v = verify_paystack(ref)
        if v.get("status") and v.get("data",{}).get("status")=="success":
            if unlock_paystack(v):
                st.session_state.pay_refs = {}; st.session_state.pay_links = {}; st.query_params.clear()
                return True
    return False

q=st.query_params
if "reference" in q:
    if unlock_paystack(verify_paystack(q["reference"])):
        st.query_params.clear(); st.session_state.pay_refs = {}; st.session_state.pay_links = {}
else:
    if st.session_state.pay_refs:
        verify_all_refs()

def extract_text_from_image(image_bytes):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    try:
        res = client.chat.completions.create(model="qwen/qwen3.6-27b", messages=[{"role": "user","content": [{"type": "text", "text": "OCR: Extract handwritten text EXACTLY as written, keep mistakes. Return only text."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
        txt = res.choices[0].message.content
        if "</think>" in txt: txt = txt.split("</think>")[-1].strip()
        return txt.strip()
    except Exception as e:
        return f"OCR_ERROR: {e}"

def extract_text_from_pdf(pdf_bytes):
    if not fitz: return "Add PyMuPDF to requirements.txt"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join([p.get_text() for p in doc[:3]])
        if len(text.strip()) < 30 and len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=200)
            text = extract_text_from_image(pix.tobytes("jpeg"))
        return text
    except Exception as e:
        return f"PDF_ERROR: {e}"

def create_branded_pdf(original_essay, ai_result, target_level, student_name="Student"):
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
    pdf.cell(0, 7, f"Student: {student_name} | Level: {target_level} | Date: {datetime.now().strftime('%d %b %Y')}", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, clean(ai_result))
    return pdf.output(dest='S').encode('latin-1')

def grade_with_groq(essay_text, level):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    prompt = f"You are Cambridge TEFL examiner for {level}. Grade: {essay_text}. ASCII only. Include CEFR Level, Score/10 vs Target {level}, Summary, 2 Strengths, Table Mistake|Correction|Why, Then corrected version."
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}])
    return res.choices[0].message.content

st.title("📝 TEFLMate v6.0.1 - Phase 2 Classroom")
st.caption(f"Grade 50 essays in 4 minutes • Class Reports + Excel • Pricing in {st.session_state.geo['code']}")

with st.sidebar:
    st.markdown("### 🔑 Your Plan")
    st.info(get_status())
    if is_pro() or (st.session_state.active_plan == "ONCE10"):
        with st.expander("📦 Your Active Package Details", expanded=True):
            if st.session_state.active_plan == "ONCE10":
                st.write(f"**Amount:** R10 Once-off"); st.write(f"**Essays:** {3 - st.session_state.uses} left"); st.write(f"**Days:** No expiry"); st.write(f"**Batch 50:** ❌ No")
            elif st.session_state.active_plan == "WEEK49":
                days = (st.session_state.pro_expiry - datetime.now()).days + 1
                st.write(f"**Amount:** R49 Weekly"); st.write(f"**Essays:** Unlimited"); st.write(f"**Days:** {days} days left"); st.write(f"**Batch 50:** ✅ Yes")
            elif st.session_state.active_plan == "MONTH99":
                days = (st.session_state.pro_expiry - datetime.now()).days + 1
                st.write(f"**Amount:** R99 Monthly"); st.write(f"**Essays:** Unlimited"); st.write(f"**Days:** {days} days left"); st.write(f"**Batch 50:** ✅ Yes")
            elif st.session_state.active_plan == "YEAR799":
                days = (st.session_state.pro_expiry - datetime.now()).days + 1
                st.write(f"**Amount:** R799 Yearly"); st.write(f"**Essays:** Unlimited"); st.write(f"**Days:** {days} days left"); st.write(f"**Batch 50:** ✅ Yes")
    g = st.session_state.geo
    if g['code'] == "ZAR":
        st.markdown(f"#### 💰 1-Click Pay ({g['code']})")
        st.caption("1. Tap a button below 2. Pay on Paystack 3. Return here 4. Tap Check Payment to unlock")
        email = st.text_input("Email for receipt:", value=YOUR_EMAIL, key="pay_email_v51")
        if not st.session_state.pay_links and email:
            with st.spinner("Loading pay options..."):
                for plan, amt in [("ONCE10",1000),("WEEK49",4900),("MONTH99",9900),("YEAR799",79900)]:
                    res = init_paystack(email, amt, plan)
                    if res.get("status"):
                        st.session_state.pay_links[plan] = res["data"]["authorization_url"]
                        st.session_state.pay_refs[plan] = res["data"]["reference"]
        if st.session_state.pay_links:
            st.link_button("💳 Pay Once R10 - +10 grades | No Batch", st.session_state.pay_links.get("ONCE10","#"), use_container_width=True)
            st.link_button("💳 Pay Weekly R49 - 7 days - Unlimited + Batch 50", st.session_state.pay_links.get("WEEK49","#"), use_container_width=True)
            st.link_button("⭐ Pay Monthly R99 - 30 days - Unlimited + Batch 50", st.session_state.pay_links.get("MONTH99","#"), use_container_width=True)
            st.link_button("💳 Pay Yearly R799 - 365 days - Unlimited + Batch 50", st.session_state.pay_links.get("YEAR799","#"), use_container_width=True)
            st.write("")
            if is_pro() or (st.session_state.active_plan == "ONCE10" and (3 - st.session_state.uses) > 3):
                st.success("✅ Your plan is already active — no need to check again")
            else:
                if st.button("✅ Check Payment - Unlock My Plan", type="primary", use_container_width=True):
                    if verify_all_refs():
                        st.rerun()
                    else:
                        st.warning("Payment not confirmed yet. Make sure you finished paying on Paystack, then wait 10 seconds and tap again.")
    else:
        st.markdown(f"#### 💰 Pricing ({g['code']})")
        st.markdown(f"- FREE: 3 essays")
        st.markdown(f"- Once-off: {g['symbol']}{g['once']} = +10 grades - No Batch")
        st.markdown(f"- Weekly: {g['symbol']}{g['weekly']} = 7 days unlimited + Batch 50")
        st.markdown(f"- Monthly: {g['symbol']}{g['monthly']} = 30 days unlimited + Batch 50 Tool")
        st.markdown(f"- Yearly: {g['symbol']}{g['yearly']} = 365 days unlimited + Batch 50")
    st.divider()
    st.markdown("#### 🌍 Pay Globally")
    st.link_button(f"💳 Pay with PayPal", PAYPAL_ME)
    st.divider()
    st.caption("Loved it? Send proof and I'll send your code instantly ❤️")
    code = st.text_input("Got a code?", placeholder="Paste your code here", type="password").strip().upper()
    if st.button("Unlock Code"):
        now = datetime.now()
        def set_plan(p): st.session_state.active_plan = p
        code_map = {
            "TEACH10": lambda: (setattr(st.session_state, 'uses', st.session_state.uses - 10), set_plan("ONCE10")),
            "WEEK49": lambda: (setattr(st.session_state, 'pro_expiry', now + timedelta(days=7)), set_plan("WEEK49")),
            "MONTH99": lambda: (setattr(st.session_state, 'pro_expiry', now + timedelta(days=30)), set_plan("MONTH99")),
            "YEAR799": lambda: (setattr(st.session_state, 'pro_expiry', now + timedelta(days=365)), set_plan("YEAR799")),
            "TEFL2026": lambda: (setattr(st.session_state, 'pro_expiry', now + timedelta(days=30)), set_plan("MONTH99")),
        }
        if code in code_map:
            code_map[code](); st.success("Unlocked!"); st.rerun()
        else:
            st.error("That code didn't work")

tab1, tab2, tab3, tab4 = st.tabs(["Single Essay", "Batch 50 PRO (Phase 2)", "📸 Photo / PDF", "📘 Guide"])
with tab1:
    essay = st.text_area("Paste Student Essay:", height=180, placeholder="I broken my leg")
    level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level")
    if st.button("GRADE ESSAY ->"):
        if not is_pro() and st.session_state.uses >= 3:
            st.error("Free limit reached"); st.stop()
        with st.spinner("Grading..."):
            result_text = grade_with_groq(essay, level)
            if not is_pro(): st.session_state.uses += 1
            st.markdown(result_text)
            st.download_button("📄 Download PDF", create_branded_pdf(essay, result_text, level, "Student"), file_name=f"Report_{level}.pdf")

with tab2:
    st.markdown("### 🚀 Phase 2 - Upload 50 Essays At Once (With Student Names)")
    st.info(f"Monthly {g['symbol']}{g['monthly']} unlocks this: Grade 50 essays at once + Class Excel + Named PDFs")
    sample_df = pd.DataFrame({
        "student_name": ["Thandi Mabaso", "John Smith", "Aisha Khan", "Lerato Dlamini", "Sipho Nkosi"],
        "essay": [
            "I go to market yesterday. It was very fun because I buyed many things.",
            "My best friend is Thandi. She is kind and she help me every day.",
            "I broken my leg last week. I was playing soccer and I fall down.",
            "My mother is the best. She cooks delicious food and she loves me.",
            "I want to be a doctor when I grow up because I want to help people."
        ]
    })
    # FIXED: Real Excel file, not CSV
    output_template = BytesIO()
    with pd.ExcelWriter(output_template, engine='openpyxl') as writer:
        sample_df.to_excel(writer, index=False, sheet_name='Essays')
    st.download_button("📥 Download Excel Template (50 Students) - Proper 2 Columns", output_template.getvalue(), file_name="TEFLMate_Batch_Template_50_Phase2.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="template_btn")
    st.caption("✅ Opens correctly in Excel with 2 columns: student_name | essay. Add your 50 students and upload below.")
    st.divider()
    level_b = st.selectbox("Target Level for batch:", ["A1","A2","B1","B2","C1","C2"], key="batch_level")
    uploaded = st.file_uploader("Upload your filled Excel or CSV or TXT", type=["csv","txt","xlsx"], key="batch_file")
    if st.button("GRADE BATCH 50 ->"):
        if not is_pro():
            st.error(f"Batch 50 needs PRO {g['symbol']}{g['monthly']}"); st.stop()
        if not uploaded:
            st.warning("Upload file first"); st.stop()
        essays = []; names = []
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
            essay_col = "essay" if "essay" in df.columns else df.columns[-1]
            name_col = "student_name" if "student_name" in df.columns else df.columns[0]
            essays = df[essay_col].dropna().astype(str).tolist()[:50]
            names = df[name_col].dropna().astype(str).tolist()[:50]
            if len(names) < len(essays):
                names += [f"Student {i+1}" for i in range(len(names), len(essays))]
        elif uploaded.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded)
            essay_col = "essay" if "essay" in df.columns else df.columns[-1]
            name_col = "student_name" if "student_name" in df.columns else df.columns[0]
            essays = df[essay_col].dropna().astype(str).tolist()[:50]
            names = df[name_col].dropna().astype(str).tolist()[:50]
            if len(names) < len(essays):
                names += [f"Student {i+1}" for i in range(len(names), len(essays))]
        else:
            content = uploaded.read().decode("utf-8", errors="ignore")
            essays = [e.strip() for e in content.split("\n") if e.strip()][:50]
            names = [f"Student {i+1}" for i in range(len(essays))]
        st.info(f"Grading {len(essays)} essays...")
        results = []; excel_rows = []; progress = st.progress(0)
        for i, es in enumerate(essays):
            res_text = grade_with_groq(es[:2000], level_b)
            score, cefr = extract_score_cefr(res_text)
            results.append({"Student": names[i], "Essay": es[:100], "Score": f"{score}/10", "CEFR": cefr, "Result": res_text})
            excel_rows.append({"Student Name": names[i], "Score /10": score, "CEFR": cefr, "Essay Preview": es[:200], "Full Feedback": res_text[:1000]})
            progress.progress((i+1)/len(essays))
        st.success(f"Done! {len(results)} graded")
        df_res = pd.DataFrame(results)
        avg_score = sum([r["Score /10"] if isinstance(r["Score /10"], int) else 0 for r in excel_rows]) / len(excel_rows) if excel_rows else 0
        st.markdown("### 📊 Class Dashboard - Phase 2")
        c1, c2, c3 = st.columns(3)
        c1.metric("Average Score", f"{avg_score:.1f} /10")
        c2.metric("Total Graded", f"{len(results)}")
        if excel_rows:
            best = max(excel_rows, key=lambda x: x["Score /10"])
            worst = min(excel_rows, key=lambda x: x["Score /10"])
            c3.metric("Top Student", f"{best['Student Name']} ({best['Score /10']}/10)")
            st.caption(f"Weakest: {worst['Student Name']} ({worst['Score /10']}/10) - Needs support")
        st.dataframe(df_res)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(excel_rows).to_excel(writer, index=False, sheet_name='Grades')
        st.download_button("📊 Download Class Grades Excel (For School)", output.getvalue(), file_name=f"Class_Grades_{level_b}_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15)
        for idx, r in enumerate(results):
            pdf.add_page(); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, f"{r['Student']} - {r['Score']} - {r['CEFR']}", ln=True)
            pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 6, clean(r["Result"]))
        st.download_button("📄 Download All 50 Named Reports PDF", pdf.output(dest='S').encode('latin-1'), file_name=f"Batch_50_Named_{level_b}.pdf")

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
            st.download_button("📄 Download PDF", create_branded_pdf(extracted, result_text, level_p, "PDF Student"), file_name=f"PDF_{level_p}.pdf")
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
            st.download_button("📄 Download PDF", create_branded_pdf(edited, result_text, level_p, "Photo Student"), file_name=f"Photo_{level_p}.pdf")
with tab4:
    st.markdown("## 📘 How Target Levels Work")
    st.info("Target Level = The level you WANT them to reach. We grade AGAINST that level.")
    st.table(pd.DataFrame([
        {"Level": "A1", "Class": "Grade 1-3", "Words": "20-40", "Use For": "ABET"},
        {"Level": "A2", "Class": "Grade 4-6", "Words": "50-80", "Use For": "Primary"},
        {"Level": "B1", "Class": "Grade 7-9", "Words": "120-150", "Use For": "High school"},
        {"Level": "B2", "Class": "Matric", "Words": "180-250", "Use For": "Matric, College"},
        {"Level": "C1", "Class": "University", "Words": "250-300", "Use For": "University, Work"},
        {"Level": "C2", "Class": "Mastery", "Words": "300+", "Use For": "Teachers"},
    ]))
st.divider()
st.markdown("### ❤️ Payshap 0658006750 | PayPal: paypal.me/TaahirMahomed | Send proof by WhatsApp or Email and I'll send your code")
col1, col2, col3 = st.columns(3)
with col1:
    st.link_button("💬 WhatsApp Proof", "https://wa.me/27658006750?text=Hi%20I%20paid%20for%20TEFLMate")
with col2:
    st.link_button(f"📧 Email proof", f"mailto:{YOUR_EMAIL}?subject=TEFLMate Payment Proof")
with col3:
    st.link_button(f"💳 Pay with PayPal", PAYPAL_ME)
st.caption("TEFLMate v6.0.1 Phase 2 • Durban, SA • Built by Mr Taahir Mahomed • Worldwide 🌍")
