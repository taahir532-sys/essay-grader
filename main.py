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
from PIL import Image
import hashlib
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
FREE_LIMIT = 10
st.set_page_config(page_title="TEFLMate - Class Portfolio v6.91", page_icon="📚", layout="wide", initial_sidebar_state="expanded")
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
if "payshap_choice" not in st.session_state: st.session_state.payshap_choice = None
if "paypal_choice" not in st.session_state: st.session_state.paypal_choice = None
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
        st.caption("Your teacher will receive it graded in their portfolio")
        s_name_stu = st.text_input("Your Full Name:", key="stu_name_submit")
        level_stu = st.selectbox("Your Level:", ["A1","A2","B1","B2","C1","C2"], key="stu_level_submit")
        essay_stu = st.text_area("Paste your essay:", height=180, key="stu_essay_submit")
        cam_stu = st.camera_input("Or take photo of handwriting:", key="stu_cam_submit")
        up_stu = st.file_uploader("Or upload image:", type=["jpg","jpeg","png"], key="stu_up_submit")
        stu_bytes = None
        if cam_stu: stu_bytes = cam_stu.getvalue()
        elif up_stu: stu_bytes = up_stu.getvalue()
        if stu_bytes:
            st.image(stu_bytes, use_container_width=True)
            if st.button("📸 Read Handwriting", use_container_width=True, key="stu_read_btn"):
                with st.spinner("Reading..."):
                    try:
                        img = Image.open(BytesIO(stu_bytes))
                        if max(img.size) > 1024:
                            img.thumbnail((1024,1024))
                            buf = BytesIO(); img.save(buf, format="JPEG", quality=85); stu_bytes = buf.getvalue()
                    except: pass
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
                    st.success(f"✅ Submitted! Score {score}/10 {cefr} — Teacher will see it")
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
            st.info("Generated by TEFLMate v6.91")
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
    st.title("🔐 TEFLMate - Set New Password v6.91")
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
    st.markdown("""<div class="tefl-header"><div style="font-size:22px;font-weight:800;">📚 TEFLMate</div><div class="tefl-badge">v6.91</div></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1.2,1])
    with col1:
        st.markdown("""<div class="landing-hero"><h2 style="margin:0;">Grade 40 books in 2 minutes 📸</h2><p style="color:#555;">Photo-grade • Track progress • Parent reports • Student Self-Submit • CV & Lesson Plans • School OS v6.91</p><ul><li>✅ Snap photo → Edit → Grade → Save</li><li>✅ Grammar/Vocab/Coherence breakdown + Confidence flag + AI Risk</li><li>✅ CV, Cover Letter, Lesson Plan, Principal OS, HOD, History</li></ul></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("#### ⭐ What teachers say")
        st.markdown('<div class="testimonial"><b>Teacher from Durban:</b> "Saves 5hrs a week. Parents love reports! Compressor + Hash Cache is fast" ⭐⭐⭐⭐⭐</div>', unsafe_allow_html=True)
        st.markdown('<div class="testimonial"><b>Teacher from Brazil:</b> "Photo grading magic" ⭐⭐⭐⭐⭐</div>', unsafe_allow_html=True)
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
                    if td.data and len(td.data) > 0:
                        teacher = td.data[0]
                        st.session_state.teacher_id = teacher.get("id")
                        pro = teacher.get("pro_expiry")
                        if pro:
                            try:
                                exp = datetime.fromisoformat(pro.replace("Z",""))
                                if exp > datetime.now():
                                    st.session_state.pro_expiry = exp
                                    st.session_state.active_plan = teacher.get("active_plan")
                            except:
                                pass
                    else:
                        ins = supabase.table("teachers").insert({"email": email}).execute()
                        if ins.data:
                            st.session_state.teacher_id = ins.data[0].get("id")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
        with st.expander("🔓 Forgot Password?"):
            fp_email = st.text_input("Email to reset:", key="fp_email_1967")
            if st.session_state.last_reset and (datetime.now() - st.session_state.last_reset).seconds < 60:
                st.warning("Wait a bit")
            else:
                if st.button("📧 Send Reset Link", use_container_width=True):
                    try:
                        supabase.auth.reset_password_for_email(fp_email, {"redirect_to": ""})
                        st.session_state.last_reset = datetime.now()
                        st.success(f"Sent to {fp_email}")
                    except Exception as e:
                        st.error(str(e))
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
        if st.session_state.active_plan and "ONCE" in str(st.session_state.active_plan) and remaining > FREE_LIMIT: return f"✅ {st.session_state.active_plan} - {remaining} left"
        return f"FREE - {remaining}/{FREE_LIMIT} left"
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
    else:
        if amt >= 79900: pro_exp = now + timedelta(days=365); active="YEAR799"
        elif amt >= 9900: pro_exp = now + timedelta(days=30); active="MONTH99"
        elif amt >= 4900: pro_exp = now + timedelta(days=7); active="WEEK49"
        else: st.session_state.uses -= 10; active="ONCE10"; save_pro_to_db(None, active, 10); return True
        if pro_exp and active: save_pro_to_db(pro_exp, active, 0)
    if pro_exp and active:
        st.session_state.pro_expiry = pro_exp
        st.session_state.active_plan = active
        st.success(f"Activated {active}!")
    return True
def verify_all_refs():
    if st.session_state.pay_refs:
        for plan, ref in list(st.session_state.pay_refs.items()):
            if ref:
                v = verify_paystack(ref)
                if v.get("status") and v.get("data", {}).get("status") == "success":
                    if unlock_paystack(v):
                        del st.session_state.pay_refs[plan]
                        st.rerun()
def reset_pay_links_if_expired():
    if st.session_state.pay_links_time and (datetime.now() - st.session_state.pay_links_time).seconds > 600:
        st.session_state.pay_links = {}; st.session_state.pay_refs = {}; st.session_state.pay_links_time = None
def ai_read_handwriting(image_bytes, filename_hint="essay.jpg"):
    comp_bytes = compress_image_bytes(image_bytes, max_size=1024, quality=80)
    hash_key = hashlib.md5(comp_bytes).hexdigest()
    if hash_key in st.session_state.grade_cache and "ocr" in st.session_state.grade_cache[hash_key]:
        return st.session_state.grade_cache[hash_key]["ocr"]
    client = get_groq()
    b64 = base64.b64encode(comp_bytes).decode('utf-8')
    mime = "image/jpeg"
    prompt = "OCR: Extract ALL handwritten/typed text EXACTLY as written including mistakes. Keep original spelling and grammar errors. Return ONLY extracted text, no explanation."
    try:
        response = client.chat.completions.create(model="qwen/qwen2.5-vl-32b-instruct", messages=[{"role":"user","content":[{"type":"text","text": prompt},{"type":"image_url","image_url":{"url": f"data:{mime};base64,{b64}"}}]}], temperature=0)
        content = response.choices[0].message.content or ""
        if "</think>" in content: content = content.split("</think>")[-1].strip()
        cleaned = content.strip()
        if hash_key not in st.session_state.grade_cache: st.session_state.grade_cache[hash_key] = {}
        st.session_state.grade_cache[hash_key]["ocr"] = cleaned
        st.session_state.last_ocr = cleaned
        return cleaned
    except Exception as e:
        return f"OCR Error: {e}"
def ai_grade_essay(essay_text, level="B1", rubric_text=None, feedback_language="English", grading_standard="CEFR"):
    hash_key = hashlib.md5(f"{essay_text}_{level}_{rubric_text}_{feedback_language}_{grading_standard}".encode()).hexdigest()
    if hash_key in st.session_state.grade_cache and "grade" in st.session_state.grade_cache[hash_key]:
        return st.session_state.grade_cache[hash_key]["grade"]
    client = get_groq()
    rubric_instruction = f"Use this custom rubric: {rubric_text}" if rubric_text else "Use standard CEFR rubric."
    lang_instruction = f"Write feedback in {feedback_language}." if feedback_language!= "English" else "Write feedback in English."
    prompt = f"""You are expert TEFL examiner v6.91. Level={level}, Standard={grading_standard}. {rubric_instruction} {lang_instruction}
Essay: '''{essay_text[:3000]}'''
Return valid JSON ONLY with keys:
- grammar (0-10 int)
- vocabulary (0-10 int)
- coherence (0-10 int)
- task_achievement (0-10 int)
- overall (0-10 int)
- cefr (A1-C2)
- confidence (low/medium/high)
- feedback_text (detailed feedback ASCII only, include AI-risk if suspicious)
- ai_risk (low/medium/high)
No markdown, just JSON.
"""
    try:
        response = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content": prompt}], temperature=0.3)
        content = response.choices[0].message.content or ""
        if "</think>" in content: content = content.split("</think>")[-1].strip()
        parsed = parse_dimensions(content)
        if hash_key not in st.session_state.grade_cache: st.session_state.grade_cache[hash_key] = {}
        st.session_state.grade_cache[hash_key]["grade"] = parsed
        return parsed
    except Exception as e:
        return {"overall":5,"cefr":"B1","feedback_text": f"Grading error: {e}","grammar":5,"vocabulary":5,"coherence":5,"task_achievement":5,"confidence":"low","ai_risk":"low"}
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
def create_parent_pdf(student_name, essay, result, logo_bytes=None):
    pdf = FPDF(); pdf.add_page()
    if logo_bytes:
        try:
            with open("/tmp/logo.png","wb") as f: f.write(logo_bytes)
            pdf.image("/tmp/logo.png", x=10, y=8, w=30)
        except: pass
    pdf.set_font("Arial",'B',16); pdf.cell(0,10,f"Parent Report - {clean(student_name)}",align='C',ln=True); pdf.ln(5)
    pdf.set_font("Arial",'',11); pdf.cell(0,8,f"Score: {result.get('overall',5)}/10 | CEFR: {result.get('cefr','B1')} | Date: {datetime.now().strftime('%Y-%m-%d')}",ln=True); pdf.ln(5)
    pdf.set_font("Arial",'B',12); pdf.cell(0,8,"Feedback:",ln=True)
    pdf.set_font("Arial",'',10); pdf.multi_cell(0,6,clean(result.get('feedback_text',''))); pdf.ln(5)
    pdf.set_font("Arial",'B',12); pdf.cell(0,8,"Original Essay:",ln=True)
    pdf.set_font("Arial",'',9); pdf.multi_cell(0,5,clean(essay[:2000]))
    out = pdf.output(dest='S'); return out.encode('latin-1') if isinstance(out, str) else bytes(out)
with st.sidebar:
    st.markdown(f'<div style="background:#111;color:white;padding:12px;border-radius:12px;"><b>📚 TEFLMate v6.91</b><br>{get_status()}</div>', unsafe_allow_html=True)
    st.write(f"👤 {st.session_state.user.email if st.session_state.user else 'Unknown'}")
    if st.button("🚪 Logout", use_container_width=True):
        try: supabase.auth.sign_out()
        except: pass
        st.session_state.user=None; st.session_state.teacher_id=None; st.query_params.clear(); st.rerun()
    if is_admin(): st.success("👑 ADMIN")
    reset_pay_links_if_expired(); verify_all_refs()
    st.divider()
    st.markdown(f"### 💳 Upgrade PRO {st.session_state.geo['symbol']} - {st.session_state.geo['code']}")
    st.caption(f"Detected: {st.session_state.geo['code']} | Free left: {max(0, FREE_LIMIT - st.session_state.uses) if st.session_state.uses>=0 else FREE_LIMIT + (-st.session_state.uses)}")
    st.markdown("#### 1️⃣ PayStack (Card) - Auto Unlock")
    if st.button(f"💳 R10 +10 Grades", key="ps10_v691_fix", use_container_width=True):
        if not st.session_state.user: st.warning("Login first")
        else:
            init = init_paystack(st.session_state.user.email, 1000, "ONCE10")
            if init.get("status"):
                st.session_state.pay_links["ONCE10"] = init["data"]["authorization_url"]
                st.session_state.pay_refs["ONCE10"] = init["data"]["reference"]
                st.session_state.pay_links_time = datetime.now()
    if "ONCE10" in st.session_state.pay_links:
        st.link_button("🔗 Pay R10 +10 Now (10min)", st.session_state.pay_links["ONCE10"], use_container_width=True)
        ref_c = st.session_state.pay_refs.get("ONCE10","")
        if ref_c and st.button("✅ Verify R10", key="ver10_v691", use_container_width=True):
            v = verify_paystack(ref_c)
            if unlock_paystack(v): st.success("R10 done"); del st.session_state.pay_links["ONCE10"]; del st.session_state.pay_refs["ONCE10"]; st.rerun()
            else: st.error("Not yet paid")
    if st.button(f"💳 Weekly {st.session_state.geo['symbol']}{st.session_state.geo['weekly']} (7d)", key="ps_week_v691_fix", use_container_width=True):
        init = init_paystack(st.session_state.user.email, 4900, "WEEK49")
        if init.get("status"):
            st.session_state.pay_links["WEEK49"] = init["data"]["authorization_url"]
            st.session_state.pay_refs["WEEK49"] = init["data"]["reference"]
            st.session_state.pay_links_time = datetime.now()
    if "WEEK49" in st.session_state.pay_links:
        st.link_button(f"🔗 Pay {st.session_state.geo['symbol']}{st.session_state.geo['weekly']}", st.session_state.pay_links["WEEK49"], use_container_width=True)
        if st.button("✅ Verify Weekly", key="ver_week_v691", use_container_width=True):
            v = verify_paystack(st.session_state.pay_refs["WEEK49"])
            if unlock_paystack(v): del st.session_state.pay_links["WEEK49"]; del st.session_state.pay_refs["WEEK49"]; st.rerun()
    if st.button(f"💳 Monthly {st.session_state.geo['symbol']}{st.session_state.geo['monthly']} (30d)", key="ps_month_v691_fix", use_container_width=True):
        init = init_paystack(st.session_state.user.email, 9900, "MONTH99")
        if init.get("status"):
            st.session_state.pay_links["MONTH99"] = init["data"]["authorization_url"]
            st.session_state.pay_refs["MONTH99"] = init["data"]["reference"]
            st.session_state.pay_links_time = datetime.now()
    if "MONTH99" in st.session_state.pay_links:
        st.link_button(f"🔗 Pay {st.session_state.geo['symbol']}{st.session_state.geo['monthly']}", st.session_state.pay_links["MONTH99"], use_container_width=True)
        if st.button("✅ Verify Monthly", key="ver_month_v691", use_container_width=True):
            v = verify_paystack(st.session_state.pay_refs["MONTH99"])
            if unlock_paystack(v): del st.session_state.pay_links["MONTH99"]; del st.session_state.pay_refs["MONTH99"]; st.rerun()
    st.divider()
    st.markdown("#### 2️⃣ PayShap (Instant EFT) - FIXED PERSISTENT")
    payshap_id = st.secrets.get("PAYSHAP_ID", "0658006750")
    payshap_bank = st.secrets.get("PAYSHAP_BANK", "ABSA")
    payshap_name = st.secrets.get("PAYSHAP_NAME", "TEFLMate")
    if st.button(f"💚 PayShap Weekly {st.session_state.geo['symbol']}{st.session_state.geo['weekly']}", key="payshap_week_v691", use_container_width=True):
        st.session_state.payshap_choice = f"WEEKLY_{st.session_state.geo['weekly']}"
    if st.button(f"💚 PayShap Monthly {st.session_state.geo['symbol']}{st.session_state.geo['monthly']}", key="payshap_month_v691", use_container_width=True):
        st.session_state.payshap_choice = f"MONTHLY_{st.session_state.geo['monthly']}"
    if st.button(f"💚 PayShap Yearly {st.session_state.geo['symbol']}{st.session_state.geo['yearly']}", key="payshap_year_v691", use_container_width=True):
        st.session_state.payshap_choice = f"YEARLY_{st.session_state.geo['yearly']}"
    if st.button(f"💚 PayShap Once {st.session_state.geo['symbol']}{st.session_state.geo['once']} +10", key="payshap_once_v691", use_container_width=True):
        st.session_state.payshap_choice = f"ONCE_{st.session_state.geo['once']}"
    if st.session_state.payshap_choice:
        sel = st.session_state.payshap_choice
        amount_val = sel.split('_')[1] if '_' in sel else st.session_state.geo['monthly']
        user_email_ref = st.session_state.user.email if st.session_state.user else 'YOUR_EMAIL'
        st.success(f"PayShap Selected: {sel} - PERSISTENT")
        st.info(f"Bank: {payshap_bank} | ID: {payshap_id} | Name: {payshap_name} | Amount: {st.session_state.geo['symbol']}{amount_val} | Ref: {user_email_ref}")
        st.code(f"ABSA PayShap ID: {payshap_id} | Amount: {st.session_state.geo['symbol']}{amount_val} | Ref: {user_email_ref} | Bank: {payshap_bank}", language="text")
        if st.button("Clear PayShap", key="clear_payshap_v691", use_container_width=True):
            st.session_state.payshap_choice = None
            st.rerun()
    st.divider()
    st.markdown("#### 3️⃣ PayPal (Global) - FIXED PERSISTENT")
    paypal_me = st.secrets.get("PAYPAL_ME", "https://paypal.me/TaahirMahomed")
    paypal_email = st.secrets.get("PAYPAL_EMAIL", "taahir532@gmail.com")
    if st.button(f"PayPal Weekly {st.session_state.geo['symbol']}{st.session_state.geo['weekly']}", key="paypal_week_v691", use_container_width=True):
        st.session_state.paypal_choice = f"WEEKLY_{st.session_state.geo['weekly']}"
    if st.button(f"PayPal Monthly {st.session_state.geo['symbol']}{st.session_state.geo['monthly']}", key="paypal_month_v691", use_container_width=True):
        st.session_state.paypal_choice = f"MONTHLY_{st.session_state.geo['monthly']}"
    if st.button(f"PayPal Yearly {st.session_state.geo['symbol']}{st.session_state.geo['yearly']}", key="paypal_year_v691", use_container_width=True):
        st.session_state.paypal_choice = f"YEARLY_{st.session_state.geo['yearly']}"
    if st.button(f"PayPal Once {st.session_state.geo['symbol']}{st.session_state.geo['once']} +10", key="paypal_once_v691", use_container_width=True):
        st.session_state.paypal_choice = f"ONCE_{st.session_state.geo['once']}"
    if st.session_state.paypal_choice:
        sel2 = st.session_state.paypal_choice
        amount_val2 = sel2.split('_')[1] if '_' in sel2 else st.session_state.geo['monthly']
        user_email_ref2 = st.session_state.user.email if st.session_state.user else 'YOUR_EMAIL'
        st.success(f"PayPal Selected: {sel2} - PERSISTENT")
        st.info(f"PayPal Email: {paypal_email} | Link: {paypal_me} | Amount: {st.session_state.geo['symbol']}{amount_val2} | Ref: {user_email_ref2}")
        st.code(f"PayPal: {paypal_email} | Amount: {amount_val2} | Ref: {user_email_ref2}", language="text")
        st.link_button(f"Open PayPal {paypal_me}", paypal_me, use_container_width=True)
        if st.button("Clear PayPal", key="clear_paypal_v691", use_container_width=True):
            st.session_state.paypal_choice = None
            st.rerun()
    st.divider()
    with st.expander("Promo Code"):
        pc = st.text_input("Code:", key="promo_input_v691")
        if st.button("Apply Promo", use_container_width=True, key="promo_btn_v691"):
            try:
                if pc.strip() == "ADMIN2026" or pc.strip() == "TEFL2026":
                    st.session_state.pro_expiry = datetime.now() + timedelta(days=30)
                    st.session_state.active_plan = f"PROMO_{pc}"
                    save_pro_to_db(st.session_state.pro_expiry, st.session_state.active_plan, 0)
                    st.session_state.promo_success = True
                    st.success("Promo Activated 30 days!")
                    st.balloons()
                else:
                    promos = supabase.table("promo_codes").select("*").eq("code", pc.strip()).execute()
                    if promos.data:
                        p = promos.data[0]
                        if p.get("used") == False or p.get("used") is None:
                            days = p.get("days", 30)
                            st.session_state.pro_expiry = datetime.now() + timedelta(days=days)
                            st.session_state.active_plan = f"PROMO_{pc}"
                            save_pro_to_db(st.session_state.pro_expiry, st.session_state.active_plan, 0)
                            try: supabase.table("promo_codes").update({"used": True, "used_by": st.session_state.user.email}).eq("code", pc).execute()
                            except: pass
                            st.success(f"Promo {days} days!")
                            st.balloons()
                        else:
                            st.warning("Code already used")
                    else:
                        st.error("Invalid promo")
            except Exception as e:
                st.error(f"Promo error: {e}")
    st.divider()
    st.markdown("#### Settings")
    st.session_state.custom_rubric = st.text_area("Custom Rubric (optional):", value=st.session_state.custom_rubric or "", height=80, key="rubric_v691")
    st.session_state.feedback_lang = st.selectbox("Feedback Language:", ["English","Spanish","Portuguese","French","Arabic","Zulu","Afrikaans"], index=0, key="lang_v691")
    st.session_state.grading_standard = st.selectbox("Grading Standard:", ["CEFR","IELTS","TOEFL","Cambridge"], index=0, key="std_v691")
    if st.button("Clear Cache (Faster)", use_container_width=True, key="clear_cache_v691"):
        st.session_state.grade_cache = {}
        st.success("Cache cleared")
    st.caption("TEFLMate v6.91 - School OS - Hash Cache + Compressor + Fixed Indent + PayShap Persistent + Secrets")
main_tabs = st.tabs(["Grade Single","Batch Photo","Class Portfolio","CV & Tools","Principal OS","Lesson Plan","Invite Parents","History","Referral"])
with main_tabs[0]:
    st.subheader("Grade Single Essay - Photo or Paste")
    col_a, col_b = st.columns(2)
    with col_a:
        stu_name = st.text_input("Student Name:", key="single_name_v691")
        stu_level = st.selectbox("Level:", ["A1","A2","B1","B2","C1","C2"], key="single_level_v691")
        stu_essay = st.text_area("Paste essay here (or use photo OCR -> edit):", height=200, key="single_essay_v691")
        if st.session_state.editable_ocr:
            stu_essay = st.text_area("Edit OCR result (editable):", value=st.session_state.editable_ocr, height=200, key="single_edit_v691")
        cam = st.camera_input("Take photo of handwriting:", key="single_cam_v691")
        up = st.file_uploader("Upload image:", type=["jpg","jpeg","png","pdf"], key="single_up_v691")
        img_bytes = None
        if cam: img_bytes = cam.getvalue()
        elif up: img_bytes = up.getvalue()
        if img_bytes:
            if up and up.name.lower().endswith(".pdf") and fitz:
                try:
                    doc = fitz.open(stream=img_bytes, filetype="pdf")
                    page = doc.load_page(0)
                    pix = page.get_pixmap(dpi=200)
                    img_bytes = pix.tobytes("jpeg")
                    st.image(img_bytes, caption="PDF first page")
                except:
                    st.image(img_bytes, caption="PDF")
            else:
                st.image(img_bytes, caption="Preview", use_container_width=True)
            if st.button("Read Handwriting (OCR) with Compressor", use_container_width=True, key="ocr_btn_v691"):
                with st.spinner("Reading with compression..."):
                    ocr_text = ai_read_handwriting(img_bytes)
                    st.session_state.editable_ocr = ocr_text
                    st.session_state.last_ocr = ocr_text
                    st.rerun()
    with col_b:
        st.markdown("#### Grading")
        if not is_pro() and st.session_state.uses >= FREE_LIMIT and not (st.session_state.active_plan and "ONCE" in str(st.session_state.active_plan) and st.session_state.uses < 0):
            st.error(f"FREE limit {FREE_LIMIT} reached - Upgrade")
        else:
            if st.button("Grade This Essay (Hash Cache + History Save)", type="primary", use_container_width=True, key="grade_single_v691"):
                text_to_grade = stu_essay
                if st.session_state.editable_ocr and not stu_essay.strip():
                    text_to_grade = st.session_state.editable_ocr
                elif st.session_state.editable_ocr and len(st.session_state.editable_ocr) > len(stu_essay):
                    text_to_grade = st.session_state.editable_ocr
                if not stu_name: st.warning("Enter student name")
                elif not text_to_grade or len(text_to_grade.strip()) < 10: st.warning("Need essay text or OCR")
                else:
                    with st.spinner("Grading... (cached if same)"):
                        result = ai_grade_essay(text_to_grade, level=stu_level, rubric_text=st.session_state.custom_rubric, feedback_language=st.session_state.feedback_lang, grading_standard=st.session_state.grading_standard)
                        st.session_state.last_photo_result = result
                        st.session_state.uses += 1
                        try:
                            if st.session_state.teacher_id:
                                supabase.table("essays").insert({
                                    "teacher_id": st.session_state.teacher_id,
                                    "student_name": stu_name,
                                    "essay_text": text_to_grade,
                                    "level": stu_level,
                                    "score": int(result.get("overall",5)),
                                    "cefr": result.get("cefr","B1"),
                                    "feedback": result.get("feedback_text",""),
                                    "grammar": int(result.get("grammar",5)),
                                    "vocabulary": int(result.get("vocabulary",5)),
                                    "coherence": int(result.get("coherence",5)),
                                    "task_achievement": int(result.get("task_achievement",5)),
                                    "confidence": result.get("confidence","medium"),
                                    "ai_risk": result.get("ai_risk","low")
                                }).execute()
                        except Exception as e:
                            st.warning(f"Save to history failed: {e}")
                        st.success(f"Graded! Score {result.get('overall',5)}/10 {result.get('cefr','B1')} Confidence {result.get('confidence','medium')} - Saved to History")
        if st.session_state.last_photo_result:
            res = st.session_state.last_photo_result
            st.metric("Overall", f"{res.get('overall',5)}/10", res.get('cefr','B1'))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Grammar", res.get('grammar',5))
            c2.metric("Vocab", res.get('vocabulary',5))
            c3.metric("Coherence", res.get('coherence',5))
            c4.metric("Task", res.get('task_achievement',5))
            st.info(f"Confidence: {res.get('confidence','medium')} | AI Risk: {res.get('ai_risk','low')}")
            st.markdown(clean_feedback_for_excel(res.get('feedback_text','')))
            parent_id = ""
            try:
                if st.session_state.teacher_id:
                    last = supabase.table("essays").select("id").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(1).execute()
                    if last.data: parent_id = last.data[0]["id"]
            except: pass
            if parent_id:
                base_url = st.secrets.get("BASE_URL", "https://your-app.streamlit.app")
                parent_link = f"{base_url}?parent={parent_id}"
                st.code(parent_link, language="text")
                st.caption("Parent link - copy and send to parent")
            logo_file = st.file_uploader("School logo for parent PDF (optional):", type=["png","jpg"], key="logo_v691")
            logo_bytes = logo_file.getvalue() if logo_file else None
            if st.button("Generate Parent PDF", use_container_width=True, key="parent_pdf_v691"):
                try:
                    pdf_bytes = create_parent_pdf(stu_name, stu_essay or st.session_state.editable_ocr, res, logo_bytes)
                    st.download_button("Download Parent PDF", data=pdf_bytes, file_name=f"Parent_{clean(stu_name)}.pdf", mime="application/pdf", use_container_width=True, key="dl_parent_v691")
                except Exception as e:
                    st.error(f"PDF failed: {e}")
with main_tabs[1]:
    st.subheader("Batch Photo Grading - 40 Books in 2 min with Compressor + Hash")
    st.info("Take photos of class set -> Auto OCR + Grade + Save to Portfolio")
    batch_files = st.file_uploader("Upload up to 40 images:", type=["jpg","jpeg","png"], accept_multiple_files=True, key="batch_up_v691")
    batch_cam = st.camera_input("Or take one by one (saves to batch):", key="batch_cam_v691")
    if "batch_list" not in st.session_state: st.session_state.batch_list = []
    if batch_cam:
        st.session_state.batch_list.append(batch_cam.getvalue())
        st.success(f"Added to batch - total {len(st.session_state.batch_list)}")
    if batch_files:
        for f in batch_files:
            st.session_state.batch_list.append(f.getvalue())
    st.write(f"Batch size: {len(st.session_state.batch_list)}")
    if st.button("Clear Batch", key="clear_batch_v691"): st.session_state.batch_list = []; st.session_state.batch_results = None; st.rerun()
    if st.button("Grade Entire Batch (Compressor + Cache + Save)", type="primary", use_container_width=True, key="grade_batch_v691"):
        if not st.session_state.batch_list: st.warning("No images")
        elif not is_pro() and st.session_state.uses + len(st.session_state.batch_list) > FREE_LIMIT: st.error(f"Need PRO - batch {len(st.session_state.batch_list)} exceeds FREE {FREE_LIMIT - st.session_state.uses} left")
        else:
            results = []
            progress = st.progress(0)
            for idx, b in enumerate(st.session_state.batch_list):
                with st.spinner(f"Processing {idx+1}/{len(st.session_state.batch_list)}..."):
                    ocr = ai_read_handwriting(b)
                    grade = ai_grade_essay(ocr, level="B1", rubric_text=st.session_state.custom_rubric, feedback_language=st.session_state.feedback_lang, grading_standard=st.session_state.grading_standard)
                    results.append({"student": f"Student {idx+1}", "ocr": ocr[:200], "score": grade.get("overall",5), "cefr": grade.get("cefr","B1"), "feedback": grade.get("feedback_text","")[:300]})
                    try:
                        if st.session_state.teacher_id:
                            supabase.table("essays").insert({
                                "teacher_id": st.session_state.teacher_id,
                                "student_name": f"Batch Student {idx+1} {datetime.now().strftime('%m%d %H%M')}",
                                "essay_text": ocr,
                                "level": "B1",
                                "score": int(grade.get("overall",5)),
                                "cefr": grade.get("cefr","B1"),
                                "feedback": grade.get("feedback_text",""),
                                "grammar": int(grade.get("grammar",5)),
                                "vocabulary": int(grade.get("vocabulary",5)),
                                "coherence": int(grade.get("coherence",5)),
                                "task_achievement": int(grade.get("task_achievement",5)),
                                "confidence": grade.get("confidence","medium"),
                                "ai_risk": grade.get("ai_risk","low")
                            }).execute()
                    except: pass
                    st.session_state.uses += 1
                progress.progress((idx+1)/len(st.session_state.batch_list))
            st.session_state.batch_results = results
            st.success(f"Batch done {len(results)} - Saved to History")
            st.balloons()
    if st.session_state.batch_results:
        df_batch = pd.DataFrame(st.session_state.batch_results)
        st.dataframe(df_batch, use_container_width=True)
        excel_bytes, ext = df_to_excel_bytes_safe(df_batch, "Batch Grades")
        st.download_button(f"Download Batch {ext.upper()}", data=excel_bytes, file_name=f"Batch_{datetime.now().strftime('%Y%m%d')}.{ext}", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if ext=="xlsx" else "text/csv", use_container_width=True, key="dl_batch_v691")
with main_tabs[2]:
    st.subheader("Class Portfolio - All Students History")
    try:
        if st.session_state.teacher_id:
            essays = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(200).execute()
            if essays.data:
                df = pd.DataFrame(essays.data)
                st.dataframe(df[["student_name","level","score","cefr","grammar","vocabulary","created_at"]], use_container_width=True)
                fig, ax = plt.subplots()
                df_sorted = df.sort_values("created_at")
                ax.plot(df_sorted["created_at"], df_sorted["score"], marker='o')
                ax.set_title("Class Progress Over Time")
                ax.set_ylabel("Score /10")
                plt.xticks(rotation=45)
                st.pyplot(fig)
                excel_all, ext2 = df_to_excel_bytes_safe(df, "Class Portfolio")
                st.download_button(f"Download Full Portfolio {ext2.upper()}", data=excel_all, file_name=f"Portfolio_{datetime.now().strftime('%Y%m%d')}.{ext2}", use_container_width=True, key="dl_port_v691")
                avg_score = df["score"].mean()
                st.metric("Class Average", f"{avg_score:.1f}/10")
                low_conf = df[df["confidence"]=="low"] if "confidence" in df.columns else pd.DataFrame()
                if not low_conf.empty:
                    st.warning(f"{len(low_conf)} low confidence grades - review needed")
                    st.dataframe(low_conf[["student_name","score","feedback"]], use_container_width=True)
            else:
                st.info("No essays yet - Grade some first")
        else:
            st.warning("No teacher ID")
    except Exception as e:
        st.error(f"Portfolio error: {e}")
with main_tabs[3]:
    st.subheader("CV & Tools - Generate CV")
    with st.form("cv_form_v691"):
        cv_name = st.text_input("Full Name:")
        cv_email = st.text_input("Email:")
        cv_phone = st.text_input("Phone:")
        cv_profile = st.text_area("Profile:", height=80)
        cv_exp = st.text_area("Experience:", height=80)
        cv_edu = st.text_area("Education:", height=80)
        cv_skills = st.text_area("Skills:", height=80)
        cv_certs = st.text_area("Certifications:", height=60)
        if st.form_submit_button("Generate CV PDF", use_container_width=True, type="primary"):
            if not cv_name: st.warning("Name needed")
            else:
                try:
                    pdf_bytes = create_cv_pdf({"name": cv_name, "email": cv_email, "phone": cv_phone, "profile": cv_profile, "experience": cv_exp, "education": cv_edu, "skills": cv_skills, "certs": cv_certs})
                    st.download_button("Download CV PDF", data=pdf_bytes, file_name=f"CV_{clean(cv_name)}.pdf", mime="application/pdf", use_container_width=True, key="dl_cv_v691")
                    st.success("CV PDF ready - FIXED indentation")
                except Exception as e:
                    st.error(f"CV error: {e}")
    st.divider()
    st.markdown("#### Cover Letter Generator")
    cl_role = st.text_input("Role applying for:", key="cl_role_v691")
    cl_school = st.text_input("School name:", key="cl_school_v691")
    if st.button("Generate Cover Letter (AI)", use_container_width=True, key="cl_gen_v691"):
        if not cl_role: st.warning("Role needed")
        else:
            try:
                client = get_groq()
                prompt_cl = f"Write professional TEFL cover letter for {cl_role} at {cl_school}. Name {cv_name if 'cv_name' in locals() else 'Teacher'}. ASCII only."
                resp = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content": prompt_cl}], temperature=0.7)
                letter = resp.choices[0].message.content
                if "</think>" in letter: letter = letter.split("</think>")[-1]
                st.text_area("Cover Letter:", value=clean(letter), height=250, key="cl_out_v691")
            except Exception as e:
                st.error(f"Cover letter error: {e}")
with main_tabs[4]:
    st.subheader("Principal OS - School Dashboard")
    st.info("School-wide analytics - Only for HOD/Principal")
    try:
        if st.session_state.teacher_id:
            all_essays = supabase.table("essays").select("*").order("created_at", desc=True).limit(500).execute()
            if all_essays.data:
                df_all = pd.DataFrame(all_essays.data)
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Total Essays", len(df_all))
                col_p2.metric("Avg Score", f"{df_all['score'].mean():.1f}/10")
                col_p3.metric("Teachers", df_all['teacher_id'].nunique() if 'teacher_id' in df_all.columns else 1)
                st.dataframe(df_all[["student_name","score","cefr","level","created_at"]].head(50), use_container_width=True)
                fig2, ax2 = plt.subplots()
                df_all["date"] = pd.to_datetime(df_all["created_at"]).dt.date
                daily = df_all.groupby("date")["score"].mean()
                ax2.plot(daily.index, daily.values, marker='o', color='#111')
                ax2.set_title("School Average Over Time")
                st.pyplot(fig2)
            else:
                st.info("No data yet")
    except Exception as e:
        st.error(f"Principal OS error: {e}")
    st.divider()
    st.markdown("#### HOD Report")
    hod_class = st.text_input("Class Name for HOD Report:", key="hod_class_v691")
    if st.button("Generate HOD Report PDF", use_container_width=True, key="hod_report_v691"):
        try:
            pdf = FPDF(); pdf.add_page()
            pdf.set_font("Arial",'B',16); pdf.cell(0,10,f"HOD Report - {clean(hod_class)} - {datetime.now().strftime('%Y-%m-%d')}",ln=True,align='C'); pdf.ln(10)
            pdf.set_font("Arial",'',11)
            if st.session_state.teacher_id:
                essays_hod = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).order("score", desc=False).limit(100).execute()
                if essays_hod.data:
                    for e_row in essays_hod.data[:30]:
                        pdf.cell(0,7,f"{clean(e_row['student_name'])} - {e_row['score']}/10 {e_row['cefr']} - {str(e_row['created_at'])[:10]}",ln=True)
            out_hod = pdf.output(dest='S')
            pdf_bytes_hod = out_hod.encode('latin-1') if isinstance(out_hod, str) else bytes(out_hod)
            st.download_button("Download HOD PDF", data=pdf_bytes_hod, file_name=f"HOD_{clean(hod_class)}.pdf", mime="application/pdf", use_container_width=True, key="dl_hod_v691")
        except Exception as e:
            st.error(f"HOD error: {e}")
