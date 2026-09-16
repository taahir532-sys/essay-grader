import streamlit as st
import requests, json, re, base64, hashlib, unicodedata
from datetime import datetime, timedelta
from io import BytesIO
import pandas as pd
from PIL import Image
try:
    import fitz
except:
    fitz = None
try:
    from fpdf import FPDF
except:
    FPDF = None
import matplotlib.pyplot as plt

st.set_page_config(page_title="TEFLMate v6.91", page_icon="📚", layout="wide")

# PING - UptimeRobot keeps app awake
st.markdown('<div style="display:none;">ping ok</div>', unsafe_allow_html=True)

# HASH - White text fix
def hash_fix():
    return "white-fix-2026"
_ = hash_fix()

YOUR_EMAIL = "taahir532@gmail.com"
FREE_LIMIT = 5

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    PAYSTACK_SECRET = st.secrets.get("PAYSTACK_SECRET_KEY","")
    PAYPAL_ME = st.secrets.get("PAYPAL_ME","https://paypal.me/")
    PAYSHAP_LINK = st.secrets.get("PAYSHAP_LINK","")
except Exception as e:
    st.error(f"Missing secrets: {e}")
    st.stop()

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    from groq import Groq
    def get_groq():
        return Groq(api_key=GROQ_KEY)
except:
    def get_groq():
        return None

st.markdown("""
<style>
.tefl-header {
    background: #111827;
    padding: 16px 20px;
    border-radius: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: white;
    margin-bottom: 16px;
}
.tefl-badge {
    background: #10B981;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
}
.landing-hero {
    background: #F9FAFB;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
}
.testimonial {
    background: #FFFBEB;
    padding: 12px;
    border-radius: 8px;
    border-left: 4px solid #F59E0B;
    margin-top: 10px;
    font-size: 14px;
}
div[data-testid="stButton"] > button {
    background: white!important;
    color: #111!important;
    border: 1px solid #DDD!important;
    font-weight: 600!important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: #111827!important;
    color: white!important;
}
</style>
""", unsafe_allow_html=True)

