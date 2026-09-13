import streamlit as st
# --- UPTIME ROBOT KEEP-ALIVE - DO NOT REMOVE ---
if "ping" in st.query_params or "uptime" in st.query_params or "health" in st.query_params:
    st.write("OK - TEFLMate Awake")
    st.stop()

from groq import Groq
from datetime import datetime, timedelta
from fpdf import FPDF
import unicodedata
import pandas as pd
import base64
import requests
import re
import urllib.parse
from io import BytesIO
import matplotlib.pyplot as plt
try:
    import fitz
except ImportError:
    fitz = None
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON)

YOUR_EMAIL = "taahir532@gmail.com"
PAYPAL_ME = "https://paypal.me/TaahirMahomed"
st.set_page_config(page_title="TEFLMate v6.5 SUPER 7Lang", page_icon="📝", layout="centered")
st.markdown("""<style>.stButton>button {background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;} div[data-testid="stLinkButton"]>a{background:#111!important;color:white!important;border-radius:10px!important;height:45px!important;font-weight:bold!important;width:100%!important;display:flex!important;align-items:center!important;justify-content:center!important;}</style>""", unsafe_allow_html=True)

if "uses" not in st.session_state: st.session_state.uses = 0
if "pro_expiry" not in st.session_state: st.session_state.pro_expiry = None
if "active_plan" not in st.session_state: st.session_state.active_plan = None
if "pay_links" not in st.session_state: st.session_state.pay_links = {}
if "pay_refs" not in st.session_state: st.session_state.pay_refs = {}
if "batch_results" not in st.session_state: st.session_state.batch_results = None
if "user" not in st.session_state: st.session_state.user = None
if "teacher_id" not in st.session_state: st.session_state.teacher_id = None
if "custom_rubric" not in st.session_state: st.session_state.custom_rubric = None
if "feedback_lang" not in st.session_state: st.session_state.feedback_lang = "English"
if "grading_standard" not in st.session_state: st.session_state.grading_standard = "CEFR"
if "geo" not in st.session_state:
    try:
        ip_data = requests.get("https://ipapi.co/json/", timeout=3).json()
        country = ip_data.get("country_code", "ZA")
    except:
        country = "ZA"
    if country == "ZA": st.session_state.geo = {"symbol":"R", "weekly":"49", "monthly":"99", "yearly":"799", "once":"10", "code":"ZAR"}
    elif country == "GB": st.session_state.geo = {"symbol":"£", "weekly":"3.99", "monthly":"6.99", "yearly":"55", "once":"0.99", "code":"GBP"}
    elif country in ["DE","FR","NL","IT","ES","PT","IE"]: st.session_state.geo = {"symbol":"€", "weekly":"4.99", "monthly":"8.50", "yearly":"65", "once":"0.99", "code":"EUR"}
    else: st.session_state.geo = {"symbol":"$", "weekly":"4.99", "monthly":"8.50", "yearly":"65", "once":"0.99", "code":"USD"}

def login_screen():
    st.title("📝 TEFLMate v6.5 SUPER 7Lang - Login")
    st.caption("Worldwide - Arabic Hindi Chinese Added - NEED")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        with st.form("login_form_fix"):
            email = st.text_input("Email"); password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    td = supabase.table("teachers").select("*").eq("email", email).execute()
                    if td.data: st.session_state.teacher_id = td.data[0]["id"]
                    else: ins = supabase.table("teachers").insert({"email": email}).execute(); st.session_state.teacher_id = ins.data[0]["id"]
                    st.rerun()
                except Exception as e: st.error(f"Login failed: {e}")
    with t2:
        with st.form("signup_form_fix"):
            email2 = st.text_input("New Email"); password2 = st.text_input("New Password", type="password"); school = st.text_input("School Name", value="My School")
            submitted2 = st.form_submit_button("Create Account", use_container_width=True)
            if submitted2:
                try:
                    res = supabase.auth.sign_up({"email": email2, "password": password2})
                    supabase.table("teachers").insert({"email": email2, "school_name": school}).execute()
                    st.success("Account created! Now go to Login tab.")
                except Exception as e: st.error(f"Signup failed: {e}")
    st.stop()