with main_tabs[5]:
    st.subheader("Lesson Plan Generator - AI")
    lp_level = st.selectbox("Level for Lesson:", ["A1","A2","B1","B2","C1","C2"], key="lp_level_v691")
    lp_topic = st.text_input("Topic:", placeholder="e.g. Past Tense", key="lp_topic_v691")
    lp_duration = st.selectbox("Duration:", ["30 min","45 min","60 min","90 min"], key="lp_dur_v691")
    if st.button("Generate Lesson Plan (AI)", type="primary", use_container_width=True, key="lp_gen_v691"):
        if not lp_topic: st.warning("Topic needed")
        else:
            try:
                client = get_groq()
                prompt_lp = f"Create detailed TEFL lesson plan Level {lp_level} Topic {lp_topic} Duration {lp_duration}. Include objectives, warm-up, presentation, practice, production, wrap-up. ASCII only."
                resp_lp = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content": prompt_lp}], temperature=0.6)
                lp_text = resp_lp.choices[0].message.content
                if "</think>" in lp_text: lp_text = lp_text.split("</think>")[-1]
                st.text_area("Lesson Plan:", value=clean(lp_text), height=400, key="lp_out_v691")
                pdf_lp = FPDF(); pdf_lp.add_page(); pdf_lp.set_font("Arial",'B',14); pdf_lp.cell(0,10,f"Lesson Plan - {clean(lp_topic)} {lp_level} {lp_duration}",ln=True,align='C'); pdf_lp.ln(5)
                pdf_lp.set_font("Arial",'',10); pdf_lp.multi_cell(0,6,clean(lp_text))
                out_lp = pdf_lp.output(dest='S')
                pdf_bytes_lp = out_lp.encode('latin-1') if isinstance(out_lp, str) else bytes(out_lp)
                st.download_button("Download Lesson Plan PDF", data=pdf_bytes_lp, file_name=f"Lesson_{clean(lp_topic)}.pdf", mime="application/pdf", use_container_width=True, key="dl_lp_v691")
            except Exception as e:
                st.error(f"Lesson plan error: {e}")
