import streamlit as st

# --- UPTIME ROBOT KEEP-ALIVE - MUST BE FIRST ---
if "ping" in st.query_params or "uptime" in st.query_params or "health" in st.query_params:
    st.write("OK - TEFLMate Awake")
    st.stop()

import streamlit.components.v1 as components
components.html("""
<script>
const hash = window.parent.location.hash;
if (hash && hash.includes('access_token')) {
    const queryString = hash.substring(1);
    const newUrl = window.parent.location.origin + window.parent.location.pathname + '?' + queryString;
    window.parent.location.href = newUrl;
}
</script>
""", height=0)

from groq import Groq
from datetime import datetime, timedelta
from fpdf import FPDF
import unicodedata
import pandas as pd
import base64
import requests
import re
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

@st.cache_resource
def get_groq():
    return Groq(api_key=st.secrets["GROQ_API_KEY"])

YOUR_EMAIL = "taahir532@gmail.com"
st.set_page_config(page_title="TEFLMate - Class Portfolio", page_icon="📚", layout="wide")

st.markdown("""<style>
.stButton>button {background:#111;color:white;border-radius:10px;height:48px;font-weight:bold;width:100%;border:1px solid #111;}
div[data-testid="stLinkButton"]>a{background:#111!important;color:white!important;border-radius:10px!important;height:48px!important;font-weight:bold!important;display:flex!important;align-items:center!important;justify-content:center!important;}
button[data-baseweb="tab"] {font-size:13px; padding:8px 10px;}
</style>""", unsafe_allow_html=True)

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
if "last_reset" not in st.session_state: st.session_state.last_reset = None
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

# === RECOVERY FIXED - WORKS WITH YOUR URL FROM PHOTO ===
q_rec = st.query_params
has_token = False
try:
    if "access_token" in q_rec:
        has_token = True
except:
    pass

if has_token:
    try:
        access_token = q_rec.get("access_token", "")
        if isinstance(access_token, list):
            access_token = access_token[0]
        refresh_token = q_rec.get("refresh_token", "")
        if isinstance(refresh_token, list):
            refresh_token = refresh_token[0]
    except:
        access_token = ""
        refresh_token = ""
    try:
        if access_token and refresh_token:
            supabase.auth.set_session(access_token, refresh_token)
    except:
        pass

    st.title("🔐 TEFLMate - Set New Password")
    st.info("Reset link detected - set your new password below")
    new_p = st.text_input("New Password (6+ chars)", type="password", key="rec_new_fixed_700")
    conf_p = st.text_input("Confirm", type="password", key="rec_conf_fixed_700")
    if st.button("✅ UPDATE PASSWORD & LOGIN", type="primary", use_container_width=True):
        if len(new_p) < 6: st.warning("6+ chars")
        elif new_p!= conf_p: st.error("No match")
        else:
            try:
                supabase.auth.update_user({"password": new_p})
                st.success("✅ Updated! Clear URL and login with new password now."); st.query_params.clear(); supabase.auth.sign_out()
                st.session_state.user=None; st.session_state.teacher_id=None; st.balloons()
            except Exception as e: st.error(f"Update failed: {e} - Try logging in first then change in sidebar")
    st.stop()

if st.session_state.user is None:
    try:
        sess = supabase.auth.get_session()
        if sess and sess.user:
            st.session_state.user = sess.user
            td = supabase.table("teachers").select("*").eq("email", sess.user.email).execute()
            if td.data:
                st.session_state.teacher_id = td.data[0]["id"]
                if td.data[0].get("pro_expiry"):
                    try:
                        exp = datetime.fromisoformat(td.data[0]["pro_expiry"].replace("Z",""))
                        if exp > datetime.now():
                            st.session_state.pro_expiry = exp
                            st.session_state.active_plan = td.data[0].get("active_plan")
                    except: pass
    except: pass