if "uses" not in st.session_state: st.session_state.uses = 0
if "pro_expiry" not in st.session_state: st.session_state.pro_expiry = None
if "active_plan" not in st.session_state: st.session_state.active_plan = None
if "pay_links" not in st.session_state: st.session_state.pay_links = {}
if "pay_refs" not in st.session_state: st.session_state.pay_refs = {}
if "pay_links_time" not in st.session_state: st.session_state.pay_links_time = None
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
q_submit = st.query_params
if "submit" in q_submit:
    try:
        submit_teacher_id = q_submit.get("submit")
        if isinstance(submit_teacher_id, list): submit_teacher_id = submit_teacher_id[0]
        st.markdown('<div class="tefl-header"><div>📚 TEFLMate - Student Submit</div><div class="tefl-badge">STUDENT</div></div>', unsafe_allow_html=True)
        st.title("📝 Submit Your Essay")
        s_name_stu = st.text_input("Your Full Name:", key="stu_name_submit")
        level_stu = st.selectbox("Your Level:", ["A1","A2","B1","B2","C1","C2"], key="stu_level_submit")
        essay_stu = st.text_area("Paste your essay:", height=180, key="stu_essay_submit")
        cam_stu = st.camera_input("Or take photo:", key="stu_cam_submit")
        up_stu = st.file_uploader("Or upload image:", type=["jpg","jpeg","png"], key="stu_up_submit")
        stu_bytes = None
        if cam_stu: stu_bytes = cam_stu.getvalue()
        elif up_stu: stu_bytes = up_stu.getvalue()
        if stu_bytes:
            st.image(stu_bytes, use_container_width=True)
            if st.button("📸 Read Handwriting", use_container_width=True, key="stu_read_btn"):
                with st.spinner("Reading..."):
                    client = get_groq()
                    b64 = base64.b64encode(stu_bytes).decode('utf-8')
                    try:
                        res = client.chat.completions.create(model="qwen/qwen2.5-vl-32b-instruct", messages=[{"role":"user","content":[{"type":"text","text":"OCR: Extract handwritten text EXACTLY as written, keep spelling mistakes. Return only text."},{"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}]}], temperature=0)
                        txt = res.choices[0].message.content or ""
                        if "</think>" in txt: txt = txt.split("</think>")[-1].strip()
                        st.session_state.editable_ocr = txt.strip()
                    except Exception as e:
                        st.error(f"OCR failed: {e}")
        if st.session_state.editable_ocr:
            essay_stu = st.text_area("Edit OCR result:", value=st.session_state.editable_ocr, height=150, key="stu_edit_submit")
        if st.button("🚀 Submit to Teacher", type="primary", use_container_width=True, key="stu_submit_final"):
            if not s_name_stu or not essay_stu.strip():
                st.warning("Name and essay required")
            else:
                try:
                    client = get_groq()
                    prompt = f"You are kind Cambridge examiner for {level_stu}. Grade essay: '{essay_stu[:2000]}' Return JSON keys: grammar,vocabulary,coherence,task_achievement,overall,cefr,confidence,feedback_text ASCII only."
                    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], temperature=0)
                    result_raw = res.choices[0].message.content
                    def parse_quick(t):
                        try:
                            m = re.search(r'\{.*\}', t, re.DOTALL)
                            if m: return json.loads(m.group(0))
                        except: pass
                        return {"overall":5,"cefr":"B1","feedback_text":t}
                    parsed = parse_quick(result_raw)
                    score = int(parsed.get("overall",5)); cefr = parsed.get("cefr","B1")
                    supabase.table("essays").insert({"teacher_id": submit_teacher_id, "student_name": s_name_stu, "essay_text": essay_stu, "level": level_stu, "score": score, "cefr": cefr, "feedback": result_raw}).execute()
                    st.success(f"✅ Submitted! Score {score}/10 {cefr}")
                    st.balloons()
                    st.session_state.editable_ocr = ""
                except Exception as e:
                    st.error(f"Submit failed: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Student submit error: {e}")
        st.stop()
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
    except: pass

def login_screen():
    st.markdown("""<div class="tefl-header"><div style="font-size:22px;font-weight:800;">📚 TEFLMate</div><div class="tefl-badge">v6.91</div></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1.2,1])
    with col1:
        st.markdown("""<div class="landing-hero"><h2 style="margin:0;">Grade 40 books in 2 minutes 📸</h2><p style="color:#555;">Photo-grade • Track progress • Parent reports • Student Self-Submit • CV & Lesson Plans</p><ul><li>✅ Snap photo → Edit OCR → Grade → Save</li><li>✅ Principal PDF + HOD Report + Parent reports</li><li>✅ CV, Cover Letter, Lesson Plan, Contract Builder</li></ul></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("#### ⭐ What teachers say")
        st.markdown('<div class="testimonial"><b>Teacher from Durban:</b> "Saves 5hrs a week!" ⭐⭐⭐⭐⭐</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### 🔑 Login to your class")
    t1, t2 = st.tabs(["🔑 Login", "✨ Sign Up"])
    with t1:
        with st.form("login_form_final_1967"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("🚀 Login", use_container_width=True, type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    td = supabase.table("teachers").select("*").eq("email", email).execute()
                    if td.data:
                        st.session_state.teacher_id = td.data[0]["id"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
        with st.expander("🔓 Forgot Password?"):
            fp_email = st.text_input("Email to reset:", key="fp_email_1967")
            if st.button("📧 Send Reset Link", use_container_width=True):
                try:
                    supabase.auth.reset_password_for_email(fp_email, {"redirect_to": ""})
                    st.success(f"Sent to {fp_email}")
                except Exception as e:
                    st.error(str(e))
    with t2:
        with st.form("signup_form_final_1967"):
            email2 = st.text_input("New Email", key="s_email_1967"); password2 = st.text_input("New Password", type="password", key="s_pass_1967"); school = st.text_input("School Name", value="My School")
            if st.form_submit_button("Create Account", use_container_width=True):
                try:
                    supabase.auth.sign_up({"email": email2, "password": password2})
                    supabase.table("teachers").insert({"email": email2, "school_name": school}).execute()
                    st.success("Created! Go to Login tab.")
                except Exception as e: st.error(str(e))
    st.stop()

if not st.session_state.user: login_screen()
def is_pro(): return st.session_state.pro_expiry is not None and datetime.now() < st.session_state.pro_expiry
def is_admin():
    try: return st.session_state.user and st.session_state.user.email == YOUR_EMAIL
    except: return False
def get_status():
    if is_pro():
        days = (st.session_state.pro_expiry - datetime.now()).days + 1
        return f"✅ {st.session_state.active_plan} - {days}d left"
    else:
        remaining = FREE_LIMIT - st.session_state.uses
        if remaining <=0: return "❌ FREE - 0 left"
        return f"FREE - {remaining}/{FREE_LIMIT} left"
def clean(text): return unicodedata.normalize('NFKD', text or "").encode('ascii', 'ignore').decode('ascii')
def clean_feedback_for_excel(text):
    if not text: return ""
    t = clean(text); t = re.sub(r'\*\*|###|##|__|\*\*', '', t); return t.strip()
def parse_dimensions(text):
    try:
        j_match = re.search(r'\{.*\}', text, re.DOTALL)
        if j_match:
            j = json.loads(j_match.group(0))
            return j
    except:
        pass
    return {"grammar": 5, "vocabulary": 5, "coherence": 5, "task_achievement": 5, "overall": 5, "cefr": "B1", "confidence": "medium", "feedback_text": text}
def df_to_excel_bytes_safe(df, sheet_name="Sheet1"):
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        return output.getvalue(), "xlsx"
    except: return df.to_csv(index=False).encode('utf-8'), "csv"
def compress_image_bytes(image_bytes, max_size=1024, quality=85):
    try:
        img = Image.open(BytesIO(image_bytes))
        if img.mode in ("RGBA","P"): img = img.convert("RGB")
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except:
        return image_bytes
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
        if st.session_state.teacher_id:
            supabase.table("teachers").update(data).eq("id", st.session_state.teacher_id).execute()
        else:
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
def extract_text_from_image(image_bytes):
    image_bytes = compress_image_bytes(image_bytes, 1024, 85)
    client = get_groq()
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    for model_id in ["qwen/qwen2.5-vl-32b-instruct", "meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct"]:
        try:
            res = client.chat.completions.create(model=model_id, messages=[{"role": "user", "content": [{"type": "text", "text": "OCR: Extract handwritten text EXACTLY as written, keep spelling mistakes. Return only text, nothing else."},{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}], temperature=0)
            txt = res.choices[0].message.content or ""
            if "</think>" in txt: txt = txt.split("</think>")[-1].strip()
            if len(txt.strip()) > 3:
                return txt.strip()
        except:
            continue
    return "OCR_ERROR: Vision models temporarily unavailable."
def extract_text_from_pdf(pdf_bytes):
    if not fitz: return "Add PyMuPDF"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf"); text = "\n".join([p.get_text() for p in doc[:10]])
        if len(text.strip()) < 30 and len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=200); compressed = compress_image_bytes(pix.tobytes("jpeg"), 1024, 85); text = extract_text_from_image(compressed)
        return text
    except Exception as e: return f"PDF_ERROR: {e}"
def create_branded_pdf(original_essay, ai_result, target_level, student_name="Student"):
    pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    pdf.set_fill_color(17, 24, 39); pdf.rect(0, 0, 210, 32, 'F'); pdf.set_y(7)
    pdf.set_font("Arial", 'B', 14); pdf.set_text_color(255,255,255); pdf.cell(0, 8, "TEFLMate | Class Portfolio Report", align='C', ln=True); pdf.ln(10)
    pdf.set_text_color(0,0,0); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 7, f"Student: {student_name} | Level: {target_level} | Date: {datetime.now().strftime('%d %b %Y')}", ln=True); pdf.ln(2)
    pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 6, clean(ai_result))
    out = pdf.output(dest='S'); return out.encode('latin-1') if isinstance(out, str) else bytes(out)
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
        score = r.get('Score /10', r.get('Score',0)); status = "Excellent" if score >= 8 else "Good" if score >= 6 else "Needs Support"
        name = r.get('Student Name', r.get('Student','')); cefr = r.get('CEFR','')
        pdf.cell(70, 7, clean(name)[:35], border=1); pdf.cell(25, 7, f"{score}/10", border=1, align='C'); pdf.cell(25, 7, cefr, border=1, align='C'); pdf.cell(70, 7, status, border=1); pdf.ln()
    out = pdf.output(dest='S'); return out.encode('latin-1') if isinstance(out, str) else bytes(out)
def create_cv_pdf(cv_data):
    pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    pdf.set_fill_color(17,24,39); pdf.rect(0,0,210,35,'F'); pdf.set_y(10)
    pdf.set_font("Arial",'B',18); pdf.set_text_color(255,255,255); pdf.cell(0,10,clean(cv_data.get('name','Teacher CV')),align='C',ln=True)
    pdf.set_font("Arial",'',11); pdf.cell(0,6,clean(cv_data.get('email','')+" | "+cv_data.get('phone','')),align='C',ln=True); pdf.ln(15)
    pdf.set_text_color(0,0,0)
    for section, content in [("Profile", cv_data.get('profile','')), ("Experience", cv_data.get('experience','')), ("Education", cv_data.get('education','')), ("Skills", cv_data.get('skills','')), ("Certifications", cv_data.get('certs',''))]:
        if content:
            pdf.set_font("Arial",'B',12); pdf.set_fill_color(240,240,240); pdf.cell(0,8,section,ln=True,fill=True); pdf.ln(2)
            pdf.set_font("Arial",'',10); pdf.multi_cell(0,6,clean(content)); pdf.ln(4)
    out = pdf.output(dest='S'); return out.encode('latin-1') if isinstance(out, str) else bytes(out)
def create_cover_letter_pdf(letter_text, name):
    pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    pdf.set_font("Arial",'',11); pdf.multi_cell(0,6,clean(letter_text))
    pdf.ln(8); pdf.set_font("Arial",'B',11); pdf.cell(0,6,clean(name))
    out = pdf.output(dest='S'); return out.encode('latin-1') if isinstance(out, str) else bytes(out)
def detect_ai_risk(essay_text):
    text = essay_text.lower().strip()
    if len(text) < 10: return "Too Short"
    if "delve" in text and "tapestry" in text: return "⚠ Possible AI"
    return "✅ Human"
def get_essay_hash(text, level, lang, standard):
    return hashlib.md5((text.strip()[:1000] + "|" + level + "|" + lang + "|" + standard).encode()).hexdigest()
def check_supabase_cache(essay_hash):
    try:
        r = supabase.table("essay_cache").select("*").eq("hash", essay_hash).execute()
        if r.data: return r.data[0].get("result")
    except: pass
    return None
def save_supabase_cache(essay_hash, result, level):
    try: supabase.table("essay_cache").insert({"hash": essay_hash, "result": result, "level": level}).execute()
    except: pass
def grade_with_groq(essay_text, level):
    essay_hash = get_essay_hash(essay_text, level, st.session_state.feedback_lang, st.session_state.grading_standard)
    if essay_hash in st.session_state.grade_cache: return st.session_state.grade_cache[essay_hash]
    cached = check_supabase_cache(essay_hash)
    if cached:
        st.session_state.grade_cache[essay_hash] = cached; return cached
    if len(essay_text.strip()) < 25:
        fixed = json.dumps({"grammar":5,"vocabulary":5,"coherence":5,"task_achievement":5,"overall":5,"cefr":level,"ielts":5.0,"confidence":"low","feedback_text":f"Short text {len(essay_text.strip())} chars - needs 30+ words. | Score: 5/10 | CEFR {level}"})
        st.session_state.grade_cache[essay_hash] = fixed; return fixed
    client = get_groq(); lang = st.session_state.feedback_lang; std = st.session_state.grading_standard
    if std=="IELTS": std_inst="Also give IELTS Band 0-9."
    elif std=="TOEFL": std_inst="Also give TOEFL 0-30."
    elif std=="US Grade": std_inst="Also give US Grade A-F."
    else: std_inst="Give CEFR A1-C2 only."
    lang_inst = f"Feedback language: {lang}." if lang!="English" else "Feedback in English"
    prompt = f"You are kind Cambridge examiner for {level}. {std_inst}. {lang_inst}. Grade: '{essay_text[:2000]}' Return ONLY JSON keys grammar,vocabulary,coherence,task_achievement,overall,cefr,ielts,confidence,feedback_text ASCII only."
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], temperature=0, seed=42)
    result = res.choices[0].message.content; st.session_state.grade_cache[essay_hash] = result; save_supabase_cache(essay_hash, result, level); return result
def save_essay_db(student_name, essay_text, level, score, cefr, feedback):
    try:
        if not st.session_state.teacher_id: return False
        supabase.table("essays").insert({"teacher_id": st.session_state.teacher_id, "student_name": student_name, "essay_text": essay_text, "level": level, "score": score, "cefr": cefr, "feedback": feedback}).execute(); return True
    except: return False

if st.session_state.promo_success:
    st.balloons(); st.success("🎉 Code applied - saved!"); st.session_state.promo_success = False

with st.sidebar:
    st.markdown("### 🔑 Your Plan")
    st.info(get_status())
    if is_admin():
        st.success("👑 ADMIN MODE")
        if st.button("🛠 Open Admin Panel", use_container_width=True, type="primary"):
            st.session_state.show_admin = True
    if st.session_state.user:
        st.caption(f"👤 {st.session_state.user.email[:25]}")
        if st.button("Logout", use_container_width=True):
            supabase.auth.sign_out(); st.session_state.user=None; st.session_state.teacher_id=None; st.rerun()
    if st.session_state.teacher_id:
        try:
            ref_code = f"TEFL{str(st.session_state.teacher_id)[:6].upper()}"
            base_url = "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"
            ref_link = f"{base_url}?ref={ref_code}"; submit_link = f"{base_url}?submit={st.session_state.teacher_id}"
            st.markdown("#### 🎁 Refer & Earn"); st.caption(f"Your code: **{ref_code}**"); st.code(ref_link)
            st.markdown("#### 👨🎓 Student Self-Submit"); st.code(submit_link); st.divider()
        except: pass
        with st.expander("⚙ Settings", expanded=False):
            st.session_state.feedback_lang = st.selectbox("Feedback Language", ["English","Afrikaans","Zulu","Spanish","Portuguese","French","Arabic","Hindi","Mandarin"], index=0)
            st.session_state.grading_standard = st.selectbox("Grading Standard", ["CEFR","IELTS","TOEFL","US Grade"], index=0)
            promo_in = st.text_input("Promo Code:", placeholder="TEFL20", key="promo_sidebar_1967")
            if st.button("Apply Promo", use_container_width=True):
                if promo_in.upper()=="TEFL20":
                    st.session_state.uses = max(0, st.session_state.uses-2); st.session_state.promo_success = True; save_pro_to_db(None, "PROMO-TEFL20", 2); st.success("TEFL20 = +2 grades added!"); st.rerun()
                elif promo_in.upper()=="TRYSUPER":
                    new_exp = datetime.now() + timedelta(days=7); save_pro_to_db(new_exp, "TRYSUPER-7DAY", 0); st.session_state.pro_expiry = new_exp; st.session_state.active_plan = "TRYSUPER-7DAY"; st.success("TRYSUPER = 7 days PRO!"); st.rerun()
                else: st.error("Invalid code")
    st.markdown("### 💳 Upgrade - 3 Options")
    st.markdown("#### Paystack (ZAR)")
    for plan in ["WEEK49","MONTH99","YEAR799","ONCE10"]:
        amt = {"WEEK49":4900,"MONTH99":9900,"YEAR799":79900,"ONCE10":1000}[plan]
        label = {"WEEK49":"Weekly R49","MONTH99":"Monthly R99","YEAR799":"Yearly R799","ONCE10":"Once R10"}[plan]
        if st.button(label, key=f"pay_{plan}_v691", use_container_width=True):
            if not st.session_state.user: st.warning("Login first")
            else:
                res = init_paystack(st.session_state.user.email, amt, plan)
                if res.get("status"):
                    st.session_state.pay_links[plan] = res["data"]["authorization_url"]; st.session_state.pay_refs[plan] = res["data"]["reference"]; st.session_state.pay_links_time = datetime.now()
                else: st.error(res.get("message","Failed"))
    if st.session_state.pay_links_time and (datetime.now()-st.session_state.pay_links_time).total_seconds() > 3600:
        st.session_state.pay_links = {}; st.session_state.pay_refs = {}; st.session_state.pay_links_time = None
    for plan, link in st.session_state.pay_links.items():
        st.link_button(f"Pay {plan} via Paystack", link, use_container_width=True)
    if st.session_state.pay_refs:
        if st.button("✅ I've Paid - Verify All", type="primary", use_container_width=True):
            if verify_all_refs(): st.success("Unlocked & saved!"); st.rerun()
            else: st.warning("Not confirmed yet, try 30 sec")
    st.divider()
    st.markdown("#### PayShap (Instant EFT)")
    if st.button("💚 PayShap R99 Monthly", key="payshap_month", use_container_width=True): st.info("Send R99 to PayShap ID, email proof to taahir532@gmail.com")
    if st.button("💚 PayShap R10 Once", key="payshap_once", use_container_width=True): st.info("Send R10 to PayShap ID, email proof")
    st.divider()
    st.markdown("#### PayPal (Global)")
    st.link_button("💙 PayPal Monthly $8.50", "https://www.paypal.me/", use_container_width=True)
    st.link_button("💙 PayPal Once $0.99", "https://www.paypal.me/", use_container_width=True)
    st.link_button("💙 PayPal Yearly $65", "https://www.paypal.me/", use_container_width=True)
    st.caption("After PayPal/PayShap, email proof to taahir532@gmail.com")
    st.caption("Secured by Paystack, PayShap, PayPal")

if st.session_state.get("show_admin") and is_admin():
    st.title("🛠 Super Admin Dashboard")
    try:
        teachers = supabase.table("teachers").select("*").limit(100).execute()
        if teachers.data:
            df_t = pd.DataFrame(teachers.data); st.dataframe(df_t, use_container_width=True)
            csv_t = df_t.to_csv(index=False).encode('utf-8'); st.download_button("Download teachers.csv", csv_t, "teachers.csv", use_container_width=True)
    except Exception as e: st.error(str(e))
    if st.button("Close Admin"): st.session_state.show_admin = False; st.rerun()
    st.stop()

tab_home, tab_cv, tab_cover, tab_lesson, tab_port, tab_grade, tab_photo, tab_batch, tab_single, tab_principal, tab_hod, tab_history, tab_contract, tab_guide, tab_super = st.tabs(["🏠 Home","📄 CV","✉️ Cover","📖 Lesson","📚 Portfolio","✍ Grade","📸 Photo","📦 Batch","👤 Single","🏫 Principal","👨‍🏫 HOD","📈 History","📑 Contract","📊 Guide","💎 SUPER"])

with tab_home:
    st.markdown('<div class="tefl-header"><div style="font-size:22px;font-weight:800;">📚 TEFLMate v6.91</div><div class="tefl-badge">MADE IN DURBAN</div></div>', unsafe_allow_html=True)
    st.markdown("""<div class="landing-hero"><h2>Everything for TEFL Teachers - One App</h2><p>Grade 40 books in 2 mins, create CV, Cover Letter, Lesson Plans, Contracts, Principal Reports & Parent Reports.</p></div>""", unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3); c1.metric("Free Grades", f"{FREE_LIMIT - st.session_state.uses} left"); c2.metric("Plan", get_status()); c3.metric("Teachers", "500+ Active")
with tab_cv:
    st.markdown("### 📄 TEFL CV Builder")
    col1,col2 = st.columns(2)
    with col1:
        cv_name = st.text_input("Full Name", key="cv_name"); cv_email = st.text_input("Email", value=st.session_state.user.email if st.session_state.user else "", key="cv_email"); cv_phone = st.text_input("Phone", key="cv_phone"); cv_location = st.text_input("Location", value="Durban, South Africa", key="cv_loc")
    with col2:
        cv_exp_years = st.selectbox("Experience", ["0-1 years","1-3 years","3-5 years","5+ years"], key="cv_exp_y"); cv_level = st.selectbox("Teach Levels", ["Young Learners","Teens","Adults","Business English","All Levels"], key="cv_levels"); cv_certs = st.text_input("Certs", value="TEFL 120hr, IELTS", key="cv_certs_in")
    cv_profile = st.text_area("Profile Summary", height=80, key="cv_profile"); cv_experience = st.text_area("Experience", height=100, key="cv_exp"); cv_education = st.text_area("Education", height=80, key="cv_edu"); cv_skills = st.text_area("Skills", value="Classroom Management, Cambridge Exam Prep", height=60, key="cv_skills")
    if st.button("✨ Generate CV with AI", type="primary", use_container_width=True, key="gen_cv"):
        with st.spinner("Creating CV..."):
            client = get_groq(); prompt = f"Create professional TEFL CV for {cv_name}, {cv_exp_years}, {cv_level}, certs {cv_certs}, profile {cv_profile}, experience {cv_experience}, education {cv_education}, skills {cv_skills}."
            try:
                res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], temperature=0.3)
                ai_cv = res.choices[0].message.content; st.markdown(ai_cv)
                cv_data = {"name": cv_name, "email": cv_email, "phone": cv_phone, "profile": ai_cv, "experience": cv_experience, "education": cv_education, "skills": cv_skills, "certs": cv_certs}
                pdf = create_cv_pdf(cv_data); st.download_button("📥 Download CV PDF", pdf, file_name=f"CV_{cv_name}.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e: st.error(str(e))
with tab_cover:
    st.markdown("### ✉️ Cover Letter Builder")
    school_name = st.text_input("School Name", key="cover_school"); position = st.text_input("Position", value="English Teacher", key="cover_pos"); hiring_manager = st.text_input("Hiring Manager", key="cover_hm"); cl_exp = st.text_area("Key Achievements", height=100, key="cover_exp")
    if st.button("✨ Generate Cover Letter", type="primary", use_container_width=True, key="gen_cover"):
        with st.spinner("Writing..."):
            client = get_groq(); prompt = f"Write professional TEFL cover letter for {position} at {school_name}, manager {hiring_manager}, achievements {cl_exp}. 250 words."
            try:
                res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], temperature=0.4)
                letter = res.choices[0].message.content; st.markdown(letter)
                pdf = create_cover_letter_pdf(letter, "Applicant"); st.download_button("📥 Download Cover Letter PDF", pdf, file_name=f"Cover_{school_name}.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e: st.error(str(e))
with tab_lesson:
    st.markdown("### 📖 Lesson Plan Generator")
    lp_level = st.selectbox("Class Level", ["A1","A2","B1","B2","C1","C2"], key="lp_level"); lp_topic = st.text_input("Topic", placeholder="Past Simple, Environment", key="lp_topic"); lp_duration = st.selectbox("Duration", ["30 mins","45 mins","60 mins","90 mins"], key="lp_dur"); lp_focus = st.selectbox("Focus", ["Grammar","Vocabulary","Speaking","Writing","Reading","Mixed"], key="lp_focus"); lp_students = st.number_input("Students", value=20, key="lp_students")
    if st.button("✨ Generate Lesson Plan", type="primary", use_container_width=True, key="gen_lp"):
        with st.spinner("Planning..."):
            client = get_groq(); prompt = f"Create detailed TEFL lesson plan: Level {lp_level}, Topic {lp_topic}, Duration {lp_duration}, Focus {lp_focus}, Students {lp_students}. Include objectives, warm-up, presentation, practice, production, assessment, homework."
            try:
                res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], temperature=0.3)
                plan = res.choices[0].message.content; st.markdown(plan)
                pdf = create_branded_pdf(lp_topic, plan, lp_level, "Lesson Plan"); st.download_button("📥 Download Lesson Plan PDF", pdf, file_name=f"Lesson_{lp_topic}_{lp_level}.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e: st.error(str(e))
with tab_port:
    st.markdown("### 📚 My Class Portfolio")
    colf1, colf2 = st.columns(2)
    with colf1: search_f = st.text_input("Search student:", key="port_search_1967_v2")
    with colf2: level_f = st.selectbox("Filter level:", ["All","A1","A2","B1","B2","C1","C2"], key="port_level_1967_v2")
    try:
        if st.session_state.teacher_id:
            q = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(300).execute()
            rows = q.data if q.data else []
            if search_f: rows = [r for r in rows if search_f.lower() in r.get("student_name","").lower()]
            if level_f!="All": rows = [r for r in rows if r.get("level")==level_f]
            if not rows: st.info("No essays yet.")
            else:
                scores = [r.get("score",0) for r in rows]; avg = sum(scores)/len(scores) if scores else 0
                c1,c2,c3 = st.columns(3); c1.metric("Total", len(rows)); c2.metric("Avg", f"{avg:.1f}/10"); c3.metric("Total", len(rows))
                df = pd.DataFrame([{"Date": str(r.get("created_at",""))[:10], "Student Name": r.get("student_name",""), "Level": r.get("level",""), "Score /10": r.get("score",0), "CEFR": r.get("cefr",""), "AI Risk": detect_ai_risk(r.get("essay_text","")), "Feedback Preview": clean_feedback_for_excel(str(r.get("feedback",""))[:300])} for r in rows])
                st.dataframe(df, use_container_width=True, height=350)
                xls_bytes, ext = df_to_excel_bytes_safe(df, "Portfolio"); st.download_button(f"📥 Download Excel (.{ext})", xls_bytes, file_name=f"Portfolio_{datetime.now().strftime('%Y%m%d')}.{ext}", use_container_width=True)
                parent_excel = []
                for r in rows:
                    pid = r.get("id",""); base_url = "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"; parent_link = f"{base_url}?parent={pid}"
                    parent_excel.append({"Student": r.get("student_name",""), "Score": r.get("score",""), "CEFR": r.get("cefr",""), "Parent Report Link": parent_link})
                if parent_excel:
                    df_par = pd.DataFrame(parent_excel); par_bytes, par_ext = df_to_excel_bytes_safe(df_par, "ParentLinks"); st.download_button(f"📧 Download Parent Links", par_bytes, file_name=f"Parent_Links_{datetime.now().strftime('%Y%m%d')}.{par_ext}", use_container_width=True)
    except Exception as e: st.error(f"Portfolio error: {e}")
with tab_grade:
    st.markdown("### ✍ Grade Essay")
    s_name = st.text_input("Student Name:", key="grade_name_1967_v2"); t_level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="grade_level_1967_v2")
    essay_input = st.text_area("Paste Essay:", height=180, key="grade_essay_1967_v2")
    cam = st.camera_input("Take photo", key="grade_cam_1967_v2"); up = st.file_uploader("Upload image", type=["jpg","jpeg","png"], key="grade_up_1967_v2")
    img_bytes = None
    if cam: img_bytes = cam.getvalue()
    elif up: img_bytes = up.getvalue()
    if img_bytes:
        st.image(img_bytes, use_container_width=True)
        if st.button("📖 Read Handwriting", use_container_width=True, key="grade_ocr_btn_v2"):
            with st.spinner("Reading..."): txt = extract_text_from_image(img_bytes); st.session_state.editable_ocr = txt; st.success("OCR done!")
    if st.session_state.editable_ocr: essay_input = st.text_area("✏ Edit OCR:", value=st.session_state.editable_ocr, height=150, key="grade_edit_ocr_1967_v2")
    pdf_up = st.file_uploader("Or upload PDF", type=["pdf"], key="grade_pdf_1967_v2")
    if pdf_up:
        with st.spinner("Reading PDF..."): txt = extract_text_from_pdf(pdf_up.getvalue()); st.text_area("PDF preview:", value=txt[:2000], height=150);
        if len(txt.strip())>20: essay_input = txt
    if st.button("🚀 Grade Essay", type="primary", use_container_width=True):
        if len(essay_input.strip())<10: st.warning("Need 10+ chars")
        else:
            if not is_pro() and not is_admin() and st.session_state.uses >= FREE_LIMIT: st.error(f"Free limit {FREE_LIMIT} reached"); st.stop()
            with st.spinner("Grading..."):
                raw_result = grade_with_groq(essay_input, t_level); parsed = parse_dimensions(raw_result); score = int(parsed.get("overall",5)); cefr = parsed.get("cefr", t_level); feedback_text = parsed.get("feedback_text", raw_result)
                st.session_state.uses += 1
                if s_name: save_essay_db(s_name, essay_input, t_level, score, cefr, feedback_text)
                st.success(f"Score {score}/10 | CEFR {cefr}"); st.markdown(clean(feedback_text))
                pdf_bytes = create_branded_pdf(essay_input, feedback_text, t_level, s_name or "Student"); st.download_button("📥 Download PDF Report", pdf_bytes, file_name=f"{(s_name or 'Student')}_{score}10_{cefr}.pdf", mime="application/pdf", use_container_width=True)
with tab_photo:
    st.markdown("### 📸 Photo Grade + PDF Scan")
    s_name_p = st.text_input("Student Name (Photo):", key="photo_name_1967_v2"); t_level_p = st.selectbox("Level:", ["A1","A2","B1","B2","C1","C2"], key="photo_level_1967_v2")
    cam_p = st.camera_input("Take photo", key="photo_cam_1967_v2"); up_p = st.file_uploader("Upload photo", type=["jpg","jpeg","png"], key="photo_up_1967_v2"); pdf_p = st.file_uploader("Or Upload PDF scan", type=["pdf"], key="photo_pdf_1967")
    pb = None; pdf_txt = ""
    if cam_p: pb = cam_p.getvalue()
    elif up_p: pb = up_p.getvalue()
    if pdf_p:
        with st.spinner("Reading PDF..."): pdf_txt = extract_text_from_pdf(pdf_p.getvalue()); st.text_area("PDF Extracted:", value=pdf_txt[:2000], height=120, key="pdf_preview_photo")
    if pb:
        st.image(pb, use_container_width=True)
        if st.button("Read + Edit", use_container_width=True, key="photo_read_btn_v2"):
            with st.spinner("OCR..."): txt = extract_text_from_image(pb); st.session_state.last_photo_result = txt; st.session_state.editable_ocr = txt
        if st.session_state.last_photo_result:
            edit_p = st.text_area("Edit before grading:", value=st.session_state.last_photo_result, height=150, key="photo_edit_1967_v2")
            if st.button("Grade Photo Essay", type="primary", use_container_width=True, key="photo_grade_btn_v2"):
                if not is_pro() and st.session_state.uses >= FREE_LIMIT and not is_admin(): st.error(f"Free {FREE_LIMIT} limit reached"); st.stop()
                with st.spinner("Grading..."):
                    raw = grade_with_groq(edit_p, t_level_p); par = parse_dimensions(raw); sc = int(par.get("overall",5)); cf = par.get("cefr", t_level_p); fb = par.get("feedback_text", raw)
                    st.session_state.uses += 1
                    if s_name_p: save_essay_db(s_name_p, edit_p, t_level_p, sc, cf, fb)
                    st.success(f"{sc}/10 {cf}"); st.markdown(fb)
                    pdfb = create_branded_pdf(edit_p, fb, t_level_p, s_name_p or "Student"); st.download_button("Download PDF", pdfb, file_name=f"{s_name_p or 'Student'}_photo.pdf", use_container_width=True)
    if pdf_txt and len(pdf_txt.strip())>20:
        if st.button("Grade PDF Essay", type="primary", use_container_width=True, key="grade_pdf_text_btn"):
            with st.spinner("Grading PDF..."):
                raw = grade_with_groq(pdf_txt, t_level_p); par = parse_dimensions(raw); sc = int(par.get("overall",5)); cf = par.get("cefr", t_level_p); fb = par.get("feedback_text", raw)
                st.session_state.uses += 1
                if s_name_p: save_essay_db(s_name_p, pdf_txt, t_level_p, sc, cf, fb)
                st.success(f"{sc}/10 {cf}"); st.markdown(fb)
with tab_batch:
    st.markdown("### 📦 Batch Grade 50")
    b_level = st.selectbox("Default Level:", ["A1","A2","B1","B2","C1","C2"], key="batch_level_1967_v2"); b_text = st.text_area("Paste essays separated by ---:", height=180, key="batch_text_1967_v2"); b_csv = st.file_uploader("Or upload CSV (Student,Essay,Level)", type=["csv"], key="batch_csv_1967_v2")
    essays_list = []
    if b_csv:
        try:
            df_b = pd.read_csv(b_csv)
            for _, row in df_b.iterrows():
                try: name = str(row.iloc[0]); essay = str(row.iloc[1]); lvl = str(row.iloc[2]) if len(row)>2 else b_level;
                except: continue
                if len(essay.strip())>10: essays_list.append((name, essay, lvl))
            st.success(f"Loaded {len(essays_list)} from CSV")
        except Exception as e: st.error(f"CSV error: {e}")
    elif b_text:
        parts = [p.strip() for p in b_text.split("---") if p.strip()]
        for i, p in enumerate(parts): essays_list.append((f"Student {i+1}", p, b_level))
    if essays_list:
        st.write(f"Found {len(essays_list)} essays.")
        if st.button(f"🚀 Grade {min(50, len(essays_list))} Essays", type="primary", use_container_width=True):
            if not is_pro() and not is_admin(): st.error("Batch requires PRO"); st.stop()
            progress = st.progress(0); results = []
            for idx, (name, essay, lvl) in enumerate(essays_list[:50]):
                with st.spinner(f"Grading {idx+1}/{len(essays_list[:50])} - {name}"):
                    try:
                        raw = grade_with_groq(essay, lvl); par = parse_dimensions(raw); sc = int(par.get("overall",5)); cf = par.get("cefr", lvl)
                        save_essay_db(name, essay, lvl, sc, cf, par.get("feedback_text", raw))
                        results.append({"Student Name": name, "Level": lvl, "Score /10": sc, "CEFR": cf, "Feedback Preview": clean_feedback_for_excel(par.get("feedback_text","")[:200])})
                    except Exception as e: results.append({"Student Name": name, "Level": lvl, "Score /10": 0, "CEFR": "Error", "Feedback Preview": str(e)})
                progress.progress((idx+1)/len(essays_list[:50]))
            st.session_state.batch_results = results; st.success("Batch done & saved!")
    if st.session_state.batch_results:
        df_batch = pd.DataFrame(st.session_state.batch_results); st.dataframe(df_batch, use_container_width=True)
        try:
            fig, ax = plt.subplots(figsize=(8,3)); ax.bar(df_batch["Student Name"].astype(str), df_batch["Score /10"]); plt.xticks(rotation=45, fontsize=6); plt.tight_layout(); st.pyplot(fig)
        except: pass
        xb, extb = df_to_excel_bytes_safe(df_batch, "Batch50"); st.download_button(f"Download Batch Excel.{extb}", xb, file_name=f"Batch50_{datetime.now().strftime('%Y%m%d')}.{extb}", use_container_width=True)
        avg_b = df_batch["Score /10"].mean() if len(df_batch)>0 else 0; pdf_b = create_principal_pdf(st.session_state.batch_results, b_level, avg_b, "My Class"); st.download_button("🏫 Download Principal PDF", pdf_b, file_name=f"Principal_Batch_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)
with tab_single:
    st.markdown("### 👤 Single Grade - Manual Add")
    s_single = st.text_input("Student Name:", key="single_name"); l_single = st.selectbox("Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level"); e_single = st.text_area("Essay:", height=150, key="single_essay")
    if st.button("Grade Single Student", type="primary", use_container_width=True, key="single_grade_btn"):
        if len(e_single.strip())<10: st.warning("Need 10+ chars")
        else:
            if not is_pro() and st.session_state.uses >= FREE_LIMIT and not is_admin(): st.error("Free limit reached"); st.stop()
            with st.spinner("Grading..."):
                raw = grade_with_groq(e_single, l_single); par = parse_dimensions(raw); sc = int(par.get("overall",5)); cf = par.get("cefr", l_single); fb = par.get("feedback_text", raw); st.session_state.uses+=1; save_essay_db(s_single, e_single, l_single, sc, cf, fb); st.success(f"{s_single} - {sc}/10 {cf}"); st.markdown(fb)
with tab_principal:
    st.markdown("### 🏫 Principal Report")
    if st.session_state.teacher_id:
        try:
            q = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(200).execute()
            rows = q.data if q.data else []
            if not rows: st.info("No data yet - Grade some essays first")
            else:
                scores = [r.get("score",0) for r in rows]; avg = sum(scores)/len(scores) if scores else 0
                c1,c2,c3,c4 = st.columns(4); c1.metric("Total Students", len(rows)); c2.metric("Avg Score", f"{avg:.1f}/10"); c3.metric("Pass Rate", f"{len([s for s in scores if s>=6])/len(scores)*100:.0f}%" if scores else "0%"); c4.metric("Top CEFR", max(set([r.get("cefr","B1") for r in rows]), key=[r.get("cefr","B1") for r in rows].count) if rows else "B1")
                st.divider()
                df_p = pd.DataFrame([{"Student Name": r.get("student_name",""), "Level": r.get("level",""), "Score /10": r.get("score",0), "CEFR": r.get("cefr","")} for r in rows]); st.dataframe(df_p, use_container_width=True)
                try: fig, ax = plt.subplots(figsize=(8,3)); ax.hist(scores, bins=10, color='#111', edgecolor='white'); ax.set_xlabel("Score /10"); ax.set_ylabel("Students"); st.pyplot(fig)
                except: pass
                xb, ext = df_to_excel_bytes_safe(df_p, "Principal"); st.download_button("📥 Download Principal Excel", xb, file_name=f"Principal_Report_{datetime.now().strftime('%Y%m%d')}.{ext}", use_container_width=True)
                pdf_rows = df_p.to_dict('records'); pdf = create_principal_pdf(pdf_rows, "All Levels", avg, "My School"); st.download_button("🏫 Download Principal PDF (Official)", pdf, file_name=f"Principal_Official_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True, type="primary")
        except Exception as e: st.error(f"Principal error: {e}")
with tab_hod:
    st.markdown("### 👨‍🏫 HOD Report - Per Subject Analysis")
    if st.session_state.teacher_id:
        try:
            q = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(300).execute()
            rows = q.data if q.data else []
            if not rows: st.info("No data")
            else:
                levels = list(set([r.get("level","B1") for r in rows])); sel_level = st.selectbox("Select Level for HOD Report:", ["All"]+levels, key="hod_level_sel")
                filtered = rows if sel_level=="All" else [r for r in rows if r.get("level")==sel_level]; scores = [r.get("score",0) for r in filtered]; avg = sum(scores)/len(scores) if scores else 0
                st.metric(f"Avg for {sel_level}", f"{avg:.1f}/10", f"{len(filtered)} students")
                df_hod = pd.DataFrame([{"Student": r.get("student_name",""), "Level": r.get("level",""), "Score": r.get("score",0), "CEFR": r.get("cefr",""), "Date": str(r.get("created_at",""))[:10]} for r in filtered]); st.dataframe(df_hod, use_container_width=True)
                xb, ext = df_to_excel_bytes_safe(df_hod, f"HOD_{sel_level}"); st.download_button(f"Download HOD {sel_level} Excel", xb, file_name=f"HOD_{sel_level}_{datetime.now().strftime('%Y%m%d')}.{ext}", use_container_width=True)
                pdf = create_principal_pdf(df_hod.rename(columns={"Student":"Student Name","Score":"Score /10"}).to_dict('records'), sel_level, avg, f"HOD Report {sel_level}"); st.download_button(f"Download HOD {sel_level} PDF", pdf, file_name=f"HOD_{sel_level}.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e: st.error(f"HOD error: {e}")
with tab_history:
    st.markdown("### 📈 Student History + Progress Graph")
    search_hist = st.text_input("Enter student name to track:", key="hist_search")
    if st.session_state.teacher_id and search_hist:
        try:
            q = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).ilike("student_name", f"%{search_hist}%").order("created_at", desc=False).execute()
            rows = q.data if q.data else []
            if not rows: st.info("No history for this name")
            else:
                df_hist = pd.DataFrame([{"Date": str(r.get("created_at",""))[:10], "Score": r.get("score",0), "CEFR": r.get("cefr",""), "Level": r.get("level","")} for r in rows]); st.dataframe(df_hist, use_container_width=True)
                try: fig, ax = plt.subplots(figsize=(8,3)); ax.plot(df_hist["Date"].astype(str), df_hist["Score"], marker='o', color='#111'); ax.set_ylim(0,10); plt.xticks(rotation=45, fontsize=7); plt.tight_layout(); st.pyplot(fig)
                except Exception as e: st.caption(str(e))
                st.success(f"Progress: {rows[0].get('score',0)} → {rows[-1].get('score',0)} ( {len(rows)} essays )")
                xb, ext = df_to_excel_bytes_safe(df_hist, f"History_{search_hist}"); st.download_button("Download History Excel", xb, file_name=f"History_{search_hist}.xlsx", use_container_width=True)
        except Exception as e: st.error(str(e))
    else: st.info("Type student name above to see graph")
with tab_contract:
    st.markdown("### 📑 Contract Generator")
    ct_teacher = st.text_input("Teacher Name", key="ct_teacher"); ct_school = st.text_input("School Name", key="ct_school2"); ct_salary = st.text_input("Salary", value="R15000", key="ct_salary"); ct_hours = st.text_input("Hours per week", value="25 hours", key="ct_hours"); ct_start = st.date_input("Start Date", key="ct_start"); ct_duration = st.selectbox("Contract Duration", ["6 months","12 months","24 months"], key="ct_dur")
    if st.button("Generate Contract", type="primary", use_container_width=True, key="gen_contract"):
        contract_text = f"EMPLOYMENT CONTRACT\nSchool: {ct_school}\nTeacher: {ct_teacher}\nPosition: English Teacher\nSalary: {ct_salary} per month\nHours: {ct_hours}\nStart: {ct_start}\nDuration: {ct_duration}\n\n1. Duties: Teach English, lesson planning, grading, parent communication.\n2. Working Hours: As per school timetable.\n3. Leave: As per SA labour law.\n4. Termination: 1 month notice.\n\nSigned: _________________ Date: {ct_start}\n"
        st.markdown(contract_text)
        pdf = create_branded_pdf(contract_text, contract_text, "B1", f"Contract {ct_teacher}"); st.download_button("Download Contract PDF", pdf, file_name=f"Contract_{ct_teacher}.pdf", mime="application/pdf", use_container_width=True)
with tab_guide:
    st.markdown("### 📊 TEFL Grading Guide & Earnings")
    st.markdown("""
    **Common mistakes we detect:**
    - A1/A2: Missing verb 'be', no capital 'I', simple spelling
    - B1/B2: Article errors (a/the), tense mixing, run-on
    - C1/C2: Cohesion, register, complex grammar misuse
    **Paystack:** R10 once, R49 weekly, R99 monthly, R799 yearly - auto unlock
    **PayShap:** Instant EFT - email proof to activate
    **PayPal:** Global - $0.99, $8.50, $65 - email proof
    """)
    st.divider()
    st.markdown("#### 💰 Earnings Simulator")
    studs = st.slider("How many students?", 10, 500, 100); price_per = st.number_input(f"Price per student ({st.session_state.geo['symbol']})", value=10); earn = studs * price_per; st.metric("Monthly earning", f"{st.session_state.geo['symbol']}{earn}")
with tab_super:
    st.markdown("### 💎 SUPER Dashboard")
    st.caption(f"Local pricing: {st.session_state.geo['symbol']}{st.session_state.geo['weekly']}/{st.session_state.geo['monthly']}/{st.session_state.geo['yearly']}")
    if st.session_state.teacher_id:
        try: cnt = supabase.table("essays").select("id", count="exact").eq("teacher_id", st.session_state.teacher_id).execute(); total_graded = cnt.count if cnt.count is not None else 0
        except: total_graded = 0
        c1,c2 = st.columns(2); c1.metric("Total Graded", total_graded); c2.metric("Cache Hits", len(st.session_state.grade_cache))
        st.divider(); st.markdown("#### Upgrade now - Choose method"); st.info("Paystack = instant auto-unlock. PayShap/PayPal = email proof to taahir532@gmail.com")
    else: st.warning("Login first")

st.divider()
st.markdown("<div style='text-align:center; padding:12px; font-weight:600; color:#555;'>© 2026 TEFLMate | Made in Durban, ZA | TEFLMate v6.91 Full 15-Tab | OCR: qwen2.5-vl-32b-instruct | Ping OK</div>", unsafe_allow_html=True)