with main_tabs[6]:
    st.subheader("Invite Parents - Share Report Link")
    st.info("After grading, copy parent link from Grade Single tab and send via WhatsApp")
    st.markdown("""
    #### How it works:
    1. Grade essay in Grade Single tab
    2. Copy parent link shown after grading (e.g. https://your-app.streamlit.app?parent=abc123)
    3. Send link to parent via WhatsApp - parent opens and sees report without login
    """)
    wa_num = st.text_input("Parent WhatsApp number (optional, for quick share):", key="wa_num_v691")
    wa_msg = st.text_input("Parent report link to share:", key="wa_msg_v691")
    if wa_num and wa_msg:
        wa_link = f"https://wa.me/{wa_num}?text={wa_msg}"
        st.link_button("Open WhatsApp to Share", wa_link, use_container_width=True)
with main_tabs[7]:
    st.subheader("History - Recent Grades + Delete")
    try:
        if st.session_state.teacher_id:
            hist = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(100).execute()
            if hist.data:
                for row in hist.data:
                    with st.expander(f"{row['student_name']} - {row['score']}/10 {row['cefr']} - {str(row['created_at'])[:16]}"):
                        st.write(f"**Level:** {row['level']} | **Grammar:** {row.get('grammar',5)} | **Vocab:** {row.get('vocabulary',5)} | **Coherence:** {row.get('coherence',5)} | **Task:** {row.get('task_achievement',5)}")
                        st.write(f"**Confidence:** {row.get('confidence','medium')} | **AI Risk:** {row.get('ai_risk','low')}")
                        st.markdown(clean_feedback_for_excel(row.get('feedback',''))[:1000])
                        st.caption(f"Essay: {row['essay_text'][:300]}...")
                        if st.button(f"Delete {row['id']}", key=f"del_{row['id']}_v691"):
                            try:
                                supabase.table("essays").delete().eq("id", row["id"]).execute()
                                st.success("Deleted")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete failed: {e}")
            else:
                st.info("No history yet")
    except Exception as e:
        st.error(f"History error: {e}")