def login_screen():
    st.title("📚 TEFLMate - Class Portfolio")
    st.caption("Photo-grade handwritten homework • Track progress • Parent reports in 7 languages")
    t1, t2 = st.tabs(["🔑 Login", "✨ Sign Up"])
    with t1:
        with st.form("login_form_v700"):
            email = st.text_input("Email"); password = st.text_input("Password", type="password")
            if st.form_submit_button("🚀 Login", use_container_width=True, type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    td = supabase.table("teachers").select("*").eq("email", email).execute()
                    if td.data: st.session_state.teacher_id = td.data[0]["id"]
                    else: ins = supabase.table("teachers").insert({"email": email}).execute(); st.session_state.teacher_id = ins.data[0]["id"]
                    st.rerun()
                except Exception as e: st.error(f"Login failed: {e}")
        with st.expander("🔓 Forgot Password?"):
            fp_email = st.text_input("Email to reset:", key="fp_email_700")
            if st.session_state.last_reset and (datetime.now()-st.session_state.last_reset).total_seconds()<3600:
                st.warning(f"Wait {int(60-(datetime.now()-st.session_state.last_reset).total_seconds()//60)} mins - Supabase rate limit")
            else:
                if st.button("📧 Send Reset Link", use_container_width=True):
                    try:
                        supabase.auth.reset_password_for_email(fp_email, {"redirect_to": "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"})
                        st.session_state.last_reset = datetime.now(); st.success(f"Sent to {fp_email} - Check spam too")
                    except Exception as e: st.error(str(e))
    with t2:
        with st.form("signup_form_v700"):
            email2 = st.text_input("New Email", key="s_email_700"); password2 = st.text_input("New Password", type="password", key="s_pass_700"); school = st.text_input("School Name", value="My School")
            if st.form_submit_button("Create Account", use_container_width=True):
                try:
                    supabase.auth.sign_up({"email": email2, "password": password2})
                    supabase.table("teachers").insert({"email": email2, "school_name": school}).execute()
                    st.success("Created! Go to Login tab.")
                except Exception as e: st.error(str(e))
    st.stop()

if not st.session_state.user: login_screen()

def is_pro(): return st.session_state.pro_expiry is not None and datetime.now() < st.session_state.pro_expiry
def get_status():
    if is_pro():
        days = (st.session_state.pro_expiry - datetime.now()).days + 1
        return f"✅ {st.session_state.active_plan} - {days}d left"
    else:
        remaining = 3 - st.session_state.uses
        if remaining <=0: return "❌ FREE - 0 left"
        if st.session_state.active_plan == "ONCE10" and remaining >3: return f"✅ R10 - {remaining} left"
        return f"FREE - {remaining} left"

def clean(text): return unicodedata.normalize('NFKD', text or "").encode('ascii', 'ignore').decode('ascii')
def clean_feedback_for_excel(text):
    if not text: return ""
    t = clean(text); t = re.sub(r'\*\*|###|##|__|\*\*', '', t); return t.strip()
def extract_score_cefr(text):
    try:
        score_match = re.search(r'(\d+)\s*/\s*10', text); score = int(score_match.group(1)) if score_match else 0
        cefr_match = re.search(r'\b(A1|A2|B1|B2|C1|C2)\b', text); cefr = cefr_match.group(1) if cefr_match else "B1"
        return score, cefr, ""
    except: return 0, "B1", ""
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
    pro_exp = None; active = None
    if amt == 1000 or plan == "ONCE10": st.session_state.uses -= 10; active="ONCE10"; st.success("R10 received! +10 grades"); st.balloons()
    elif amt == 4900 or plan == "WEEK49": pro_exp = now + timedelta(days=7); active="WEEK49"; st.success("R49 Weekly PRO"); st.balloons()
    elif amt == 9900 or plan == "MONTH99": pro_exp = now + timedelta(days=30); active="MONTH99"; st.success("R99 Monthly PRO"); st.balloons()
    elif amt == 79900 or plan == "YEAR799": pro_exp = now + timedelta(days=365); active="YEAR799"; st.success("R799 Yearly PRO"); st.balloons()
    else: return False
    if active!= "ONCE10" and pro_exp:
        st.session_state.pro_expiry = pro_exp; st.session_state.active_plan = active
        try: supabase.table("teachers").update({"pro_expiry": pro_exp.isoformat(), "active_plan": active}).eq("id", st.session_state.teacher_id).execute()
        except: pass
    else:
        st.session_state.active_plan = active
    return True

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

# === YOUR WORKING QWEN - LOCKED, DO NOT CHANGE ===
def extract_text_from_image(image_bytes):
    client = get_groq(); b64 = base64.b64encode(image_bytes).decode('utf-8')
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
    pdf.set_font("Arial", 'B', 14); pdf.set_text_color(255,255,255); pdf.cell(0, 8, "TEFLMate | Class Portfolio Report", align='C', ln=True); pdf.ln(10)
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

def grade_with_groq(essay_text, level):
    client = get_groq()
    rubric = f"CUSTOM RUBRIC: {st.session_state.custom_rubric[:2000]}" if st.session_state.custom_rubric else ""
    lang = st.session_state.feedback_lang; std = st.session_state.grading_standard
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

# FIXED: This was [3][1] and crashed - now [3,1]
col_title, col_user = st.columns([3,1])
with col_title:
    st.title("📚 TEFLMate - Class Portfolio")
    st.caption("Track progress • Photo-grade handwriting • Parent reports in 7 languages • HOD reports")
with col_user:
    st.info(f"👤 {st.session_state.user.email[:20]} | {get_status()}" if st.session_state.user else "Not logged")
    if st.session_state.user and st.button("Logout", use_container_width=True):
        supabase.auth.sign_out(); st.session_state.user=None; st.session_state.teacher_id=None; st.rerun()

with st.sidebar:
    st.markdown("### 🔑 Your Plan"); st.info(get_status())
    with st.expander("🔐 Change Password"):
        new_pass = st.text_input("New Password", type="password", key="new_pass_700")
        confirm_pass = st.text_input("Confirm New Password", type="password", key="confirm_pass_700")
        if st.button("Update Password", use_container_width=True, type="primary"):
            if not new_pass or len(new_pass) < 6: st.warning("6+ chars")
            elif new_pass!= confirm_pass: st.error("No match")
            else:
                try: supabase.auth.update_user({"password": new_pass}); st.success("✅ Updated!"); st.balloons()
                except Exception as e: st.error(str(e))
    st.divider()
    g = st.session_state.geo
    st.markdown(f"#### 💰 Plans ({g['code']}) - Keep Portfolio")
    email = st.text_input("Email for receipt:", value=YOUR_EMAIL, key="pay_email_700")
    if not st.session_state.pay_links and email:
        with st.spinner("Loading..."):
            for plan, amt in [("ONCE10",1000),("WEEK49",4900),("MONTH99",9900),("YEAR799",79900)]:
                res = init_paystack(email, amt, plan)
                if res.get("status"): st.session_state.pay_links[plan]=res["data"]["authorization_url"]; st.session_state.pay_refs[plan]=res["data"]["reference"]
    if st.session_state.pay_links:
        st.link_button(f"💳 Once {g['symbol']}{g['once']} - 10 grades", st.session_state.pay_links.get("ONCE10","#"), use_container_width=True)
        st.link_button(f"💳 Weekly {g['symbol']}{g['weekly']}", st.session_state.pay_links.get("WEEK49","#"), use_container_width=True)
        st.link_button(f"⭐ Monthly {g['symbol']}{g['monthly']} - Keep Portfolio", st.session_state.pay_links.get("MONTH99","#"), use_container_width=True)
        st.link_button(f"💳 Yearly {g['symbol']}{g['yearly']}", st.session_state.pay_links.get("YEAR799","#"), use_container_width=True)
        if st.button("✅ Check Payment - Unlock", type="primary", use_container_width=True):
            if verify_all_refs(): st.rerun()
    st.divider()
    st.markdown("#### 🌎 7 Languages = 6M teachers")
    st.session_state.feedback_lang = st.selectbox("Parent Feedback Language:", ["English","Spanish","Portuguese","French","Arabic","Hindi","Chinese"], index=["English","Spanish","Portuguese","French","Arabic","Hindi","Chinese"].index(st.session_state.feedback_lang))
    st.session_state.grading_standard = st.selectbox("Standard:", ["CEFR","IELTS","TOEFL","US Grade"], index=["CEFR","IELTS","TOEFL","US Grade"].index(st.session_state.grading_standard))

tab4, tab1, tab3, tab2, tab5, tab6 = st.tabs(["📚 Portfolio - Keep if PRO","✍️ Grade Essay","📸 Photo/PDF - Handwriting","⚡ Batch 15 PRO","📘 Guide","🚀 SUPER 7Lang"])

with tab4:
    st.markdown("### 📚 Your Class Portfolio - This is why you pay monthly. Cancel = lose this.")
    try:
        rows=supabase.table("essays").select("*").eq("teacher_id",st.session_state.teacher_id).order("created_at",desc=True).limit(200).execute()
        if rows.data:
            df=pd.DataFrame(rows.data)
            c1,c2,c3=st.columns(3)
            c1.metric("Essays Saved", len(df)); c2.metric("Avg Score", f"{df['score'].mean():.1f}/10"); c3.metric("Students", df['student_name'].nunique())
            if len(df)>1:
                fig, ax = plt.subplots(); df_sorted=df.sort_values('created_at'); ax.plot(pd.to_datetime(df_sorted['created_at']), df_sorted['score'], marker='o'); ax.set_ylabel("Score/10"); plt.xticks(rotation=25); st.pyplot(fig)
            st.dataframe(df[["student_name","level","score","cefr","created_at"]], use_container_width=True)
            if not is_pro():
                st.warning("🔒 Excel export + Principal PDF + Full history need PRO - upgrade to keep portfolio safe")
            else:
                excel_df = df[["student_name","score","cefr","level"]]
                b,_ = df_to_excel_bytes_safe(excel_df, "Portfolio"); st.download_button("📥 Export Portfolio Excel (PRO)", b, file_name="Portfolio.xlsx", use_container_width=True)
        else: st.info("No essays yet. Grade your first essay — it lives here forever. Build portfolio → parents & HOD love it.")
    except Exception as e: st.error(f"History error: {e}")

with tab1:
    essay = st.text_area("Paste Essay:", height=150, placeholder="Paste student essay..."); s_name = st.text_input("Student Name:", value="Student", key="s_name_single"); level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level")
    if st.button("🚀 GRADE & SAVE TO PORTFOLIO ->", type="primary", use_container_width=True):
        if not is_pro() and st.session_state.uses>=3: st.error("Free limit reached. Upgrade to keep portfolio."); st.stop()
        if not essay.strip(): st.warning("Paste essay first"); st.stop()
        with st.spinner("Grading & saving to portfolio..."):
            try:
                result_text = grade_with_groq(essay, level); score, cefr, _ = extract_score_cefr(result_text); ai_flag = detect_ai_risk(essay)
                save_essay_db(s_name, essay, level, score, cefr, result_text)
                if not is_pro(): st.session_state.uses+=1
                st.success(f"Saved to {s_name} portfolio: {score}/10 {cefr}"); st.markdown(f"**AI Check:** {ai_flag}"); st.markdown(result_text)
                st.download_button("📄 Parent Report PDF", create_branded_pdf(essay, result_text, level, s_name), file_name=f"Report_{s_name}_{level}.pdf", use_container_width=True)
            except Exception as e: st.error(f"Grading error: {e}")

with tab3:
    st.markdown("### 📸 Photo/PDF - Grade 40 handwritten books with phone. Brazil/India NEED this.")
    level_p=st.selectbox("Target Level:",["A1","A2","B1","B2","C1","C2"],key="photo_level")
    camera_pic=st.camera_input("Take photo"); upload_img=st.file_uploader("Upload Image",type=["jpg","jpeg","png"],key="img_up_700"); upload_pdf=st.file_uploader("Upload PDF",type=["pdf"],key="pdf_up_700")
    image_bytes=None
    if camera_pic: image_bytes=camera_pic.getvalue()
    elif upload_img: image_bytes=upload_img.getvalue()
    if image_bytes: st.image(image_bytes,use_container_width=True)
    if upload_pdf:
        extracted=extract_text_from_pdf(upload_pdf.getvalue()); st.text_area("Text from PDF:",value=extracted,height=120, key="pdf_text_700")
        if st.button("GRADE PDF TEXT -> Save to Portfolio", type="primary", use_container_width=True):
            try:
                result_text=grade_with_groq(extracted,level_p); score,cefr,_=extract_score_cefr(result_text); save_essay_db("PDF Student",extracted,level_p,score,cefr,result_text); st.markdown(result_text)
            except Exception as e: st.error(str(e))
    if image_bytes and st.button("READ & GRADE PHOTO ->", use_container_width=True):
        with st.spinner("Reading handwriting with Qwen..."): extracted=extract_text_from_image(image_bytes); st.session_state['last_ocr']=extracted; st.rerun()
    if 'last_ocr' in st.session_state:
        edited=st.text_area("Edit OCR (fix reading errors):",value=st.session_state['last_ocr'],height=120)
        if st.button("GRADE THIS TEXT -> Save to Portfolio", type="primary", use_container_width=True):
            try:
                result_text=grade_with_groq(edited,level_p); score,cefr,_=extract_score_cefr(result_text); save_essay_db("Photo Student",edited,level_p,score,cefr,result_text); st.markdown(result_text)
            except Exception as e: st.error(str(e))

with tab2:
    st.markdown("### ⚡ Batch 15 PRO - Safe batch, saves after each essay (no crash)")
    sample_df = pd.DataFrame({"student_name":["Thandi","John","Aisha"],"essay":["I go to market yesterday.","My best friend is Thandi.","I broken my leg last week."]})
    b,_ = df_to_excel_bytes_safe(sample_df,"Essays"); st.download_button("📥 Download Template", b, file_name="Template.xlsx", use_container_width=True)
    school_name = st.text_input("School Name:", value="My School", key="school_name_700"); level_b = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="batch_level_700")
    uploaded = st.file_uploader("Upload Excel/CSV (max 15)", type=["csv","xlsx","txt"], key="batch_file_700")
    if st.button("🚀 GRADE BATCH 15 -> Save to Portfolio", type="primary", use_container_width=True):
        if not is_pro(): st.error("Batch needs PRO - Upgrade to keep portfolio"); st.stop()
        if not uploaded: st.warning("Upload first"); st.stop()
        essays=[]; names=[]
        try:
            if uploaded.name.endswith(".csv"): df=pd.read_csv(uploaded); essay_col="essay" if "essay" in df.columns else df.columns[-1]; name_col="student_name" if "student_name" in df.columns else df.columns[0]; essays=df[essay_col].astype(str).tolist()[:15]; names=df[name_col].astype(str).tolist()[:15]
            elif uploaded.name.endswith(".xlsx"): df=pd.read_excel(uploaded); essay_col="essay" if "essay" in df.columns else df.columns[-1]; name_col="student_name" if "student_name" in df.columns else df.columns[0]; essays=df[essay_col].astype(str).tolist()[:15]; names=df[name_col].astype(str).tolist()[:15]
            else: content=uploaded.read().decode("utf-8", errors="ignore"); essays=[e.strip() for e in content.split("\n") if e.strip()][:15]; names=[f"Student {i+1}" for i in range(len(essays))]
        except Exception as e: st.error(f"Read error: {e}"); st.stop()
        results=[]; excel_rows=[]; progress=st.progress(0)
        for i,es in enumerate(essays):
            try:
                res_text=grade_with_groq(es[:2000],level_b); score,cefr,_=extract_score_cefr(res_text); ai_flag=detect_ai_risk(es)
                save_essay_db(names[i],es,level_b,score,cefr,res_text); clean_res=clean_feedback_for_excel(res_text)
                results.append({"Student":names[i],"Score":f"{score}/10","CEFR":cefr,"AI_Flag":ai_flag}); excel_rows.append({"Student Name":names[i],"Score /10":score,"CEFR":cefr,"AI Check":ai_flag,"Full Feedback":clean_res[:1000]})
            except Exception as e:
                results.append({"Student":names[i],"Score":"Error","CEFR":"Error","AI_Flag":str(e)[:30]})
            progress.progress((i+1)/len(essays))
        st.session_state.batch_results={"results":results,"excel_rows":excel_rows,"level":level_b,"school":school_name}
        st.success(f"Done {len(results)} - all saved to portfolio even if one fails")
    if st.session_state.batch_results:
        results=st.session_state.batch_results["results"]; excel_rows=st.session_state.batch_results["excel_rows"]; level_b=st.session_state.batch_results["level"]; school_name=st.session_state.batch_results["school"]
        avg_score=sum([r["Score /10"] for r in excel_rows if isinstance(r["Score /10"], int)])/len(excel_rows) if excel_rows else 0
        st.markdown(f"### Avg {avg_score:.1f}/10 - {len(results)} graded - saved to portfolio")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
        if is_pro():
            st.download_button("📄 Principal PDF (PRO)", create_principal_pdf(excel_rows, level_b, avg_score, school_name), file_name=f"Principal_{school_name}.pdf", use_container_width=True)
        else:
            st.warning("Principal PDF needs PRO")