if not st.session_state.user: login_screen()

def is_pro(): return st.session_state.pro_expiry is not None and datetime.now() < st.session_state.pro_expiry
def get_status():
    if is_pro():
        days = (st.session_state.pro_expiry - datetime.now()).days + 1
        plan = st.session_state.active_plan
        if plan == "WEEK49": return f"✅ R49 Weekly ACTIVE - {days} days left"
        elif plan == "MONTH99": return f"✅ R99 Monthly ACTIVE - {days} days left"
        elif plan == "YEAR799": return f"✅ R799 Yearly ACTIVE - {days} days left"
        else: return f"PRO ACTIVE - {days} days left"
    else:
        remaining = 3 - st.session_state.uses
        if remaining <= 0: return "❌ FREE - 0 left"
        if st.session_state.active_plan == "ONCE10" and remaining > 3: return f"✅ R10 Active - {remaining} left"
        return f"FREE - {remaining} left"

def clean(text): return unicodedata.normalize('NFKD', text or "").encode('ascii', 'ignore').decode('ascii')
def clean_feedback_for_excel(text):
    if not text: return ""
    t = clean(text); t = re.sub(r'\*\*|###|##|__|\*\*', '', t); t = re.sub(r'\*\s*', '- ', t); return t.strip()
def extract_score_cefr(text):
    try:
        score_match = re.search(r'(\d+)\s*/\s*10', text); score = int(score_match.group(1)) if score_match else 0
        cefr_match = re.search(r'\b(A1|A2|B1|B2|C1|C2)\b', text); cefr = cefr_match.group(1) if cefr_match else "N/A"
        return score, cefr, ""
    except: return 0, "N/A", ""
def df_to_excel_bytes_safe(df, sheet_name="Sheet1"):
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
            ws = writer.sheets[sheet_name]
            from openpyxl.styles import Alignment
            for col in ws.columns:
                max_len = 0; col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        l = len(str(cell.value))
                        if l > max_len: max_len = l
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
                ws.column_dimensions[col_letter].width = min(50, max(12, max_len + 2))
            ws.auto_filter.ref = ws.dimensions; ws.freeze_panes = 'A2'
        return output.getvalue(), "xlsx"
    except: return df.to_csv(index=False).encode('utf-8'), "csv"

def init_paystack(email, amount_kobo, plan_code):
    try:
        secret = st.secrets["PAYSTACK_SECRET_KEY"]; headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
        data = {"email": email, "amount": int(amount_kobo), "metadata": {"plan": plan_code}}
        r = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers, timeout=10); return r.json()
    except Exception as e: return {"status": False, "message": str(e)}
def verify_paystack(ref):
    try:
        secret = st.secrets["PAYSTACK_SECRET_KEY"]; r = requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers={"Authorization": f"Bearer {secret}"}, timeout=10); return r.json()
    except Exception as e: return {"status": False, "message": str(e)}
def unlock_paystack(v):
    if not v.get("status"): return False
    d = v.get("data", {});
    if d.get("status")!= "success": return False
    amt = d.get("amount", 0); plan = d.get("metadata", {}).get("plan", ""); now = datetime.now()
    if amt == 1000 or plan == "ONCE10": st.session_state.uses -= 10; st.session_state.active_plan = "ONCE10"; st.success("R10 received!"); st.balloons(); return True
    elif amt == 4900 or plan == "WEEK49": st.session_state.pro_expiry = now + timedelta(days=7); st.session_state.active_plan = "WEEK49"; st.success("R49 Weekly PRO"); st.balloons(); return True
    elif amt == 9900 or plan == "MONTH99": st.session_state.pro_expiry = now + timedelta(days=30); st.session_state.active_plan = "MONTH99"; st.success("R99 Monthly PRO"); st.balloons(); return True
    elif amt == 79900 or plan == "YEAR799": st.session_state.pro_expiry = now + timedelta(days=365); st.session_state.active_plan = "YEAR799"; st.success("R799 Yearly PRO"); st.balloons(); return True
    return False