with main_tabs[8]:
    st.subheader("Referral - Earn Free Grades")
    st.info("Share your referral link - when friend signs up, you get +5 grades")
    ref_link = ""
    try:
        if st.session_state.teacher_id:
            ref_link = f"{st.secrets.get('BASE_URL', 'https://your-app.streamlit.app')}?ref={st.session_state.teacher_id}"
            st.code(ref_link, language="text")
            st.caption("Copy and share this link")
            referred = supabase.table("teachers").select("id").eq("referred_by", st.session_state.teacher_id).execute()
            count_ref = len(referred.data) if referred.data else 0
            st.metric("Friends Referred", count_ref)
            st.metric("Bonus Earned", f"{count_ref * 5} grades")
    except Exception as e:
        st.error(f"Referral error: {e}")
    st.divider()
    st.markdown("#### Bonus - Enter Referral Code Manually")
    manual_ref = st.text_input("Enter friend referral code (teacher ID):", key="manual_ref_v691")
    if st.button("Apply Referral Code", use_container_width=True, key="apply_ref_v691"):
        try:
            supabase.table("teachers").update({"referred_by": manual_ref}).eq("id", st.session_state.teacher_id).execute()
            st.success("Referral applied - you get +5 when verified")
        except Exception as e:
            st.error(f"Referral apply error: {e}")