with tab5:
    st.markdown("## 📘 Why 6M teachers need this, not just grading")
    st.table(pd.DataFrame([{"Lang":"Portuguese","Market":"Brazil 500k teachers","NEED":"Parent letter in PT from photo"},{"Lang":"Spanish","Market":"Mexico/Spain 300k","NEED":"Photo handwritten homework"},{"Lang":"Arabic","Market":"MENA 400k","NEED":"IELTS track + principal report"},{"Lang":"Hindi","Market":"India 600k","NEED":"40 notebooks phone grade"},{"Lang":"English","Market":"SA/US/UK","NEED":"Portfolio for HOD"}]))

with tab6:
    st.markdown("## 🚀 SUPER 7Lang - One click set market")
    c1,c2,c3=st.columns(3)
    with c1:
        if st.button("🇧🇷 Set Brazil", use_container_width=True, key="set_br_700"): st.session_state.feedback_lang="Portuguese"; st.session_state.grading_standard="CEFR"; st.success("PT+CEFR - Brazil ready"); st.balloons()
    with c2:
        if st.button("🇸🇦 Set Arabic", use_container_width=True, key="set_ar_700"): st.session_state.feedback_lang="Arabic"; st.session_state.grading_standard="IELTS"; st.success("AR+IELTS - MENA ready")
    with c3:
        if st.button("🇮🇳 Set Hindi", use_container_width=True, key="set_in_700"): st.session_state.feedback_lang="Hindi"; st.session_state.grading_standard="IELTS"; st.success("HI+IELTS - India ready")

st.caption("TEFLMate v7.1 - Fixed crash [3,1] + Fixed recovery + Qwen locked + Portfolio first")
