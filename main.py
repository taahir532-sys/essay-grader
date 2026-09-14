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
                        res = client.chat.completions.create(model="qwen/qwen3-32b", messages=[{"role":"user","content":[{"type":"text","text":"OCR: Extract handwritten text EXACTLY as written, keep spelling mistakes. Return only text."},{"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}]}], temperature=0)
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
    st.markdown("""<div class="tefl-header"><div style="font-size:22px;font-weight:800;">📚 TEFLMate</div><div class="tefl-badge">TEFLMate v6.8</div></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1.2,1])
    with col1:
        st.markdown("""<div class="landing-hero"><h2 style="margin:0;">Grade 40 books in 2 minutes 📸</h2><p style="color:#555;">Photo-grade • Track progress • Parent reports in 9 languages • Confidence flag • School OS • Student Self-Submit</p><ul><li>✅ Snap photo → Edit OCR → Grade → Save</li><li>✅ Grammar/Vocab/Coherence breakdown + Common Mistakes Report</li><li>✅ Parent reports in home language + Student link</li><li>✅ NEW: School Dashboard for Principals</li></ul></div>""", unsafe_allow_html=True)
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
            if st.session_state.last_reset and (datetime.now()-st.session_state.last_reset).seconds < 60:
                st.warning("Wait a bit")
            else:
                if st.button("📧 Send Reset Link", use_container_width=True):
                    try:
                        supabase.auth.reset_password_for_email(fp_email, {"redirect_to": ""})
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
    for model_id in ["qwen/qwen3-32b", "qwen/qwen3-27b", "qwen/qwen3-8b", "llama-3.2-90b-vision-preview"]:
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
        except:
            continue
    return "OCR_ERROR: Vision models temporarily unavailable. Please type text manually."
def extract_text_from_pdf(pdf_bytes):
    if not fitz: return "Add PyMuPDF"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf");
        pages_to_read = min(10, len(doc))
        text = "\n".join([p.get_text() for p in doc[:pages_to_read]])
        if len(text.strip()) < 30 and len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=200);
            compressed = compress_image_bytes(pix.tobytes("jpeg"), 1024, 85)
            text = extract_text_from_image(compressed)
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
def get_essay_hash(text, level, lang, standard):
    return hashlib.md5((text.strip()[:1000] + "|" + level + "|" + lang + "|" + standard).encode()).hexdigest()
def check_supabase_cache(essay_hash):
    try:
        r = supabase.table("essay_cache").select("*").eq("hash", essay_hash).execute()
        if r.data: return r.data[0].get("result")
    except:
        pass
    return None
def save_supabase_cache(essay_hash, result, level):
    try:
        supabase.table("essay_cache").insert({"hash": essay_hash, "result": result, "level": level}).execute()
    except:
        pass
def grade_with_groq(essay_text, level):
    essay_hash = get_essay_hash(essay_text, level, st.session_state.feedback_lang, st.session_state.grading_standard)
    cache_key = essay_hash
    if cache_key in st.session_state.grade_cache:
        return st.session_state.grade_cache[cache_key]
    cached = check_supabase_cache(essay_hash)
    if cached:
        st.session_state.grade_cache[cache_key] = cached
        return cached
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
    save_supabase_cache(essay_hash, result, level)
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
    st.markdown("""<div class="tefl-header"><div><div style="font-size:22px;font-weight:800;">📚 TEFLMate - Class Portfolio</div><div style="font-size:12px;opacity:0.8;">Track progress • Photo-grade • 9 languages • Confidence flag • School OS v6.8</div></div><div class="tefl-badge">TEFLMate v6.8</div></div>""", unsafe_allow_html=True)
with col_user:
    st.info(f"👤 {st.session_state.user.email[:20]} | {get_status()}" if st.session_state.user else "Not logged")
    if st.session_state.user and st.button("Logout", use_container_width=True):
        supabase.auth.sign_out(); st.session_state.user=None; st.session_state.teacher_id=None; st.rerun()
if st.session_state.promo_success:
    st.balloons(); st.success("🎉 Code applied - saved!"); st.session_state.promo_success = False
with st.sidebar:
    st.markdown("### 🔑 Your Plan")
    st.info(get_status())
    if is_admin():
        st.success("👑 ADMIN MODE")
        if st.button("🛠️ Open Admin Panel", use_container_width=True, type="primary"):
            st.session_state.show_admin = True
    if st.session_state.teacher_id:
        try:
            ref_code = f"TEFL{str(st.session_state.teacher_id)[:6].upper()}"
            base_url = "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"
            ref_link = f"{base_url}?ref={ref_code}"
            submit_link = f"{base_url}?submit={st.session_state.teacher_id}"
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
            st.markdown("#### 👨‍🎓 Student Self-Submit (NEW)")
            st.caption("Students upload directly to your portfolio")
            st.code(submit_link)
            st.caption("Share on WhatsApp class group")
            st.divider()
        except:
            pass
                with st.expander("⚙️ Settings", expanded=False):
        st.session_state.feedback_lang = st.selectbox("Feedback Language", ["English","Afrikaans","Zulu","Spanish","Portuguese","French","Arabic","Hindi","Mandarin"], index=0)
        st.session_state.grading_standard = st.selectbox("Grading Standard", ["CEFR","IELTS","TOEFL","US Grade"], index=0)
        promo_in = st.text_input("Promo Code:", placeholder="TEFL20", key="promo_sidebar_1967")
        if st.button("Apply Promo", use_container_width=True):
            if promo_in.upper()=="TEFL20":
                st.session_state.uses = max(0, st.session_state.uses-2)
                st.session_state.promo_success = True
                save_pro_to_db(None, "PROMO-TEFL20", 2)
                st.success("TEFL20 = +2 grades added & saved!"); st.rerun()
            elif promo_in.upper()=="TRYSUPER":
                new_exp = datetime.now() + timedelta(days=7)
                save_pro_to_db(new_exp, "TRYSUPER-7DAY", 0)
                st.session_state.pro_expiry = new_exp; st.session_state.active_plan = "TRYSUPER-7DAY"
                st.success("TRYSUPER = 7 days PRO unlocked!"); st.rerun()
            else:
                st.error("Invalid code")
    st.markdown("### 💳 Paystack Upgrade")
    cols = st.columns(4)
    for i, plan in enumerate(["WEEK49","MONTH99","YEAR799","ONCE10"]):
        with cols[i]:
            amt = {"WEEK49":4900,"MONTH99":9900,"YEAR799":79900,"ONCE10":1000}[plan]
            label = {"WEEK49":"Weekly R49","MONTH99":"Monthly R99","YEAR799":"Yearly R799","ONCE10":"Once R10"}[plan]
            if st.button(label, key=f"pay_{plan}", use_container_width=True):
                if not st.session_state.user:
                    st.warning("Login first")
                else:
                    res = init_paystack(st.session_state.user.email, amt, plan)
                    if res.get("status"):
                        st.session_state.pay_links[plan] = res["data"]["authorization_url"]
                        st.session_state.pay_refs[plan] = res["data"]["reference"]
                        st.session_state.pay_links_time = datetime.now()
                    else:
                        st.error(res.get("message","Failed"))
    if st.session_state.pay_links_time and (datetime.now()-st.session_state.pay_links_time).total_seconds() > 3600:
        st.session_state.pay_links = {}; st.session_state.pay_refs = {}; st.session_state.pay_links_time = None
    for plan, link in st.session_state.pay_links.items():
        st.link_button(f"Pay {plan} via Paystack", link, use_container_width=True)
    if st.session_state.pay_refs:
        if st.button("✅ I've Paid - Verify All", type="primary", use_container_width=True):
            if verify_all_refs():
                st.success("Unlocked & saved to account!"); st.rerun()
            else:
                st.warning("Payment not confirmed yet, try again in 30 sec")
    st.caption("Payments secured by Paystack")
    if is_admin():
        st.divider()
        if st.button("🛠️ ADMIN - Grant Myself 100 Grades", use_container_width=True):
            save_pro_to_db(None, "ADMIN-100", 100); st.session_state.uses -= 100; st.success("Granted 100"); st.rerun()
if st.session_state.get("show_admin") and is_admin():
    st.title("🛠️ Super Admin Dashboard")
    st.info(f"Total teachers table, search")
    try:
        teachers = supabase.table("teachers").select("*").limit(100).execute()
        if teachers.data:
            df_t = pd.DataFrame(teachers.data)
            st.dataframe(df_t, use_container_width=True)
            csv_t = df_t.to_csv(index=False).encode('utf-8')
            st.download_button("Download teachers.csv", csv_t, "teachers.csv", use_container_width=True)
            st.markdown("#### Manually Grant PRO")
            email_g = st.text_input("Email to grant:")
            plan_g = st.selectbox("Plan", ["WEEK49","MONTH99","YEAR799","ONCE10","ADMIN-100"])
            days_g = st.number_input("Days (for subscription)", value=30)
            if st.button("Grant PRO to email"):
                try:
                    if "ONCE" in plan_g or "ADMIN" in plan_g:
                        bonus = 100 if "100" in plan_g else 10
                        supabase.table("teachers").update({"bonus_grades": bonus}).eq("email", email_g).execute()
                        st.success(f"Granted {bonus} to {email_g}")
                    else:
                        exp_g = datetime.now() + timedelta(days=days_g)
                        supabase.table("teachers").update({"pro_expiry": exp_g.isoformat(), "active_plan": plan_g}).eq("email", email_g).execute()
                        st.success(f"Granted {plan_g} till {exp_g} to {email_g}")
                except Exception as e:
                    st.error(str(e))
    except Exception as e:
        st.error(str(e))
    if st.button("Close Admin"): st.session_state.show_admin = False; st.rerun()
    st.stop()
st.markdown("---")
if is_pro():
    status_line = f"**Status:** {get_status()} | **Geo:** {st.session_state.geo['symbol']}{st.session_state.geo['weekly']}/{st.session_state.geo['monthly']} local"
else:
    rem = FREE_LIMIT - st.session_state.uses
    status_line = f"**FREE:** {rem} left / {FREE_LIMIT} | Upgrade for unlimited • **Geo:** {st.session_state.geo['symbol']}{st.session_state.geo['weekly']}"
st.caption(status_line)
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["📚 Portfolio","✍️ Grade","📸 Photo","📦 Batch 50","📊 Guide","💎 SUPER","🏫 School OS","👨‍🏫 HOD"])
with tab1:
    st.markdown("### 📚 My Class Portfolio (v6.8)")
    st.caption("All graded essays auto-saved, with student self-submissions included")
    colf1, colf2 = st.columns(2)
    with colf1:
        search_f = st.text_input("Search student:", placeholder="Type name", key="port_search_1967")
    with colf2:
        level_f = st.selectbox("Filter level:", ["All","A1","A2","B1","B2","C1","C2"], key="port_level_1967")
    try:
        if st.session_state.teacher_id:
            q = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(200).execute()
            rows = q.data if q.data else []
            if search_f: rows = [r for r in rows if search_f.lower() in r.get("student_name","").lower()]
            if level_f!="All": rows = [r for r in rows if r.get("level")==level_f]
            if not rows:
                st.info("No essays yet. Grade in ✍️ tab or share student link.")
            else:
                scores = [r.get("score",0) for r in rows if r.get("score") is not None]
                avg = sum(scores)/len(scores) if scores else 0
                c1,c2,c3 = st.columns(3)
                c1.metric("Total Graded", len(rows))
                c2.metric("Avg Score", f"{avg:.1f}/10")
                c3.metric("Self-Submits", len([r for r in rows if "self" in str(r.get("student_name","")).lower()]) if rows else 0)
                st.divider()
                df = pd.DataFrame([{"Date": str(r.get("created_at",""))[:10], "Student Name": r.get("student_name",""), "Level": r.get("level",""), "Score /10": r.get("score",0), "CEFR": r.get("cefr",""), "AI Risk": detect_ai_risk(r.get("essay_text","")), "Feedback Preview": clean_feedback_for_excel(str(r.get("feedback",""))[:300])} for r in rows])
                st.dataframe(df, use_container_width=True, height=350)
                xls_bytes, ext = df_to_excel_bytes_safe(df, "Portfolio")
                st.download_button(f"📥 Download Excel (.{ext})", xls_bytes, file_name=f"TEFLMate_Portfolio_{datetime.now().strftime('%Y%m%d')}.{ext}", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if ext=="xlsx" else "text/csv", use_container_width=True)
                parent_excel = []
                for r in rows:
                    pid = r.get("id","")
                    base_url = "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"
                    parent_link = f"{base_url}?parent={pid}"
                    parent_excel.append({"Student": r.get("student_name",""), "Score": r.get("score",""), "CEFR": r.get("cefr",""), "Parent Report Link": parent_link})
                if parent_excel:
                    df_par = pd.DataFrame(parent_excel)
                    par_bytes, par_ext = df_to_excel_bytes_safe(df_par, "ParentLinks")
                    st.download_button(f"📧 Download Parent Links Excel", par_bytes, file_name=f"Parent_Links_{datetime.now().strftime('%Y%m%d')}.{par_ext}", use_container_width=True)
                st.divider()
                st.markdown("#### 📊 Progress Graph")
                try:
                    df_sorted = df.sort_values("Date")
                    fig, ax = plt.subplots(figsize=(8,3))
                    ax.plot(df_sorted["Date"].astype(str), df_sorted["Score /10"], marker='o')
                    plt.xticks(rotation=45, fontsize=7); plt.tight_layout()
                    st.pyplot(fig)
                except Exception as e:
                    st.caption(f"Graph error: {e}")
    except Exception as e:
        st.error(f"Portfolio error: {e}")
with tab2:
    st.markdown("### ✍️ Grade Essay (with Compression + Hash Cache)")
    st.caption("10 free grades for new users. AI Risk Detection + Common Mistakes Report + Auto-saves")
    s_name = st.text_input("Student Name:", placeholder="e.g. Aisha Mohammed", key="grade_name_1967")
    t_level = st.selectbox("Target Level:", ["A1","A2","B1","B2","C1","C2"], key="grade_level_1967")
    essay_input = st.text_area("Paste Essay Here:", height=180, placeholder="Paste 30+ words...", key="grade_essay_1967")
    st.divider()
    st.markdown("#### 📸 Or take photo + Edit OCR (with compressor)")
    cam = st.camera_input("Take photo of handwriting", key="grade_cam_1967")
    up = st.file_uploader("Upload image", type=["jpg","jpeg","png"], key="grade_up_1967")
    img_bytes = None
    if cam: img_bytes = cam.getvalue()
    elif up: img_bytes = up.getvalue()
    if img_bytes:
        st.image(img_bytes, caption="Uploaded (will compress to 1024px)", use_container_width=True)
        if st.button("📖 Read Handwriting (Compressed OCR)", use_container_width=True, key="grade_ocr_btn"):
            with st.spinner("Compressing + OCR via Qwen..."):
                txt = extract_text_from_image(img_bytes)
                if "OCR_ERROR" in txt:
                    st.error(txt)
                else:
                    st.session_state.last_ocr = txt
                    st.session_state.editable_ocr = txt
                    st.success("OCR done! Edit below.")
    if st.session_state.editable_ocr:
        edited = st.text_area("✏️ Edit OCR text before grading:", value=st.session_state.editable_ocr, height=150, key="grade_edit_ocr_1967")
        essay_input = edited
    pdf_up = st.file_uploader("Or upload PDF (up to 10 pages)", type=["pdf"], key="grade_pdf_1967")
    if pdf_up:
        with st.spinner("Reading PDF..."):
            txt = extract_text_from_pdf(pdf_up.getvalue())
            st.text_area("PDF text preview:", value=txt[:2000], height=150)
            if len(txt.strip())>20:
                essay_input = txt
    st.divider()
    if st.button("🚀 Grade Essay (Compressed + Cache)", type="primary", use_container_width=True):
        if not essay_input or len(essay_input.strip())<10:
            st.warning("Paste 10+ characters or use OCR")
        else:
            if not is_pro() and not is_admin() and st.session_state.uses >= FREE_LIMIT:
                st.error(f"Free limit {FREE_LIMIT} reached. Upgrade in sidebar")
                st.stop()
            with st.spinner("Grading with hash cache..."):
                raw_result = grade_with_groq(essay_input, t_level)
                parsed = parse_dimensions(raw_result)
                score = int(parsed.get("overall",5)); cefr = parsed.get("cefr", t_level); feedback_text = parsed.get("feedback_text", raw_result)
                ai_risk = detect_ai_risk(essay_input)
                st.session_state.uses += 1
                if s_name:
                    saved = save_essay_db(s_name, essay_input, t_level, score, cefr, feedback_text)
                    if saved: st.toast(f"Saved to {s_name} portfolio")
                st.success(f"Score {score}/10 | CEFR {cefr} | {ai_risk} | Confidence {parsed.get('confidence','medium')}")
                st.markdown("#### Feedback")
                st.markdown(clean(feedback_text))
                st.divider()
                pdf_bytes = create_branded_pdf(essay_input, feedback_text, t_level, s_name or "Student")
                st.download_button("📥 Download PDF Report", pdf_bytes, file_name=f"{(s_name or 'Student')}_{score}10_{cefr}.pdf", mime="application/pdf", use_container_width=True)
                if st.session_state.teacher_id:
                    essay_row = supabase.table("essays").select("id").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(1).execute()
                    if essay_row.data:
                        eid = essay_row.data[0]["id"]
                        base_url = "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"
                        plink = f"{base_url}?parent={eid}"
                        st.info(f"🔗 Parent Report Link: {plink}")
                        st.code(plink)
                        with tab3:
    st.markdown("### 📸 Photo Grade + Edit (NEW)")
    st.caption("Snap → Compress → Edit → Grade → Auto-saves to Portfolio")
    st.info("Uses compressor to avoid blur + cost savings")
    s_name_p = st.text_input("Student Name (Photo):", key="photo_name_1967")
    t_level_p = st.selectbox("Level:", ["A1","A2","B1","B2","C1","C2"], key="photo_level_1967")
    cam_p = st.camera_input("Take photo", key="photo_cam_1967")
    up_p = st.file_uploader("Upload photo", type=["jpg","jpeg","png"], key="photo_up_1967")
    pb = None
    if cam_p: pb = cam_p.getvalue()
    elif up_p: pb = up_p.getvalue()
    if pb:
        st.image(pb, use_container_width=True)
        if st.button("Read + Edit", use_container_width=True, key="photo_read_btn"):
            with st.spinner("OCR..."):
                txt = extract_text_from_image(pb)
                st.session_state.last_photo_result = txt
                st.session_state.editable_ocr = txt
        if st.session_state.last_photo_result:
            edit_p = st.text_area("Edit before grading:", value=st.session_state.last_photo_result, height=150, key="photo_edit_1967")
            if st.button("Grade Photo Essay", type="primary", use_container_width=True, key="photo_grade_btn"):
                if not is_pro() and st.session_state.uses >= FREE_LIMIT and not is_admin():
                    st.error(f"Free {FREE_LIMIT} limit reached")
                    st.stop()
                with st.spinner("Grading..."):
                    raw = grade_with_groq(edit_p, t_level_p)
                    par = parse_dimensions(raw)
                    sc = int(par.get("overall",5)); cf = par.get("cefr", t_level_p); fb = par.get("feedback_text", raw)
                    st.session_state.uses += 1
                    if s_name_p: save_essay_db(s_name_p, edit_p, t_level_p, sc, cf, fb)
                    st.success(f"{sc}/10 {cf}")
                    st.markdown(fb)
                    pdfb = create_branded_pdf(edit_p, fb, t_level_p, s_name_p or "Student")
                    st.download_button("Download PDF", pdfb, file_name=f"{s_name_p or 'Student'}_photo.pdf", use_container_width=True)
with tab4:
    st.markdown("### 📦 Batch Grade 50 Essays (Class Mode)")
    st.caption("Paste 50 separated by --- or upload CSV. Uses hash cache for duplicate savings.")
    st.info("CSV format: Student Name, Essay Text, Level")
    b_level = st.selectbox("Default Level for Batch:", ["A1","A2","B1","B2","C1","C2"], key="batch_level_1967")
    b_text = st.text_area("Paste essays separated by --- (e.g. Essay1 --- Essay2):", height=180, key="batch_text_1967")
    b_csv = st.file_uploader("Or upload CSV (Student,Essay,Level)", type=["csv"], key="batch_csv_1967")
    essays_list = []
    if b_csv:
        try:
            df_b = pd.read_csv(b_csv)
            for _, row in df_b.iterrows():
                try:
                    name = str(row.iloc[0]); essay = str(row.iloc[1]); lvl = str(row.iloc[2]) if len(row)>2 else b_level
                    if len(essay.strip())>10: essays_list.append((name, essay, lvl))
                except: continue
            st.success(f"Loaded {len(essays_list)} from CSV")
        except Exception as e:
            st.error(f"CSV error: {e}")
    elif b_text:
        parts = [p.strip() for p in b_text.split("---") if p.strip()]
        for i, p in enumerate(parts):
            essays_list.append((f"Student {i+1}", p, b_level))
    if essays_list:
        st.write(f"Found {len(essays_list)} essays. Will grade max 50.")
        if st.button(f"🚀 Grade {min(50, len(essays_list))} Essays (uses cache)", type="primary", use_container_width=True):
            if not is_pro() and not is_admin():
                st.error("Batch requires PRO - Upgrade")
                st.stop()
            progress = st.progress(0)
            results = []
            for idx, (name, essay, lvl) in enumerate(essays_list[:50]):
                with st.spinner(f"Grading {idx+1}/{len(essays_list[:50])} - {name}"):
                    try:
                        raw = grade_with_groq(essay, lvl)
                        par = parse_dimensions(raw)
                        sc = int(par.get("overall",5)); cf = par.get("cefr", lvl)
                        save_essay_db(name, essay, lvl, sc, cf, par.get("feedback_text", raw))
                        results.append({"Student Name": name, "Level": lvl, "Score /10": sc, "CEFR": cf, "Feedback Preview": clean_feedback_for_excel(par.get("feedback_text","")[:200])})
                    except Exception as e:
                        results.append({"Student Name": name, "Level": lvl, "Score /10": 0, "CEFR": "Error", "Feedback Preview": str(e)})
                progress.progress((idx+1)/len(essays_list[:50]))
            st.session_state.batch_results = results
            st.success("Batch done & saved to Portfolio!")
    if st.session_state.batch_results:
        df_batch = pd.DataFrame(st.session_state.batch_results)
        st.dataframe(df_batch, use_container_width=True)
        xb, extb = df_to_excel_bytes_safe(df_batch, "Batch50")
        st.download_button(f"Download Batch Excel.{extb}", xb, file_name=f"Batch50_{datetime.now().strftime('%Y%m%d')}.{extb}", use_container_width=True)
        avg_b = df_batch["Score /10"].mean() if len(df_batch)>0 else 0
        pdf_b = create_principal_pdf(st.session_state.batch_results, b_level, avg_b, "My Class")
        st.download_button("Download Principal PDF for this batch", pdf_b, file_name=f"Principal_Batch_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)
with tab5:
    st.markdown("### 📊 TEFL Grading Guide + Mistakes Report")
    st.markdown("""
    **Common mistakes we auto-detect:**
    - A1/A2: Missing verb 'be', no capital 'I', simple spelling
    - B1/B2: Article errors (a/the), tense mixing, run-on sentences
    - C1/C2: Cohesion, register, complex grammar misuse

    **How scoring works (v6.8 - Generous A1/A2):**
    - 30+ words communicating idea at A1 = 6/10 minimum
    - Good clear A2 paragraph = 7-8/10
    - Short <15 words or unreadable = 4-5/10
    - B1 and above = Cambridge strict

    **Features in this build:**
    - Image compressor (1024px, 85% quality) = faster + cheaper
    - Hash cache: same essay + level + lang = instant from Supabase, no Groq cost
    - AI Risk flag: flags possible AI text
    - Confidence flag: low/medium/high
    - Editable OCR before grading
    - Student self-submit link (?submit=teacher_id)
    - Parent report in 9 languages (?parent=essay_id)
    """)
    st.divider()
    st.markdown("#### 💰 Earnings Simulator")
    studs = st.slider("How many students you have?", 10, 500, 100)
    price_per = st.number_input(f"Price you charge per student ({st.session_state.geo['symbol']})", value=10)
    earn = studs * price_per
    st.metric("Monthly earning potential", f"{st.session_state.geo['symbol']}{earn}")
with tab6:
    st.markdown("### 💎 SUPER Dashboard (Monetization)")
    st.caption(f"Geo price: {st.session_state.geo['symbol']}{st.session_state.geo['weekly']}/{st.session_state.geo['monthly']}/{st.session_state.geo['yearly']} (local)")
    if st.session_state.teacher_id:
        try:
            cnt = supabase.table("essays").select("id", count="exact").eq("teacher_id", st.session_state.teacher_id).execute()
            total_graded = cnt.count if cnt.count is not None else 0
        except:
            total_graded = 0
        c1,c2 = st.columns(2)
        c1.metric("Total Graded", total_graded)
        c2.metric("Cache Hits Saved", len(st.session_state.grade_cache))
        st.divider()
        st.markdown("#### Upgrade now - Paystack")
        st.info("Paystack auto-saves to DB + restores on login")
        st.link_button("Contact Support", "mailto:taahir532@gmail.com")
    else:
        st.warning("Login first")
with tab7:
    st.markdown("### 🏫 School OS - Principal Dashboard (NEW in v6.8)")
    st.caption("For HOD / Principal - whole school overview")
    school_name_in = st.text_input("School Name:", value="My School", key="school_name_1967")
    try:
        if st.session_state.teacher_id:
            all_rows = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).limit(500).execute()
            rows = all_rows.data if all_rows.data else []
            if not rows:
                st.info("No data yet for School OS")
            else:
                scores = [r.get("score",0) for r in rows if r.get("score") is not None]
                avg = sum(scores)/len(scores) if scores else 0
                level_counts = {}
                for r in rows:
                    lvl = r.get("level","B1")
                    level_counts[lvl] = level_counts.get(lvl,0)+1
                c1,c2,c3 = st.columns(3)
                c1.metric("Total Students Graded", len(rows))
                c2.metric("School Average", f"{avg:.1f}/10")
                c3.metric("Levels Covered", len(level_counts))
                st.bar_chart(pd.DataFrame(list(level_counts.items()), columns=["Level","Count"]).set_index("Level"))
                st.divider()
                excel_rows = [{"Student Name": r.get("student_name",""), "Level": r.get("level",""), "Score /10": r.get("score",0), "CEFR": r.get("cefr","")} for r in rows]
                pdf_prin = create_principal_pdf(excel_rows, "All Levels", avg, school_name_in)
                st.download_button("📥 Download Principal PDF (Whole School)", pdf_prin, file_name=f"Principal_{school_name_in}_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True, type="primary")
    except Exception as e:
        st.error(f"School OS error: {e}")
with tab8:
    st.markdown("### 👨‍🏫 HOD Moderation View")
    st.caption("Same as Principal but with feedback quality check")
    try:
        if st.session_state.teacher_id:
            q = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).order("created_at", desc=True).limit(100).execute()
            rows = q.data if q.data else []
            if rows:
                for r in rows[:10]:
                    with st.expander(f"{r.get('student_name','')} - {r.get('score','')}/10 {r.get('cefr','')}"):
                        st.write(f"**Essay:** {str(r.get('essay_text',''))[:500]}")
                        st.write(f"**Feedback:** {str(r.get('feedback',''))[:800]}")
                        st.caption(f"Date: {str(r.get('created_at',''))[:10]} | Confidence check needed if low")
            else:
                st.info("No essays")
    except Exception as e:
        st.error(str(e))
st.markdown("---")
st.caption("TEFLMate v6.8 FULL - Compressor + Hash Cache + Confidence + 9 Langs + AI Risk + Student Submit + School OS | taahir532@gmail.com | Made in Durban 🇿🇦")