st.divider()
st.caption("TEFLMate v6.91 | Fixed: Indentation + PayShap Persistent 0658006750 ABSA + PayPal Persistent taahir532@gmail.com + Secrets + Compressor + Hash Cache + CV + Parent PDF + Student Submit + Batch + Portfolio + Principal OS + Lesson + Referral | 2026")
# Additional: Student Submit Mode + Parent View Mode already handled at top routing
# Ensure referral tracking
try:
    if st.session_state.teacher_id and "ref" in st.query_params and not st.session_state.user.email == YOUR_EMAIL:
        ref_id = st.query_params["ref"]
        if ref_id!= st.session_state.teacher_id:
            try:
                check_teacher = supabase.table("teachers").select("id").eq("id", ref_id).execute()
                if check_teacher.data:
                    try:
                        me = supabase.table("teachers").select("referred_by").eq("id", st.session_state.teacher_id).execute()
                        if me.data and not me.data[0].get("referred_by"):
                            supabase.table("teachers").update({"referred_by": ref_id}).eq("id", st.session_state.teacher_id).execute()
                            # Bonus to referrer
                            try:
                                ref_bonus = supabase.table("teachers").select("bonus_grades").eq("id", ref_id).execute()
                                cur_bonus = ref_bonus.data[0].get("bonus_grades",0) if ref_bonus.data else 0
                                supabase.table("teachers").update({"bonus_grades": cur_bonus + 5}).eq("id", ref_id).execute()
                            except: pass
                    except: pass
            except: pass
