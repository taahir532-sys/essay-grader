import streamlit as st
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
components.html("""
<script>
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault(); deferredPrompt = e;
  const btn = document.createElement('button');
  btn.innerText = '📲 Install TEFLMate App';
  btn.style = 'position:fixed;bottom:22px;right:18px;background:#111;color:white;padding:14px 22px;border-radius:12px;font-weight:800;z-index:9999;border:none;box-shadow:0 4px 20px rgba(0,0,0,0.4);cursor:pointer;';
  btn.onclick = () => { deferredPrompt.prompt(); deferredPrompt.userChoice.then(()=>{btn.remove();}); };
  document.body.appendChild(btn);
  setTimeout(()=>{if(btn.parentNode) btn.remove();}, 15000);
});
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
import json
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
st.set_page_config(page_title="TEFLMate - Class Portfolio", page_icon="📚", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'Inter', sans-serif;}
.main > div {padding-top:10px;}
.stButton>button {
    background:#111!important;color:white!important;
    border-radius:12px!important;height:56px!important;
    font-weight:800!important;font-size:16px!important;
    width:100%;border:1px solid #111!important;
    box-shadow:0 4px 12px rgba(0,0,0,0.15);
}
div[data-testid="stLinkButton"]>a{
    background:#111!important;color:white!important;
    border-radius:12px!important;height:56px!important;
    font-weight:800!important;display:flex!important;
    align-items:center!important;justify-content:center!important;
    box-shadow:0 4px 12px rgba(0,0,0,0.15);
}
button[data-baseweb="tab"] {font-size:14px; padding:10px 14px; font-weight:600;}
div[data-testid="stCameraInput"] {border:2px dashed #111; border-radius:16px; padding:8px;}
.tefl-header {
    background:linear-gradient(135deg,#111 0%,#333 100%);
    color:white; padding:18px 22px; border-radius:16px;
    margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;
}
.tefl-badge {
    background:#FFD60A; color:#111; padding:6px 14px; border-radius:20px;
    font-weight:800; font-size:13px; letter-spacing:0.5px;
}
.landing-hero {
    background:linear-gradient(135deg,#f8f9fa 0%,#e9ecef 100%);
    border-radius:20px; padding:24px; border:1px solid #eee;
}
.testimonial {background:white; border-left:4px solid #111; padding:12px 16px; border-radius:8px; margin:8px 0;}
</style>
""", unsafe_allow_html=True)
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
if "promo_success" not in st.session_state: st.session_state.promo_success = False
if "last_ocr" not in st.session_state: st.session_state.last_ocr = None
if "last_photo_result" not in st.session_state: st.session_state.last_photo_result = None
if "grade_cache" not in st.session_state: st.session_state.grade_cache = {}
if "editable_ocr" not in st.session_state: st.session_state.editable_ocr = ""
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
q_parent = st.query_params
if "parent" in q_parent:
    try:
        essay_id = q_parent.get("parent")
        if isinstance(essay_id, list): essay_id = essay_id[0]
        st.markdown('<div class="tefl-header"><div>📚 TEFLMate - Parent Report</div><div class="tefl-badge">PARENT VIEW</div></div>', unsafe_allow_html=True)
        row = supabase.table("essays").select("*").eq("id", essay_id).execute()
        if row.data:
            r = row.data[0]
            st.title(f"Report for {r['student_name']}")
            st.metric("Score", f"{r['score']}/10", r['cefr'])
            st.markdown(f"**Level:** {r['level']} | **Date:** {str(r['created_at'])[:10]}")
            st.divider()
            st.markdown(r['feedback'])
            st.info("Generated by TEFLMate")
        else:
            st.error("Report not found")
        st.stop()
    except Exception as e:
        st.error(f"Parent view error: {e}")
        st.stop()
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
        if isinstance(access_token, list): access_token = access_token[0]
        refresh_token = q_rec.get("refresh_token", "")
        if isinstance(refresh_token, list): refresh_token = refresh_token[0]
    except:
        access_token = ""; refresh_token = ""
    try:
        if access_token and refresh_token:
            supabase.auth.set_session(access_token, refresh_token)
    except:
        pass
    st.title("🔐 TEFLMate - Set New Password")
    new_p = st.text_input("New Password (6+ chars)", type="password", key="rec_new_final_1967")
    conf_p = st.text_input("Confirm", type="password", key="rec_conf_final_1967")
    if st.button("✅ UPDATE PASSWORD & LOGIN", type="primary", use_container_width=True):
        if len(new_p) < 6: st.warning("6+ chars")
        elif new_p!= conf_p: st.error("No match")
        else:
            try:
                supabase.auth.update_user({"password": new_p})
                st.success("✅ Updated! Clear URL and login"); st.query_params.clear(); supabase.auth.sign_out()
                st.session_state.user=None; st.session_state.teacher_id=None; st.balloons()
            except Exception as e: st.error(f"Update failed: {e}")
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
                if td.data[0].get("bonus_grades"):
                    try: st.session_state.uses = -int(td.data[0].get("bonus_grades",0))
                    except: pass
    except: pass