def verify_all_refs():
    for ref in list(st.session_state.pay_refs.values()):
        v = verify_paystack(ref)
        if v.get("status") and v.get("data", {}).get("status") == "success":
            if unlock_paystack(v): st.session_state.pay_refs = {}; st.session_state.pay_links = {}; st.query_params.clear(); return True
    return False

q = st.query_params
if "reference" in q:
    if unlock_paystack(verify_paystack(q["reference"])): st.query_params.clear(); st.session_state.pay_refs = {}; st.session_state.pay_links = {}
else:
    if st.session_state.pay_refs: verify_all_refs()

def extract_text_from_image(image_bytes):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"]); b64 = base64.b64encode(image_bytes).decode('utf-8')
    try:
        res = client.chat.completions.create(model="qwen/qwen3.6-27b", messages=[{"role": "user", "content": [{"type": "text", "text": "OCR: Extract handwritten text EXACTLY as written, keep mistakes. Return only text."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
        txt = res.choices[0].message.content
        if "</think>" in txt: txt = txt.split("</think>")[-1].strip()
        return txt.strip()
    except Exception as e: return f"OCR_ERROR: {e}"
def extract_text_from_pdf(pdf_bytes):
    if not fitz: return "Add PyMuPDF"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf"); text = "\n".join([p.get_text() for p in doc[:3]])
        if len(text.strip()) < 30 and len(doc) > 0: pix = doc[0].get_pixmap(dpi=200); text = extract_text_from_image(pix.tobytes("jpeg"))
        return text
    except Exception as e: return f"PDF_ERROR: {e}"
def create_branded_pdf(original_essay, ai_result, target_level, student_name="Student"):
    pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    pdf.set_fill_color(17, 24, 39); pdf.rect(0, 0, 210, 32, 'F'); pdf.set_y(7)
    pdf.set_font("Arial", 'B', 14); pdf.set_text_color(255,255,255); pdf.cell(0, 8, "Mr Mahomed | Essay Grader Report", align='C', ln=True); pdf.ln(10)
    pdf.set_text_color(0,0,0); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 7, f"Student: {student_name} | Level: {target_level} | Date: {datetime.now().strftime('%d %b %Y')}", ln=True); pdf.ln(2)
    pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 6, clean(ai_result)); return pdf.output(dest='S').encode('latin-1')
def create_principal_pdf(excel_rows, level, avg_score, school_name="School"):
    pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    pdf.set_fill_color(17, 24, 39); pdf.rect(0, 0, 210, 30, 'F'); pdf.set_y(7)
    pdf.set_font("Arial", 'B', 16); pdf.set_text_color(255,255,255); pdf.cell(0, 8, f"Principal Report - {school_name}", align='C', ln=True)
    pdf.set_font("Arial", '', 10); pdf.cell(0, 6, f"Level: {level} | Total: {len(excel_rows)} | Avg: {avg_score:.1f}/10", align='C', ln=True); pdf.ln(12)
    pdf.set_text_color(0,0,0); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, f"Class Summary - Average: {avg_score:.1f}/10", ln=True); pdf.ln(4)
    pdf.set_font("Arial", 'B', 11); pdf.cell(0, 7, "Student List:", ln=True); pdf.ln(2)
    pdf.set_fill_color(230,230,230); pdf.set_font("Arial", 'B', 10)
    pdf.cell(70, 8, "Student Name", border=1, fill=True); pdf.cell(25, 8, "Score", border=1, fill=True, align='C'); pdf.cell(25, 8, "CEFR", border=1, fill=True, align='C'); pdf.cell(70, 8, "Status", border=1, fill=True); pdf.ln()
    pdf.set_font("Arial", '', 9)
    for r in excel_rows:
        score = r['Score /10']; status = "Excellent" if score >= 8 else "Good" if score >= 6 else "Needs Support"
        pdf.cell(70, 7, clean(r['Student Name'])[:35], border=1); pdf.cell(25, 7, f"{score}/10", border=1, align='C'); pdf.cell(25, 7, r['CEFR'], border=1, align='C'); pdf.cell(70, 7, status, border=1); pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

def detect_ai_risk(essay_text):
    text = essay_text.lower()
    if len(text) < 30: return "N/A"
    if text.count("delve")>0 or text.count("tapestry")>0: return "⚠️ Possible AI"
    avg = sum(len(w) for w in text.split())/len(text.split()) if text.split() else 0
    if avg>5.5 and len([w for w in text.split() if len(w)>10])>5: return "⚠️ Possible AI"
    return "✅ Human"
def translate_feedback(text, target_lang):
    if target_lang == "English": return text
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        m = {"Spanish":"Spanish","Portuguese":"Brazilian Portuguese","French":"French","Arabic":"Arabic","Hindi":"Hindi","Chinese":"Simplified Chinese"}
        prompt = f"Translate to {m.get(target_lang,'Spanish')}, keep scores English: {text[:1200]}"
        res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except: return text
def grade_with_groq(essay_text, level):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    rubric = f"CUSTOM RUBRIC: {st.session_state.custom_rubric[:2000]}" if st.session_state.custom_rubric else ""
    lang = st.session_state.feedback_lang; std = st.session_state.grading_standard
    std_inst = ""
    if std=="IELTS": std_inst="Also give IELTS Band 0-9. Format: IELTS Band X.X"
    elif std=="TOEFL": std_inst="Also give TOEFL 0-30. Format: TOEFL Score XX/30"
    elif std=="US Grade": std_inst="Also give US Grade A-F."
    else: std_inst="Give CEFR A1-C2"
    lang_inst = f"Feedback language: {lang}. Write entire feedback in {lang}, keep Score/10 English." if lang!="English" else "Feedback in English"
    prompt = f"You are Cambridge TEFL examiner for {level}. {std_inst}. {lang_inst}. {rubric} Grade: {essay_text}. ASCII only. Structure: 1.CEFR+{std} 2.Score/10 3.AI Check 4.Summary 5.2 Strengths 6.Table Mistake|Correction|Why 7.Corrected version 8.Parent Summary"
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}])
    return res.choices[0].message.content