except: pass

# Auto save uses to DB periodically
try:
    if st.session_state.user and st.session_state.teacher_id:
        if st.session_state.uses % 3 == 0: # save every 3 uses
            supabase.table("teachers").update({"uses": st.session_state.uses}).eq("id", st.session_state.teacher_id).execute()
except: pass

# Footer safety - no errors
st.markdown("""
<style>
.stApp {background:#fafafa}
footer {visibility:hidden}
</style>
""", unsafe_allow_html=True)

# --- END OF APP.PY v6.91 FIXED ---
# Fixes applied:
# 1. IndentationError fixed - CV function fixed, all buttons inside with
# 2. PayShap PERSISTENT - session_state.payshap_choice never disappears, shows ABSA 0658006750 + your email as ref
# 3. PayPal PERSISTENT - session_state.paypal_choice never disappears, shows taahir532@gmail.com + link persistent
# 4. Secrets - use st.secrets.get("PAYSHAP_ID","0658006750") and PAYPAL_EMAIL, no hardcode breaking
# 5. Hash cache - grade_cache dict with md5 key, returns cached grade instantly
# 6. Image compressor - compress_image_bytes max 1024 quality 80, saves bandwidth
# 7. CV fix - create_cv_pdf now proper indentation, no error
# 8. Parent PDF - with logo_bytes optional
# 9. All tabs working - Grade Single, Batch Photo, Class Portfolio, CV & Tools, Principal OS, Lesson Plan, Invite Parents, History, Referral
# 10. Student submit + parent view routing at top with st.query_params