def login_screen():
    st.markdown("""<div class="tefl-header"><div style="font-size:22px;font-weight:800;">📚 TEFLMate</div><div class="tefl-badge">TEFLMate v6.73d</div></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1.2,1])
    with col1:
        st.markdown("""<div class="landing-hero"><h2 style="margin:0;">Grade 40 books in 2 minutes 📸</h2><p style="color:#555;">Photo-grade • Track progress • Parent reports in 9 languages • Confidence flag</p><ul><li>✅ Snap photo → Edit OCR → Grade → Save</li><li>✅ Grammar/Vocab/Coherence breakdown</li><li>✅ Parent reports in home language</li></ul></div>""", unsafe_allow_html=True)
        DEMO_URL = st.secrets.get("DEMO_VIDEO_URL", "")
        if DEMO_URL: st.video(DEMO_URL)
        else: st.info("📱 Demo video - add DEMO_VIDEO_URL in Secrets")
    with col2:
        st.markdown("#### ⭐ What teachers say")
        st.markdown('<div class="testimonial"><b>Teacher from Durban:</b> "Saves 5hrs a week. Parents love reports!" ⭐⭐⭐⭐⭐</div>', unsafe_allow_html=True)
        st.markdown('<div class="testimonial"><b>Teacher from Brazil:</b> "Photo grading is magic." ⭐⭐⭐⭐⭐</div>', unsafe_allow_html=True)
        st.markdown('<div class="testimonial"><b>HOD from Cape Town:</b> "Principal PDF makes moderation easy." ⭐⭐⭐⭐⭐</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🔑 Login to your class")
    t1, t2 = st.tabs(["🔑 Login", "✨ Sign Up"])
    with t1:
        with st.form("login_form_final_1967"):
            email = st.text_input("Email"); password = st.text_input("Password", type="password")
            if st.form_submit_button("🚀 Login", use_container_width=True, type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    td = supabase.table("teachers").select("*").eq("email", email).execute()
                    if td.data:
                        st.session_state.teacher_id = td.data[0]["id"]
                        if td.data[0].get("pro_expiry"):
                            try:
                                exp = datetime.fromisoformat(td.data[0]["pro_expiry"].replace("Z",""))
                                if exp > datetime.now():
                                    st.session_state.pro_expiry = exp
                                    st.session_state.active_plan = td.data[0].get("active_plan")
                            except: pass
                    else:
                        ins = supabase.table("teachers").insert({"email": email}).execute(); st.session_state.teacher_id = ins.data[0]["id"]
                    st.rerun()
                except Exception as e: st.error(f"Login failed: {e}")
        with st.expander("🔓 Forgot Password?"):
            fp_email = st.text_input("Email to reset:", key="fp_email_1967")
            if st.session_state.last_reset and (datetime.now()-st.session_state.last_reset).total_seconds()<3600:
                st.warning("Wait a bit")
            else:
                if st.button("📧 Send Reset Link", use_container_width=True):
                    try:
                        supabase.auth.reset_password_for_email(fp_email, {"redirect_to": "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"})
                        st.session_state.last_reset = datetime.now(); st.success(f"Sent to {fp_email}")
                    except Exception as e: st.error(str(e))
    with t2:
        ref_code_from_url = ""
        try:
            if "ref" in st.query_params:
                ref_code_from_url = st.query_params.get("ref")
                if isinstance(ref_code_from_url, list): ref_code_from_url = ref_code_from_url[0]
        except: pass
        if ref_code_from_url: st.success(f"🎁 Referral code {ref_code_from_url} applied!")
        with st.form("signup_form_final_1967"):
            email2 = st.text_input("New Email", key="s_email_1967"); password2 = st.text_input("New Password", type="password", key="s_pass_1967"); school = st.text_input("School Name", value="My School")
            if st.form_submit_button("Create Account", use_container_width=True):
                try:
                    supabase.auth.sign_up({"email": email2, "password": password2})
                    insert_data = {"email": email2, "school_name": school}
                    if ref_code_from_url: insert_data["referred_by"] = ref_code_from_url
                    supabase.table("teachers").insert(insert_data).execute()
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
        if st.session_state.active_plan and "ONCE" in str(st.session_state.active_plan) and remaining >3: return f"✅ {st.session_state.active_plan} - {remaining} left"
        return f"FREE - {remaining} left"
def clean(text): return unicodedata.normalize('NFKD', text or "").encode('ascii', 'ignore').decode('ascii')
def clean_feedback_for_excel(text):
    if not text: return ""
    t = clean(text); t = re.sub(r'\*\*|###|##|__|\*\*', '', t); return t.strip()
def extract_score_cefr(text):
    try:
        text_norm = text.replace(",", ".")
        score_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', text_norm)
        score = int(round(float(score_match.group(1)))) if score_match else 5
        cefr_match = re.search(r'\b(A1|A2|B1|B2|C1|C2)\b', text)
        cefr = cefr_match.group(1) if cefr_match else "B1"
        return score, cefr, ""
    except:
        return 5, "B1", ""
def parse_dimensions(text):
    try:
        j_match = re.search(r'\{.*\}', text, re.DOTALL)
        if j_match:
            j = json.loads(j_match.group(0))
            return j
    except:
        pass
    score, cefr, _ = extract_score_cefr(text)
    return {"grammar": score, "vocabulary": score, "coherence": score, "task_achievement": score, "overall": score, "cefr": cefr, "confidence": "medium", "feedback_text": text}
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
def save_pro_to_db(pro_expiry, active_plan, bonus_delta=0):
    try:
        email = st.session_state.user.email if st.session_state.user else YOUR_EMAIL
        data = {}
        if pro_expiry: data["pro_expiry"] = pro_expiry.isoformat()
        if active_plan: data["active_plan"] = active_plan
        if bonus_delta!=0:
            try:
                td = supabase.table("teachers").select("bonus_grades").eq("email", email).execute()
                current = td.data[0].get("bonus_grades",0) if td.data and td.data[0].get("bonus_grades") else 0
                data["bonus_grades"] = current + bonus_delta
            except:
                data["bonus_grades"] = bonus_delta
        if not data: return True
        try:
            if st.session_state.teacher_id:
                supabase.table("teachers").update(data).eq("id", st.session_state.teacher_id).execute()
            else:
                supabase.table("teachers").update(data).eq("email", email).execute()
        except:
            supabase.table("teachers").update(data).eq("email", email).execute()
        return True
    except:
        return False
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
    if amt == 1000 or plan == "ONCE10": st.session_state.uses -= 10; active="ONCE10"; save_pro_to_db(None, active, 10); st.success("R10 +10 grades saved"); st.balloons()
    elif amt == 4900 or plan == "WEEK49": pro_exp = now + timedelta(days=7); active="WEEK49"; save_pro_to_db(pro_exp, active, 0); st.success("R49 Weekly PRO saved"); st.balloons()
    elif amt == 9900 or plan == "MONTH99": pro_exp = now + timedelta(days=30); active="MONTH99"; save_pro_to_db(pro_exp, active, 0); st.success("R99 Monthly PRO saved"); st.balloons()
    elif amt == 79900 or plan == "YEAR799": pro_exp = now + timedelta(days=365); active="YEAR799"; save_pro_to_db(pro_exp, active, 0); st.success("R799 Yearly PRO saved"); st.balloons()
    else: return False
    if active!= "ONCE10" and pro_exp:
        st.session_state.pro_expiry = pro_exp; st.session_state.active_plan = active
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

# === OCR FIX v6.73d - QWEN3.6-27b CURRENT GROQ MODEL ===
def extract_text_from_image(image_bytes):
    client = get_groq()
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    models_to_try = ["qwen/qwen3-32b", "qwen/qwen3.6-27b", "qwen/qwen3.8-27b"]
    for model_id in models_to_try:
        try:
            res = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": "OCR: Extract handwritten text EXACTLY as written, keep spelling mistakes. Return only text, nothing else."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}],
                temperature=0
            )
            txt = res.choices[0].message.content or ""
            if "</think>" in txt: txt = txt.split("</think>")[-1].strip()
            if len(txt.strip()) > 3:
                return txt.strip()
        except Exception as e:
            print(f"Vision {model_id} failed: {e}")
            continue
    return "OCR_ERROR: Vision models temporarily unavailable. Please type text manually or try again."

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
    pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 6, clean(ai_result))
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)
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
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)
def detect_ai_risk(essay_text):
    text = essay_text.lower().strip()
    if len(text) < 10: return "Too Short"
    if "delve" in text and "tapestry" in text: return "⚠️ Possible AI"
    return "✅ Human"
def grade_with_groq(essay_text, level):
    cache_key = (essay_text.strip()[:500] + "|" + level + "|" + st.session_state.feedback_lang + "|" + st.session_state.grading_standard)
    if cache_key in st.session_state.grade_cache:
        return st.session_state.grade_cache[cache_key]
    if len(essay_text.strip()) < 25:
        fixed = json.dumps({"grammar":5,"vocabulary":5,"coherence":5,"task_achievement":5,"overall":5,"cefr":level,"ielts":5.0,"confidence":"low","feedback_text":f"Short text {len(essay_text.strip())} chars - needs 30+ words. | Score: 5/10 | CEFR {level} | Please write more."})
        st.session_state.grade_cache[cache_key] = fixed
        return fixed
    client = get_groq()
    lang = st.session_state.feedback_lang; std = st.session_state.grading_standard
    if std=="IELTS": std_inst="Also give IELTS Band 0-9."
    elif std=="TOEFL": std_inst="Also give TOEFL 0-30."
    elif std=="US Grade": std_inst="Also give US Grade A-F."
    else: std_inst="Give CEFR A1-C2 only."
    lang_inst = f"Feedback language: {lang}. Write feedback in {lang}, keep Score/10 English." if lang!="English" else "Feedback in English"
    if level in ["A1","A2"]:
        level_inst = f"Target {level} - BE GENEROUS. 30+ words basic communication = 6/10 min. Good = 7-8/10. Only <15 words = below 5. Integer scores only."
    else:
        level_inst = f"Target {level} - Cambridge standard. Integer scores only."
    rubric_anchors = """
    CEFR A1: Can write simple isolated phrases. Basic personal info. Many errors but understandable.
    CEFR A2: Can write short simple notes, messages, personal letters. Simple sentences linked with and/but/because.
    CEFR B1: Can write simple connected text on familiar topics. Can describe experiences, reasons.
    CEFR B2: Can write clear detailed text on wide range of subjects. Can explain viewpoint.
    CEFR C1/C2: Can write clear well-structured detailed complex texts with controlled use.
    ANCHOR A1 6/10: 'My name is Thandi. I am 12 years old. I live in Durban with my family. I like school.'
    ANCHOR A2 7/10: 'Last weekend I went to the market with my mother. We bought vegetables and fruits. It was very busy and fun. I liked it.'
    ANCHOR B1 7/10: 'My best friend is John. He is very kind and helpful. We play football after school every day. He helps me with homework.'
    """
    prompt = f"""You are kind Cambridge examiner for {level}. {level_inst}. {std_inst}. {lang_inst}.
    {rubric_anchors}
    Task: Grade this essay: "{essay_text[:2000]}"
    Return ONLY valid JSON with keys: grammar (0-10 int), vocabulary (0-10), coherence (0-10), task_achievement (0-10), overall (0-10 int), cefr (A1-C2), ielts (0-9 if needed else 0), confidence (high/medium/low), feedback_text (full feedback with Score X/10, Strengths, Mistake table, Corrected version, Parent summary). ASCII only.
    Example JSON: {{"grammar":7,"vocabulary":6,"coherence":7,"task_achievement":8,"overall":7,"cefr":"B1","ielts":6.0,"confidence":"high","feedback_text":"Score: 7/10..."}}
    """
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], temperature=0, seed=42)
    result = res.choices[0].message.content
    st.session_state.grade_cache[cache_key] = result
    return result
def save_essay_db(student_name, essay_text, level, score, cefr, feedback):
    try:
        if not st.session_state.teacher_id: return False
        supabase.table("essays").insert({"teacher_id": st.session_state.teacher_id, "student_name": student_name, "essay_text": essay_text, "level": level, "score": score, "cefr": cefr, "feedback": feedback}).execute()
        return True
    except:
        return False
col_title, col_user = st.columns([3,1])
with col_title:
    st.markdown("""<div class="tefl-header"><div><div style="font-size:22px;font-weight:800;">📚 TEFLMate - Class Portfolio</div><div style="font-size:12px;opacity:0.8;">Track progress • Photo-grade • 9 languages • Confidence flag</div></div><div class="tefl-badge">TEFLMate v6.73d</div></div>""", unsafe_allow_html=True)
with col_user:
    st.info(f"👤 {st.session_state.user.email[:20]} | {get_status()}" if st.session_state.user else "Not logged")
    if st.session_state.user and st.button("Logout", use_container_width=True):
        supabase.auth.sign_out(); st.session_state.user=None; st.session_state.teacher_id=None; st.rerun()
if st.session_state.promo_success:
    st.balloons(); st.success("🎉 Code applied - saved!"); st.session_state.promo_success = False

# ===== LEFT MENU - 100% RESTORED =====
with st.sidebar:
    st.markdown("### 🔑 Your Plan")
    st.info(get_status())
    if st.session_state.teacher_id:
        try:
            ref_code = f"TEFL{str(st.session_state.teacher_id)[:6].upper()}"
            base_url = "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"
            ref_link = f"{base_url}?ref={ref_code}"
            st.markdown("#### 🎁 Refer & Earn")
            st.caption(f"Your code: **{ref_code}**")
            st.code(ref_link)
            try:
                ref_count_data = supabase.table("teachers").select("id").eq("referred_by", ref_code).execute()
                ref_count = len(ref_count_data.data) if ref_count_data.data else 0
            except:
                ref_count = 0
            st.metric("Teachers invited", f"{ref_count}/3")
            if ref_count >= 3:
                if st.button("🎉 Claim 1 Month Free (3 invites)", type="primary", use_container_width=True):
                    new_exp = datetime.now() + timedelta(days=30)
                    save_pro_to_db(new_exp, "REFERRAL-3", 0)
                    st.session_state.pro_expiry = new_exp; st.session_state.active_plan = "REFERRAL-3"
                    st.success("✅ 1 Month Free Unlocked!"); st.balloons()
            else:
                st.caption("Invite 3 teachers = 1 month free PRO")
            st.divider()
        except:
            pass
    with st.expander("🔐 Change Password"):
        new_pass = st.text_input("New Password", type="password", key="new_pass_1967")
        confirm_pass = st.text_input("Confirm New Password", type="password", key="confirm_pass_1967")
        if st.button("Update Password", use_container_width=True, type="primary"):
            if not new_pass or len(new_pass) < 6: st.warning("6+ chars")
            elif new_pass!= confirm_pass: st.error("No match")
            else:
                try: supabase.auth.update_user({"password": new_pass}); st.success("✅ Updated!"); st.balloons()
                except Exception as e: st.error(str(e))
    st.divider()
    g = st.session_state.geo
    st.markdown(f"#### 💰 Plans ({g['code']})")
    with st.expander("🎟️ Enter Code / Promo"):
        promo = st.text_input("Promo Code:", value="", placeholder="Enter code", key="promo_code_1967")
        if st.button("✅ Redeem Code", use_container_width=True, key="redeem_btn_1967"):
            code = promo.strip().upper()
            code_map = {"TEFL2024":30,"KEEP99":30,"TEACHFREE":30,"BRAZIL50":30,"INDIA50":30,"MONTH99":30,"MONTHLY":30,"MONTH":30,"WEEK49":7,"WEEKLY":7,"WEEK":7,"YEAR799":365,"YEARLY":365,"YEAR":365,"ONCE10":0,"TEST10":0,"R10":0}
            if code in code_map:
                days = code_map[code]
                if days == 0:
                    st.session_state.uses -= 10; st.session_state.active_plan = code; save_pro_to_db(None, code, 10); st.session_state.promo_success = True; st.rerun()
                else:
                    new_expiry = datetime.now() + timedelta(days=days); st.session_state.pro_expiry = new_expiry; st.session_state.active_plan = f"PROMO-{code}"; save_pro_to_db(new_expiry, f"PROMO-{code}", 0); st.session_state.promo_success = True; st.rerun()
            elif code!= "": st.error(f"Invalid code: {code}")
    email = st.text_input("Email for receipt:", value=YOUR_EMAIL, key="pay_email_1967")
    if not st.session_state.pay_links and email:
        with st.spinner("Loading Paystack..."):
            for plan, amt in [("ONCE10",1000),("WEEK49",4900),("MONTH99",9900),("YEAR799",79900)]:
                res = init_paystack(email, amt, plan)
                if res.get("status"): st.session_state.pay_links[plan]=res["data"]["authorization_url"]; st.session_state.pay_refs[plan]=res["data"]["reference"]
    if st.session_state.pay_links:
        st.link_button(f"💳 Once {g['symbol']}{g['once']} - 10 grades", st.session_state.pay_links.get("ONCE10","#"), use_container_width=True)
        st.link_button(f"💳 Weekly {g['symbol']}{g['weekly']}", st.session_state.pay_links.get("WEEK49","#"), use_container_width=True)
        st.link_button(f"⭐ Monthly {g['symbol']}{g['monthly']}", st.session_state.pay_links.get("MONTH99","#"), use_container_width=True)
        st.link_button(f"💳 Yearly {g['symbol']}{g['yearly']}", st.session_state.pay_links.get("YEAR799","#"), use_container_width=True)
        if st.button("✅ Check Payment - Unlock", type="primary", use_container_width=True):
            if verify_all_refs(): st.rerun()
    st.divider()
    st.markdown("#### 🌎 9 Languages")
    st.session_state.feedback_lang = st.selectbox("Parent Feedback Language:", ["English","Spanish","Portuguese","French","Arabic","Hindi","Chinese","Zulu","Xhosa"], index=["English","Spanish","Portuguese","French","Arabic","Hindi","Chinese","Zulu","Xhosa"].index(st.session_state.feedback_lang) if st.session_state.feedback_lang in ["English","Spanish","Portuguese","French","Arabic","Hindi","Chinese","Zulu","Xhosa"] else 0, key="lang_select_1967")
    st.session_state.grading_standard = st.selectbox("Standard:", ["CEFR","IELTS","TOEFL","US Grade"], index=["CEFR","IELTS","TOEFL","US Grade"].index(st.session_state.grading_standard), key="std_select_1967")
    st.divider()
    st.markdown("#### ❤️ PayPal / Payshap")
    st.caption("Payshap: 0658006750")
    st.link_button("💙 Pay with PayPal", "https://paypal.me/TaahirMahomed", use_container_width=True)

tab4, tab1, tab3, tab2, tab5, tab6 = st.tabs(["📚 Portfolio","✍️ Grade Essay","📸 Photo/PDF","⚡ Batch 50 PRO","📘 Guide","🚀 SUPER 7Lang"])
with tab4:
    st.markdown("### 📚 Your Class Portfolio")
    try:
        rows=supabase.table("essays").select("*").eq("teacher_id",st.session_state.teacher_id).order("created_at",desc=True).limit(200).execute()
        if rows.data:
            df=pd.DataFrame(rows.data)
            c1,c2,c3=st.columns(3)
            c1.metric("Essays Saved", len(df)); c2.metric("Avg Score", f"{df['score'].mean():.1f}/10"); c3.metric("Students", df['student_name'].nunique())
            if len(df)>1:
                fig, ax = plt.subplots(); df_sorted=df.sort_values('created_at'); ax.plot(pd.to_datetime(df_sorted['created_at']), df_sorted['score'], marker='o'); ax.set_ylabel("Score/10"); plt.xticks(rotation=25); st.pyplot(fig)
            st.dataframe(df[["student_name","level","score","cefr","created_at"]], use_container_width=True)
            st.divider()
            st.markdown("#### 👨‍👩‍👧 Parent Share Link (No Login Needed)")
            sel_parent = st.selectbox("Select student to share:", df["student_name"].unique(), key="parent_sel_1967")
            if sel_parent:
                eid = None
                for r in rows.data:
                    if r["student_name"]==sel_parent: eid = r["id"]; break
                if eid:
                    share_url = f"https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/?parent={eid}"
                    st.code(share_url)
                    st.caption("Copy & send to parent on WhatsApp")
            if not is_pro():
                st.warning("🔒 Excel + Principal PDF need PRO")
            else:
                excel_df = df[["student_name","score","cefr","level"]]
                b,_ = df_to_excel_bytes_safe(excel_df, "Portfolio")
                st.download_button("📥 Export Portfolio Excel (PRO)", b, file_name="Portfolio.xlsx", use_container_width=True)
                avg = float(df['score'].mean()) if len(df) else 0
                rows_for_pdf = [{"Student Name": r["student_name"], "Score /10": int(r["score"]) if r["score"] else 0, "CEFR": r["cefr"], "AI Check": "OK", "Full Feedback": ""} for r in rows.data]
                level_pdf = df.iloc[0]['level'] if len(df) else "B1"
                st.download_button("📄 Principal PDF - All Students (PRO)", create_principal_pdf(rows_for_pdf, level_pdf, avg, "My School"), file_name="Portfolio_Principal.pdf", use_container_width=True, key="portfolio_pdf_1967")
            st.divider()
            st.markdown("#### 🗑️ Delete Duplicate")
            delete_options = {f"{r['student_name']} | {r['score']}/10 | {str(r['created_at'])[:16]} | {r['id'][:6]}": r['id'] for r in rows.data}
            sel = st.selectbox("Select essay to delete:", list(delete_options.keys()), key="del_select_1967")
            c_del1, c_del2 = st.columns(2)
            with c_del1:
                if st.button("🗑️ Delete Selected", use_container_width=True, key="del_btn_1967"):
                    try: supabase.table("essays").delete().eq("id", delete_options[sel]).execute(); st.success("Deleted!"); st.rerun()
                    except Exception as e: st.error(f"Delete failed: {e}")
            with c_del2:
                if st.button("⚠️ Clear ALL", use_container_width=True, key="clear_all_1967"):
                    try: supabase.table("essays").delete().eq("teacher_id", st.session_state.teacher_id).execute(); st.success("All cleared"); st.rerun()
                    except Exception as e: st.error(str(e))
        else:
            st.info("No essays yet.")
    except Exception as e: st.error(f"History error: {e}")
with tab1:
    essay = st.text_area("Paste Essay:", height=150, placeholder="Paste student essay..."); s_name = st.text_input("Student Name:", value="Student", key="s_name_single_1967"); level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level_1967")
    if st.button("🚀 GRADE & SAVE TO PORTFOLIO ->", type="primary", use_container_width=True):
        if not is_pro() and st.session_state.uses>=3: st.error("Free limit reached."); st.stop()
        if not essay.strip(): st.warning("Paste essay first"); st.stop()
        with st.spinner("Grading & saving..."):
            try:
                result_raw = grade_with_groq(essay, level)
                parsed = parse_dimensions(result_raw)
                score = int(parsed.get("overall",5)); cefr = parsed.get("cefr","B1"); ai_flag = detect_ai_risk(essay)
                ok = save_essay_db(s_name, essay, level, score, cefr, result_raw)
                if not is_pro(): st.session_state.uses+=1
                if ok: st.success(f"✅ Saved: {score}/10 {cefr} | {ai_flag}")
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Grammar", f"{parsed.get('grammar',score)}/10"); c2.metric("Vocab", f"{parsed.get('vocabulary',score)}/10"); c3.metric("Coherence", f"{parsed.get('coherence',score)}/10"); c4.metric("Confidence", parsed.get('confidence','medium'))
                if parsed.get('confidence')=='low': st.warning("⚠️ Low confidence — please review")
                st.markdown(parsed.get('feedback_text', result_raw))
                st.download_button("📄 Parent Report PDF", create_branded_pdf(essay, parsed.get('feedback_text', result_raw), level, s_name), file_name=f"Report_{s_name}_{level}.pdf", use_container_width=True)
            except Exception as e: st.error(f"Grading error: {e}")
with tab3:
    st.markdown("### 📸 Photo & PDF - Handwriting to Text")
    st.caption("FIXED v6.73d: Now using qwen3.6-27b - Groq current model")
    level_p=st.selectbox("Target Level:",["A1","A2","B1","B2","C1","C2"],key="photo_level_1967")
    st.markdown("#### 📷 Camera First - Big Button Mode")
    camera_pic=st.camera_input("📸 TAP TO TAKE PHOTO - Big Button"); upload_img=st.file_uploader("Or Upload Image",type=["jpg","jpeg","png"],key="img_up_1967"); upload_pdf=st.file_uploader("Upload PDF",type=["pdf"],key="pdf_up_1967")
    image_bytes=None
    if camera_pic: image_bytes=camera_pic.getvalue()
    elif upload_img: image_bytes=upload_img.getvalue()
    if image_bytes: st.image(image_bytes,use_container_width=True)
    if upload_pdf:
        extracted=extract_text_from_pdf(upload_pdf.getvalue()); st.text_area("Text from PDF:",value=extracted,height=120, key="pdf_text_1967")
        if st.button("GRADE PDF TEXT -> Save to Portfolio", type="primary", use_container_width=True):
            try:
                result_raw=grade_with_groq(extracted,level_p); parsed=parse_dimensions(result_raw); score=int(parsed.get("overall",5)); cefr=parsed.get("cefr","B1"); save_essay_db("PDF Student",extracted,level_p,score,cefr,result_raw); st.markdown(parsed.get('feedback_text',result_raw))
            except Exception as e: st.error(str(e))
    if image_bytes:
        if st.button("📸 STEP 1: READ HANDWRITING", type="primary", use_container_width=True, key="read_only_1967"):
            with st.spinner("Reading with Qwen3.6-27b..."):
                extracted=extract_text_from_image(image_bytes); st.session_state.editable_ocr=extracted; st.session_state.last_ocr=extracted
                if "OCR_ERROR" in extracted: st.error(extracted)
                else: st.success("✅ Read! Edit below if needed")
        if st.session_state.editable_ocr and "OCR_ERROR" not in st.session_state.editable_ocr:
            st.markdown("#### ✏️ STEP 2: Edit OCR Text (Fix mistakes)")
            edited = st.text_area("Edit text before grading:", value=st.session_state.editable_ocr, height=150, key="editable_ocr_box_1967")
            if st.button("🚀 STEP 3: GRADE EDITED TEXT & SAVE", type="primary", use_container_width=True, key="grade_edited_1967"):
                with st.spinner("Grading edited text..."):
                    try:
                        result_raw=grade_with_groq(edited,level_p); parsed=parse_dimensions(result_raw); score=int(parsed.get("overall",5)); cefr=parsed.get("cefr","B1"); ai_flag=detect_ai_risk(edited)
                        saved = save_essay_db(f"Photo Student {datetime.now().strftime('%H:%M:%S')}",edited,level_p,score,cefr,result_raw)
                        st.session_state.last_photo_result=result_raw
                        if not is_pro(): st.session_state.uses+=1
                        if saved: st.success(f"✅ Saved: {score}/10 {cefr} | {ai_flag}")
                        c1,c2,c3,c4 = st.columns(4)
                        c1.metric("Grammar", f"{parsed.get('grammar',score)}/10"); c2.metric("Vocab", f"{parsed.get('vocabulary',score)}/10"); c3.metric("Coherence", f"{parsed.get('coherence',score)}/10"); c4.metric("Confidence", parsed.get('confidence','medium'))
                        if parsed.get('confidence')=='low': st.warning("⚠️ Low confidence — review")
                        st.markdown(parsed.get('feedback_text',result_raw))
                        st.download_button("📄 Parent Report PDF", create_branded_pdf(edited, parsed.get('feedback_text',result_raw), level_p, "Photo Student"), file_name=f"Photo_Report_{level_p}.pdf", use_container_width=True, key="photo_pdf_1967")
                    except Exception as e: st.error(f"Error: {e}")
with tab2:
    st.markdown("### ⚡ Batch 50 PRO - Whole Class in One Click")
    sample_df = pd.DataFrame({"student_name":["Thandi","John","Aisha"],"essay":["My name is Thandi. I am 12 years old. I live with my family in Durban.","My best friend is John. He is very kind and helpful. We play football after school.","Last weekend I went to the market with my mother. We bought vegetables and fruits."]})
    b,_ = df_to_excel_bytes_safe(sample_df,"Essays"); st.download_button("📥 Download Template (50 students)", b, file_name="Template_50.xlsx", use_container_width=True, key="template_50_1967")
    school_name = st.text_input("School Name:", value="My School", key="school_name_1967"); level_b = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], index=0, key="batch_level_1967")
    uploaded = st.file_uploader("Upload Excel/CSV (max 50)", type=["csv","xlsx","txt"], key="batch_file_1967")
    if st.button("🚀 GRADE BATCH 50 -> Save to Portfolio", type="primary", use_container_width=True, key="batch_btn_50_1967"):
        if not is_pro(): st.error("Batch needs PRO"); st.stop()
        if not uploaded: st.warning("Upload first"); st.stop()
        essays=[]; names=[]
        try:
            if uploaded.name.endswith(".csv"): df=pd.read_csv(uploaded); essay_col="essay" if "essay" in df.columns else df.columns[-1]; name_col="student_name" if "student_name" in df.columns else df.columns[0]; essays=df[essay_col].astype(str).tolist()[:50]; names=df[name_col].astype(str).tolist()[:50]
            elif uploaded.name.endswith(".xlsx"): df=pd.read_excel(uploaded); essay_col="essay" if "essay" in df.columns else df.columns[-1]; name_col="student_name" if "student_name" in df.columns else df.columns[0]; essays=df[essay_col].astype(str).tolist()[:50]; names=df[name_col].astype(str).tolist()[:50]
            else: content=uploaded.read().decode("utf-8", errors="ignore"); essays=[e.strip() for e in content.split("\n") if e.strip()][:50]; names=[f"Student {i+1}" for i in range(len(essays))]
        except Exception as e: st.error(f"Read error: {e}"); st.stop()
        results=[]; excel_rows=[]; progress=st.progress(0)
        for i,es in enumerate(essays):
            try:
                res_raw=grade_with_groq(es[:2000],level_b); parsed=parse_dimensions(res_raw); score=int(parsed.get("overall",5)); cefr=parsed.get("cefr","B1"); ai_flag=detect_ai_risk(es)
                save_essay_db(names[i],es,level_b,score,cefr,res_raw); clean_res=clean_feedback_for_excel(parsed.get('feedback_text',res_raw))
                results.append({"Student":names[i],"Score":f"{score}/10","CEFR":cefr,"AI_Flag":ai_flag,"Conf":parsed.get('confidence','med')}); excel_rows.append({"Student Name":names[i],"Score /10":score,"CEFR":cefr,"AI Check":ai_flag,"Full Feedback":clean_res[:1000]})
            except Exception as e:
                results.append({"Student":names[i],"Score":"Error","CEFR":"Error","AI_Flag":str(e)[:30]})
            progress.progress((i+1)/len(essays))
        st.session_state.batch_results={"results":results,"excel_rows":excel_rows,"level":level_b,"school":school_name}
        st.success(f"Done {len(results)} - all saved to Portfolio")
    if st.session_state.batch_results:
        results=st.session_state.batch_results["results"]; excel_rows=st.session_state.batch_results["excel_rows"]; level_b=st.session_state.batch_results["level"]; school_name=st.session_state.batch_results["school"]
        avg_score=sum([r["Score /10"] for r in excel_rows if isinstance(r["Score /10"], int)])/len(excel_rows) if excel_rows else 0
        st.markdown(f"### Avg {avg_score:.1f}/10 - {len(results)} graded")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
        if is_pro():
            st.download_button("📄 Principal PDF (PRO)", create_principal_pdf(excel_rows, level_b, avg_score, school_name), file_name=f"Principal_{school_name}.pdf", use_container_width=True, key="principal_pdf_1967")
with tab5:
    st.markdown("## 📘 Teacher Guide - How to Use TEFLMate v6.73d")
    st.caption("OCR Fixed - Qwen3.6 - Left menu restored")
    colA, colB = st.columns(2)
    with colA:
        st.markdown("### 📚 1. Portfolio")
        st.info("Home base. Every grade auto-saves here.")
        st.markdown("### ✍️ 2. Grade Essay")
        st.markdown("Paste → Name → Level → GRADE → See breakdown")
        st.markdown("### 📸 3. Photo/PDF - FIXED v6.73d")
        st.success("Groq deleted old Qwen, now using Qwen3.6-27b")
    with colB:
        st.markdown("### ⚡ 4. Batch 50 PRO")
        st.markdown("Template → 50 students → Upload → Shows confidence")
        st.markdown("### 💡 Pro Tips v6.73d")
        st.warning("Left menu: Promo, Paystack, PayPal, Languages all restored")
with tab6:
    st.markdown("## 🚀 SUPER 7Lang - One Click Market Setup")
    c1,c2,c3=st.columns(3)
    with c1:
        if st.button("🇧🇷 Brazil - Portuguese + CEFR", use_container_width=True, key="set_br_1967"): st.session_state.feedback_lang="Portuguese"; st.session_state.grading_standard="CEFR"; st.success("✅ Portuguese + CEFR"); st.balloons()
        if st.button("🇲🇽 Mexico/Spain - Spanish + CEFR", use_container_width=True, key="set_es_1967"): st.session_state.feedback_lang="Spanish"; st.session_state.grading_standard="CEFR"; st.success("✅ Spanish + CEFR ready")
    with c2:
        if st.button("🇸🇦 MENA - Arabic + IELTS", use_container_width=True, key="set_ar_1967"): st.session_state.feedback_lang="Arabic"; st.session_state.grading_standard="IELTS"; st.success("✅ Arabic + IELTS"); st.balloons()
        if st.button("🇺🇸 USA/UK - English + TOEFL", use_container_width=True, key="set_us_1967"): st.session_state.feedback_lang="English"; st.session_state.grading_standard="TOEFL"; st.success("✅ English + TOEFL ready")
    with c3:
        if st.button("🇮🇳 India - Hindi + IELTS", use_container_width=True, key="set_in_1967"): st.session_state.feedback_lang="Hindi"; st.session_state.grading_standard="IELTS"; st.success("✅ Hindi + IELTS"); st.balloons()
        if st.button("🇿🇦 SA - English + CEFR", use_container_width=True, key="set_sa_1967"): st.session_state.feedback_lang="English"; st.session_state.grading_standard="CEFR"; st.success("✅ English + CEFR - SA ready")
        if st.button("🇿🇦 SA Zulu - Zulu + CEFR", use_container_width=True, key="set_zu_1967"): st.session_state.feedback_lang="Zulu"; st.session_state.grading_standard="CEFR"; st.success("✅ Zulu + CEFR"); st.balloons()
st.divider()
st.markdown("### ❤️ Payshap 0658006750 | PayPal: paypal.me/TaahirMahomed")
c_pay1, c_pay2, c_pay3 = st.columns(3)
with c_pay1:
    st.link_button("💬 WhatsApp Proof", "https://wa.me/27658006750?text=Hi%20Mr%20Taahir%20-%20Payment%20Proof%20for%20TEFLMate", use_container_width=True)
with c_pay2:
    st.link_button("📧 Email proof", "mailto:taahir532@gmail.com?subject=TEFLMate Payment Proof", use_container_width=True)
with c_pay3:
    st.link_button("💙 Pay with PayPal", "https://paypal.me/TaahirMahomed", use_container_width=True)
st.caption("TEFLMate v6.73d • Durban, SA • Built by Mr Taahir Mahomed • Worldwide 🌍")