def save_essay_db(student_name, essay_text, level, score, cefr, feedback):
    try: supabase.table("essays").insert({"teacher_id": st.session_state.teacher_id, "student_name": student_name, "essay_text": essay_text, "level": level, "score": score, "cefr": cefr, "feedback": feedback}).execute()
    except Exception as e: st.warning(f"DB error: {e}")

st.title("📝 TEFLMate v6.5 SUPER - 7 Languages")
st.caption(f"Logged in as {st.session_state.user.email} | 7 Langs + Rubric + IELTS/TOEFL + AI Flag + Graph")
if st.sidebar.button("Logout"): supabase.auth.sign_out(); st.session_state.user=None; st.session_state.teacher_id=None; st.rerun()

with st.sidebar:
    st.markdown("### 🔑 Your Plan"); st.info(get_status())
    g = st.session_state.geo
    if g['code']=="ZAR":
        st.markdown(f"#### 💰 1-Click Pay ({g['code']})")
        email = st.text_input("Email for receipt:", value=YOUR_EMAIL, key="pay_email_clean")
        if not st.session_state.pay_links and email:
            with st.spinner("Loading pay options..."):
                for plan, amt in [("ONCE10",1000),("WEEK49",4900),("MONTH99",9900),("YEAR799",79900)]:
                    res = init_paystack(email, amt, plan)
                    if res.get("status"): st.session_state.pay_links[plan]=res["data"]["authorization_url"]; st.session_state.pay_refs[plan]=res["data"]["reference"]
        if st.session_state.pay_links:
            st.link_button("💳 Pay Once R10", st.session_state.pay_links.get("ONCE10","#"), use_container_width=True)
            st.link_button("💳 Pay Weekly R49", st.session_state.pay_links.get("WEEK49","#"), use_container_width=True)
            st.link_button("⭐ Pay Monthly R99", st.session_state.pay_links.get("MONTH99","#"), use_container_width=True)
            st.link_button("💳 Pay Yearly R799", st.session_state.pay_links.get("YEAR799","#"), use_container_width=True)
            if st.button("✅ Check Payment - Unlock My Plan", type="primary", use_container_width=True):
                if verify_all_refs(): st.rerun()
    st.divider()
    st.markdown("#### 🌎 GLOBAL Controls (7 Languages) - NEED")
    st.session_state.feedback_lang = st.selectbox("Feedback Language:", ["English","Spanish","Portuguese","French","Arabic","Hindi","Chinese"], index=["English","Spanish","Portuguese","French","Arabic","Hindi","Chinese"].index(st.session_state.feedback_lang))
    st.session_state.grading_standard = st.selectbox("Grading Standard:", ["CEFR","IELTS","TOEFL","US Grade"], index=["CEFR","IELTS","TOEFL","US Grade"].index(st.session_state.grading_standard))
    st.caption(f"Active: {st.session_state.feedback_lang} + {st.session_state.grading_standard}")
    with st.expander("📋 Custom Rubric Upload (NEED)"):
        rub_file = st.file_uploader("Upload Rubric PDF/Image/TXT", type=["pdf","jpg","jpeg","png","txt"], key="rubric_up")
        rub_text = st.text_area("Or paste rubric:", value=st.session_state.custom_rubric or "", height=80)
        if rub_file:
            if rub_file.name.endswith(".pdf"): txt = extract_text_from_pdf(rub_file.getvalue())
            elif rub_file.name.endswith(".txt"): txt = rub_file.getvalue().decode("utf-8")
            else: txt = extract_text_from_image(rub_file.getvalue())
            st.session_state.custom_rubric = txt; st.success("Rubric loaded!")
        elif rub_text: st.session_state.custom_rubric = rub_text
        if st.session_state.custom_rubric:
            st.info(f"Rubric active: {st.session_state.custom_rubric[:80]}...")
            if st.button("Clear Rubric"): st.session_state.custom_rubric=None; st.rerun()

tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["Single Essay","Batch 50 PRO","📸 Photo/PDF","📚 History+Graph","📘 Guide","🚀 SUPER 7Lang"])

with tab1:
    essay = st.text_area("Paste Essay:", height=150); s_name = st.text_input("Student Name:", value="Student", key="s_name_single"); level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level")
    st.caption(f"🌍 {st.session_state.feedback_lang} | {st.session_state.grading_standard} | Rubric: {'✅' if st.session_state.custom_rubric else '❌'}")
    if st.button("GRADE ESSAY ->"):
        if not is_pro() and st.session_state.uses>=3: st.error("Free limit"); st.stop()
        with st.spinner("Grading..."):
            result_text = grade_with_groq(essay, level); score, cefr, _ = extract_score_cefr(result_text); ai_flag = detect_ai_risk(essay)
            save_essay_db(s_name, essay, level, score, cefr, result_text)
            if not is_pro(): st.session_state.uses+=1
            st.markdown(f"**AI Check:** {ai_flag}"); st.markdown(result_text)
            st.download_button("📄 Download PDF", create_branded_pdf(essay, result_text, level, s_name), file_name=f"Report_{level}.pdf")

with tab2:
    st.markdown("### 🚀 Batch 50 SUPER 7Lang")
    sample_df = pd.DataFrame({"student_name":["Thandi","John","Aisha"],"essay":["I go to market yesterday.","My best friend is Thandi.","I broken my leg last week."]})
    b,_ = df_to_excel_bytes_safe(sample_df,"Essays"); st.download_button("📥 Download Template", b, file_name="Template.xlsx")
    school_name = st.text_input("School Name:", value="My School", key="school_name_input"); level_b = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="batch_level")
    uploaded = st.file_uploader("Upload Excel/CSV", type=["csv","xlsx","txt"], key="batch_file")
    if st.button("GRADE BATCH 50 ->"):
        if not is_pro(): st.error("Need PRO"); st.stop()
        if not uploaded: st.warning("Upload first"); st.stop()
        essays=[]; names=[]
        try:
            if uploaded.name.endswith(".csv"): df=pd.read_csv(uploaded); essay_col="essay" if "essay" in df.columns else df.columns[-1]; name_col="student_name" if "student_name" in df.columns else df.columns[0]; essays=df[essay_col].astype(str).tolist()[:50]; names=df[name_col].astype(str).tolist()[:50]
            elif uploaded.name.endswith(".xlsx"): df=pd.read_excel(uploaded); essay_col="essay" if "essay" in df.columns else df.columns[-1]; name_col="student_name" if "student_name" in df.columns else df.columns[0]; essays=df[essay_col].astype(str).tolist()[:50]; names=df[name_col].astype(str).tolist()[:50]
            else: content=uploaded.read().decode("utf-8", errors="ignore"); essays=[e.strip() for e in content.split("\n") if e.strip()][:50]; names=[f"Student {i+1}" for i in range(len(essays))]
        except Exception as e: st.error(f"Read error: {e}"); st.stop()
        results=[]; excel_rows=[]; progress=st.progress(0)
        for i,es in enumerate(essays):
            res_text=grade_with_groq(es[:2000],level_b); score,cefr,_=extract_score_cefr(res_text); ai_flag=detect_ai_risk(es)
            save_essay_db(names[i],es,level_b,score,cefr,res_text); clean_res=clean_feedback_for_excel(res_text)
            results.append({"Student":names[i],"Score":f"{score}/10","CEFR":cefr,"AI_Flag":ai_flag,"Result":clean_res}); excel_rows.append({"Student Name":names[i],"Score /10":score,"CEFR":cefr,"AI Check":ai_flag,"Full Feedback":clean_res[:1000]})
            progress.progress((i+1)/len(essays))
        st.session_state.batch_results={"results":results,"excel_rows":excel_rows,"level":level_b,"school":school_name}
        st.success(f"Done {len(results)}")
    if st.session_state.batch_results:
        results=st.session_state.batch_results["results"]; excel_rows=st.session_state.batch_results["excel_rows"]; level_b=st.session_state.batch_results["level"]; school_name=st.session_state.batch_results["school"]
        avg_score=sum([r["Score /10"] for r in excel_rows])/len(excel_rows) if excel_rows else 0
        st.markdown(f"### Avg {avg_score:.1f}/10 - {len(results)} graded")
        st.dataframe(pd.DataFrame(results))
        grades_df=pd.DataFrame(excel_rows); gb,_=df_to_excel_bytes_safe(grades_df,"Grades")
        col1,col2=st.columns(2)
        with col1: st.download_button("📊 Download Excel", gb, file_name="Grades.xlsx")
        with col2: st.download_button("🏫 Principal PDF", create_principal_pdf(excel_rows, level_b, avg_score, school_name), file_name="Principal.pdf")
        classroom_df=pd.DataFrame([{"Student Name":r["Student Name"],"Score":r["Score /10"],"Max":10,"CEFR":r["CEFR"]} for r in excel_rows]); cb,_=df_to_excel_bytes_safe(classroom_df,"Classroom")
        st.download_button("🎓 Google Classroom CSV", cb, file_name="Classroom_Import.csv")

with tab3:
    st.markdown("### 📸 Photo/PDF")
    level_p=st.selectbox("Target Level:",["A1","A2","B1","B2","C1","C2"],key="photo_level")
    camera_pic=st.camera_input("Take photo"); upload_img=st.file_uploader("Upload Image",type=["jpg","jpeg","png"],key="img_up"); upload_pdf=st.file_uploader("Upload PDF",type=["pdf"],key="pdf_up")
    image_bytes=None
    if camera_pic: image_bytes=camera_pic.getvalue()
    elif upload_img: image_bytes=upload_img.getvalue()
    if image_bytes: st.image(image_bytes,use_container_width=True)
    if upload_pdf:
        extracted=extract_text_from_pdf(upload_pdf.getvalue()); st.text_area("Text from PDF:",value=extracted,height=120)
        if st.button("GRADE PDF TEXT ->"):
            result_text=grade_with_groq(extracted,level_p); score,cefr,_=extract_score_cefr(result_text); save_essay_db("PDF Student",extracted,level_p,score,cefr,result_text); st.markdown(result_text)
    if image_bytes and st.button("READ & GRADE PHOTO ->"):
        with st.spinner("Reading..."): extracted=extract_text_from_image(image_bytes); st.session_state['last_ocr']=extracted; st.rerun()
    if 'last_ocr' in st.session_state:
        edited=st.text_area("Edit:",value=st.session_state['last_ocr'],height=120)
        if st.button("GRADE THIS TEXT ->"):
            result_text=grade_with_groq(edited,level_p); st.markdown(result_text)

with tab4:
    st.markdown("### 📚 History + Graph - Retention Moat")
    try:
        rows=supabase.table("essays").select("*").eq("teacher_id",st.session_state.teacher_id).order("created_at",desc=True).limit(200).execute()
        if rows.data:
            df=pd.DataFrame(rows.data); st.dataframe(df[["student_name","level","score","cefr","created_at"]])
            student_list=df["student_name"].unique().tolist(); sel=st.selectbox("Select Student:",student_list)
            if sel:
                sdf=df[df["student_name"]==sel].sort_values("created_at")
                if len(sdf)>1:
                    fig,ax=plt.subplots(); ax.plot(pd.to_datetime(sdf["created_at"]),sdf["score"],marker='o'); ax.set_title(f"{sel} Progress"); st.pyplot(fig)
                    st.success(f"Growth {sdf['score'].iloc[0]} -> {sdf['score'].iloc[-1]}")
                else: st.info("Need 2+ essays for graph")
            avg=df["score"].mean(); st.metric("Avg",f"{avg:.1f}/10"); st.metric("Total",len(df))
        else: st.info("No history yet")
    except Exception as e: st.error(f"History error: {e}")

with tab5:
    st.markdown("## 📘 Guide - 7 Languages = NEED")
    st.table(pd.DataFrame([{"Lang":"English","Market":"SA/US/UK","Teachers":"300k"},{"Lang":"Spanish","Market":"Mexico/Spain","Teachers":"300k"},{"Lang":"Portuguese","Market":"Brazil","Teachers":"500k"},{"Lang":"French","Market":"France/Africa","Teachers":"200k"},{"Lang":"Arabic","Market":"MENA","Teachers":"400k"},{"Lang":"Hindi","Market":"India","Teachers":"600k"},{"Lang":"Chinese","Market":"China","Teachers":"300k"}]))

with tab6:
    st.markdown("## 🚀 SUPER 7Lang - Worldwide NEED")
    c1,c2,c3=st.columns(3)
    with c1:
        st.markdown("### 🇧🇷 Brazil");
        if st.button("Set Brazil"): st.session_state.feedback_lang="Portuguese"; st.session_state.grading_standard="CEFR"; st.success("PT+CEFR")
    with c2:
        st.markdown("### 🇸🇦 MENA");
        if st.button("Set Arabic"): st.session_state.feedback_lang="Arabic"; st.session_state.grading_standard="IELTS"; st.success("AR+IELTS")
    with c3:
        st.markdown("### 🇮🇳 India");
        if st.button("Set Hindi"): st.session_state.feedback_lang="Hindi"; st.session_state.grading_standard="IELTS"; st.success("HI+IELTS")
    c4,c5,c6=st.columns(3)
    with c4:
        st.markdown("### 🇨🇳 China");
        if st.button("Set China"): st.session_state.feedback_lang="Chinese"; st.session_state.grading_standard="TOEFL"; st.success("ZH+TOEFL")
    with c5:
        st.markdown("### 🇲🇽 Mexico");
        if st.button("Set Mexico"): st.session_state.feedback_lang="Spanish"; st.session_state.grading_standard="IELTS"; st.success("ES+IELTS")
    with c6:
        st.markdown("### 🇫🇷 Africa");
        if st.button("Set French"): st.session_state.feedback_lang="French"; st.session_state.grading_standard="CEFR"; st.success("FR+CEFR")

st.caption("TEFLMate v6.5 SUPER 7Lang • Worldwide - 7 Languages + Rubric + IELTS/TOEFL + AI Flag + Graph")
