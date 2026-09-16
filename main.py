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
import os
import base64
import io
import json
import re
import hashlib
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import requests
from supabase import create_client, Client
from fpdf import FPDF

FREE_LIMIT = 10
st.set_page_config(page_title="TEFLMate v6.91", page_icon="🎓", layout="wide")

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
PAYSTACK_SECRET = st.secrets.get("PAYSTACK_SECRET", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase secrets")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = Groq(api_key=GROQ_API_KEY)

if "user" not in st.session_state: st.session_state.user = None
if "teacher_id" not in st.session_state: st.session_state.teacher_id = None
if "uses" not in st.session_state: st.session_state.uses = 0
if "grade_cache" not in st.session_state: st.session_state.grade_cache = {}
if "batch_results" not in st.session_state: st.session_state.batch_results = []
if "last_ocr" not in st.session_state: st.session_state.last_ocr = ""
if "editable_ocr" not in st.session_state: st.session_state.editable_ocr = ""
if "last_photo_result" not in st.session_state: st.session_state.last_photo_result = ""
if "pay_links" not in st.session_state: st.session_state.pay_links = {}
if "pay_refs" not in st.session_state: st.session_state.pay_refs = {}
if "pay_links_time" not in st.session_state: st.session_state.pay_links_time = None
if "show_admin" not in st.session_state: st.session_state.show_admin = False
if "geo" not in st.session_state:
    st.session_state.geo = {"symbol":"R","weekly":"49","monthly":"99","yearly":"799"}
if "feedback_lang" not in st.session_state: st.session_state.feedback_lang = "English"
if "grading_standard" not in st.session_state: st.session_state.grading_standard = "Cambridge"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
* {font-family: 'Inter', sans-serif!important;}
.stApp {background: #fafafa;}
h1 {font-weight: 800!important; color: #111!important;}
.stButton>button {
    background: #111!important;
    color: white!important;
    border-radius: 12px!important;
    height: 56px!important;
    font-weight: 700!important;
    font-size: 16px!important;
    border: none!important;
}
.stButton>button * {color: white!important; -webkit-text-fill-color: white!important;}
.landing-hero {
    background: linear-gradient(135deg, #111 0%, #333 100%);
    color: white; padding: 40px; border-radius: 20px; margin-bottom: 20px;
}
.landing-hero h1 {color: white!important; font-size: 42px!important;}
</style>
""", unsafe_allow_html=True)

def clean(text):
    if not text: return ""
    return str(text).replace("**","").replace("__","").strip()

def clean_feedback_for_excel(text):
    if not text: return ""
    return re.sub(r'[^\x00-\x7F]+', ' ', str(text))[:500]

def compress_image_bytes(image_bytes, max_size=1024, quality=85):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA","P"): img = img.convert("RGB")
        w,h = img.size
        if max(w,h) > max_size:
            if w>h: new_w, new_h = max_size, int(h * max_size / w)
            else: new_w, new_h = int(w * max_size / h), max_size
            img = img.resize((new_w, new_h), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue()
    except:
        return image_bytes

def create_branded_pdf(essay_text, feedback, level, student_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(17, 24, 39)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_y(7)
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(255,255,255)
    pdf.cell(0, 8, f"TEFLMate v6.91 - {student_name}", align='C', ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Level: {level} | Score Report", align='C', ln=True)
    pdf.ln(12)
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Original Essay:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, clean(essay_text)[:2000])
    pdf.ln(6)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Feedback:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, clean(feedback)[:4000])
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

def create_principal_pdf(excel_rows, level, avg_score, school_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(17, 24, 39)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_y(7)
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(255,255,255)
    pdf.cell(0, 8, f"Principal Report - {school_name}", align='C', ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Level: {level} | Total: {len(excel_rows)} | Avg: {avg_score:.1f}/10", align='C', ln=True)
    pdf.ln(12)
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Class Summary - Average: {avg_score:.1f}/10", ln=True)
    pdf.ln(4)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 7, "Student List:", ln=True)
    pdf.ln(2)
    pdf.set_fill_color(230,230,230)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(70, 8, "Student Name", border=1, fill=True)
    pdf.cell(25, 8, "Score", border=1, fill=True, align='C')
    pdf.cell(25, 8, "CEFR", border=1, fill=True, align='C')
    pdf.cell(70, 8, "Status", border=1, fill=True)
    pdf.ln()
    pdf.set_font("Arial", '', 9)
    for r in excel_rows:
        score = r['Score /10']
        status = "Excellent" if score >= 8 else "Good" if score >= 6 else "Needs Support"
        pdf.cell(70, 7, clean(r['Student Name'])[:35], border=1)
        pdf.cell(25, 7, f"{score}/10", border=1, align='C')
        pdf.cell(25, 7, r['CEFR'], border=1, align='C')
        pdf.cell(70, 7, status, border=1)
        pdf.ln()
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

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
    cached = check_supabase_cache(essay_hash)
    if cached:
        return cached
    if essay_hash in st.session_state.grade_cache:
        return st.session_state.grade_cache[essay_hash]
    try:
        prompt = f"""Grade this {level} essay generously but accurate to {st.session_state.grading_standard} standard. Feedback in {st.session_state.feedback_lang}.
Essay: {essay_text[:2000]}
Return exactly:
OVERALL: X/10
CEFR: Y
CONFIDENCE: high/medium/low
FEEDBACK: detailed feedback
COMMON_MISTAKES: list
"""
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=45)
        if r.status_code!= 200:
            return f"OVERALL: 5/10\nCEFR: {level}\nCONFIDENCE: low\nFEEDBACK: Groq error {r.status_code} - {r.text[:200]}"
        result = r.json()["choices"][0]["message"]["content"]
        st.session_state.grade_cache[essay_hash] = result
        save_supabase_cache(essay_hash, result, level)
        return result
    except Exception as e:
        return f"OVERALL: 5/10\nCEFR: {level}\nCONFIDENCE: low\nFEEDBACK: Error {str(e)}"

def parse_dimensions(raw_text):
    try:
        overall_match = re.search(r'OVERALL:\s*(\d+)', raw_text, re.I)
        overall = int(overall_match.group(1)) if overall_match else 5
        cefr_match = re.search(r'CEFR:\s*([A-C][1-2])', raw_text, re.I)
        cefr = cefr_match.group(1).upper() if cefr_match else "B1"
        conf_match = re.search(r'CONFIDENCE:\s*(high|medium|low)', raw_text, re.I)
        confidence = conf_match.group(1).lower() if conf_match else "medium"
        feedback_match = re.search(r'FEEDBACK:\s*(.*)', raw_text, re.I | re.S)
        feedback_text = feedback_match.group(1).strip() if feedback_match else raw_text
        return {"overall": overall, "cefr": cefr, "confidence": confidence, "feedback_text": feedback_text}
    except:
        return {"overall": 5, "cefr": "B1", "confidence": "low", "feedback_text": raw_text}

def df_to_excel_bytes_safe(df, sheet_name="Sheet1"):
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        return output.getvalue(), "xlsx"
    except:
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        return csv_bytes, "csv"

def extract_text_from_image(image_bytes):
    try:
        compressed = compress_image_bytes(image_bytes)
        b64 = base64.b64encode(compressed).decode('utf-8')
        for model_id in ["qwen/qwen2.5-vl-32b-instruct", "meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct"]:
            try:
                if "qwen" in model_id:
                    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id,
                        "messages": [{"role":"user","content":[
                            {"type":"text","text":"OCR: Extract handwritten text EXACTLY as written, keep spelling mistakes. Return only text."},
                            {"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}
                        ]}],
                        "max_tokens": 2000
                    }
                    r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
                    if r.status_code == 200:
                        return r.json()["choices"][0]["message"]["content"]
                else:
                    res = client.chat.completions.create(model=model_id, messages=[{"role":"user","content":[{"type":"text","text":"OCR: Extract handwritten text EXACTLY as written, keep spelling mistakes. Return only text."},{"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}]}], temperature=0)
                    return res.choices[0].message.content
            except Exception as e:
                continue
        return "OCR_ERROR All models failed"
    except Exception as e:
        return f"OCR_ERROR {str(e)}"

def extract_text_from_pdf(pdf_bytes):
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages[:10]:
            text += page.extract_text() or ""
        return text[:5000] if text.strip() else "OCR_ERROR No text found in PDF"
    except Exception as e:
        return f"OCR_ERROR PDF read failed: {str(e)}"

def is_admin():
    try:
        return st.session_state.user and st.session_state.user.email == "taahir532@gmail.com"
    except:
        return False

def is_pro():
    if is_admin(): return True
    if not st.session_state.user or not st.session_state.teacher_id: return False
    try:
        r = supabase.table("teachers").select("*").eq("id", st.session_state.teacher_id).execute()
        if not r.data: return False
        row = r.data[0]
        if row.get("bonus_grades",0) > 0: return True
        expiry = row.get("pro_expiry")
        if expiry:
            exp_dt = datetime.fromisoformat(expiry.replace("Z","+00:00")).replace(tzinfo=None)
            if exp_dt > datetime.now():
                return True
    except:
        pass
    return False

def get_status():
    if is_admin(): return "👑 ADMIN MODE - Unlimited"
    if is_pro(): return "💎 PRO - Unlimited"
    return f"FREE - {FREE_LIMIT - st.session_state.uses}/{FREE_LIMIT} left"

def save_essay_db(student_name, essay_text, level, score, cefr, feedback):
    try:
        if not st.session_state.teacher_id: return False
        supabase.table("essays").insert({
            "teacher_id": st.session_state.teacher_id,
            "student_name": student_name,
            "essay_text": essay_text,
            "level": level,
            "score": score,
            "cefr": cefr,
            "feedback": feedback
        }).execute()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False

def save_pro_to_db(email, plan, bonus):
    try:
        if plan in ["WEEK49","MONTH99","YEAR799"]:
            days = {"WEEK49":7,"MONTH99":30,"YEAR799":365}[plan]
            expiry = datetime.now() + timedelta(days=days)
            supabase.table("teachers").update({"pro_expiry": expiry.isoformat(), "active_plan": plan}).eq("email", email).execute()
        else:
            supabase.table("teachers").update({"bonus_grades": bonus}).eq("email", email).execute()
        return True
    except Exception as e:
        st.error(f"Pro save error: {e}")
        return False

def init_paystack(email, amount, plan):
    try:
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}", "Content-Type": "application/json"}
        ref = f"TEFL_{plan}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(email.encode()).hexdigest()[:4]}"
        payload = {"email": email, "amount": amount, "reference": ref, "callback_url": "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"}
        r = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"status": False, "message": str(e)}

def verify_all_refs():
    ok = False
    for plan, ref in st.session_state.pay_refs.items():
        try:
            headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
            r = requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers=headers, timeout=30)
            data = r.json()
            if data.get("status") and data["data"]["status"] == "success":
                bonus = 100 if "YEAR" in plan else 30 if "MONTH" in plan else 7 if "WEEK" in plan else 10
                save_pro_to_db(st.session_state.user.email, plan, bonus)
                ok = True
        except:
            pass
    if ok:
        st.session_state.pay_links = {}
        st.session_state.pay_refs = {}
    return ok

q_params = st.query_params
if "ping" in q_params:
    st.write("pong v6.91")
    st.stop()

q_parent = st.query_params
if "parent" in q_parent:
    try:
        pid = q_parent["parent"]
        if isinstance(pid, list): pid = pid[0]
        essay_q = supabase.table("essays").select("*").eq("id", pid).execute()
        if essay_q.data:
            row = essay_q.data[0]
            st.title(f"📄 Parent Report - {row.get('student_name','Student')}")
            st.markdown(f"**Score:** {row.get('score','')}/10 | **CEFR:** {row.get('cefr','')}")
            st.divider()
            st.markdown("### Essay")
            st.write(row.get('essay_text',''))
            st.divider()
            st.markdown("### Teacher Feedback")
            st.markdown(clean(row.get('feedback','')))
            st.stop()
    except Exception as e:
        st.error(f"Parent mode error: {e}")
        st.stop()

q_submit = st.query_params
if "submit" in q_submit:
    try:
        tid = q_submit["submit"]
        if isinstance(tid, list): tid = tid[0]
        st.markdown('<div class="landing-hero"><h1>🎓 TEFLMate - Submit Your Essay</h1></div>', unsafe_allow_html=True)
        s_name_self = st.text_input("Your Full Name:")
        s_level_self = st.selectbox("Your Level:", ["A1","A2","B1","B2","C1","C2"])
        s_essay_self = st.text_area("Paste Your Essay (30+ words):", height=200)
        cam_self = st.camera_input("Or take photo")
        up_self = st.file_uploader("Or upload image", type=["jpg","jpeg","png"], key="self_up")
        img_b_self = None
        if cam_self: img_b_self = cam_self.getvalue()
        elif up_self: img_b_self = up_self.getvalue()
        if img_b_self:
            st.image(img_b_self, use_container_width=True)
            if st.button("📖 Read My Handwriting"):
                txt_self = extract_text_from_image(img_b_self)
                st.session_state.editable_ocr = txt_self
                st.success("Read! Edit below")
        if st.session_state.editable_ocr:
            s_essay_self = st.text_area("Edit OCR:", value=st.session_state.editable_ocr, height=150)
        if st.button("🚀 Submit to Teacher", type="primary", use_container_width=True):
            if not s_name_self or len(s_essay_self.strip())<10:
                st.warning("Name + 10 chars needed")
            else:
                supabase.table("essays").insert({
                    "teacher_id": tid,
                    "student_name": f"{s_name_self} (self)",
                    "essay_text": s_essay_self,
                    "level": s_level_self,
                    "score": 0,
                    "cefr": s_level_self,
                    "feedback": "Self-submitted - awaiting grading"
                }).execute()
                st.success(f"Submitted {s_name_self}!")
                st.balloons()
        st.stop()
    except Exception as e:
        st.error(f"Self-submit error: {e}")
        st.stop()

with st.sidebar:
    st.markdown("### 🎓 TEFLMate v6.91")
    st.caption("Durban 🇿🇦 | Compressor + Hash Cache")
    if st.session_state.user:
        st.write(f"👤 {st.session_state.user.email}")
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.teacher_id = None
            st.rerun()
        try:
            if st.session_state.teacher_id:
                cnt = supabase.table("essays").select("id", count="exact").eq("teacher_id", st.session_state.teacher_id).execute()
                total = cnt.count if cnt.count is not None else 0
                st.metric("Essays Graded", total)
        except:
            pass
        st.divider()
        st.markdown(f"**{get_status()}**")
        if st.session_state.teacher_id:
            base_url = "https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/"
            self_link = f"{base_url}?submit={st.session_state.teacher_id}"
            st.info(f"🔗 Student Self-Submit Link:")
            st.code(self_link)
    else:
        st.markdown("#### 🔑 Login / Sign Up")
        email = st.text_input("Email:")
        password = st.text_input("Password:", type="password")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("Login", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if res.user:
                        st.session_state.user = res.user
                        prof = supabase.table("teachers").select("*").eq("email", email).execute()
                        if prof.data:
                            st.session_state.teacher_id = prof.data[0]["id"]
                            st.session_state.uses = prof.data[0].get("free_uses",0)
                        else:
                            new_t = supabase.table("teachers").insert({"email": email, "free_uses":0}).execute()
                            if new_t.data: st.session_state.teacher_id = new_t.data[0]["id"]
                        st.success("Logged in")
                        st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
        with c2:
            if st.button("Sign Up", use_container_width=True):
                try:
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    if res.user:
                        st.success("Check email to confirm")
                except Exception as e:
                    st.error(str(e))
        st.divider()
        st.markdown("### 💳 Upgrade")
        for plan in ["WEEK49","MONTH99","YEAR799","ONCE10"]:
            amt = {"WEEK49":4900,"MONTH99":9900,"YEAR799":79900,"ONCE10":1000}[plan]
            label = {"WEEK49":"Weekly R49","MONTH99":"Monthly R99","YEAR799":"Yearly R799","ONCE10":"Once R10"}[plan]
            if st.button(f"Pay {label}", key=f"pay_{plan}", use_container_width=True):
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
        for plan, link in st.session_state.pay_links.items():
            st.link_button(f"Pay {plan} via Paystack", link, use_container_width=True)
        if st.session_state.pay_refs:
            if st.button("✅ I've Paid - Verify All", type="primary", use_container_width=True):
                if verify_all_refs():
                    st.success("Unlocked & saved!")
                    st.rerun()
                else:
                    st.warning("Not confirmed yet, try in 30 sec")

if st.session_state.get("show_admin") and is_admin():
    st.title("🛠 Super Admin Dashboard - v6.91")
    try:
        teachers = supabase.table("teachers").select("*").limit(100).execute()
        if teachers.data:
            df_t = pd.DataFrame(teachers.data)
            st.dataframe(df_t, use_container_width=True)
    except Exception as e:
        st.error(str(e))
    if st.button("Close Admin"):
        st.session_state.show_admin = False
        st.rerun()
    st.stop()

st.markdown("---")
status_line = f"**Status:** {get_status()} | **Geo:** {st.session_state.geo['symbol']}{st.session_state.geo['weekly']} | v6.91"
st.caption(status_line)
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["📚 Portfolio","✍ Grade","📸 Photo","📦 Batch 50","📊 Guide","💎 SUPER","🏫 School OS","👨🏫 HOD"])
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
                st.info("No essays yet. Grade in ✍ tab or share student link.")
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
    st.markdown("### ✍ Grade Essay (v6.91 - Compressor + Hash Cache)")
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
            with st.spinner("Compressing + OCR via Qwen 2.5 VL..."):
                txt = extract_text_from_image(img_bytes)
                if "OCR_ERROR" in txt:
                    st.error(txt)
                else:
                    st.session_state.last_ocr = txt
                    st.session_state.editable_ocr = txt
                    st.success("OCR done! Edit below.")
    if st.session_state.editable_ocr:
        edited = st.text_area("✏ Edit OCR text before grading:", value=st.session_state.editable_ocr, height=150, key="grade_edit_ocr_1967")
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
    st.markdown("### 📸 Photo Grade (v6.91)")
    st.caption("Compressed OCR via Qwen2.5-VL-32B + Groq llama-3.1-8b-instant - faster & cheaper")
    s_name_p = st.text_input("Student Name (Photo):", key="photo_name_1967")
    t_level_p = st.selectbox("Level:", ["A1","A2","B1","B2","C1","C2"], key="photo_level_1967", index=2)
    cam_p = st.camera_input("Take photo", key="photo_cam_1967")
    up_p = st.file_uploader("Upload photo", type=["jpg","jpeg","png","pdf"], key="photo_up_1967")
    ib = None
    if cam_p: ib = cam_p.getvalue()
    elif up_p: ib = up_p.getvalue()
    if ib:
        if up_p and up_p.type == "application/pdf":
            with st.spinner("PDF..."):
                txt = extract_text_from_pdf(ib)
                st.session_state.last_photo_result = txt
                st.text_area("PDF Extracted:", value=txt[:2000], height=150)
        else:
            st.image(ib, use_container_width=True)
            if st.button("📖 Read This Photo (Compressor)", key="photo_read_1967", use_container_width=True):
                with st.spinner("Compressing to 1024px + OCR Qwen2.5-VL..."):
                    txt = extract_text_from_image(ib)
                    if "OCR_ERROR" in txt: st.error(txt)
                    else:
                        st.session_state.last_photo_result = txt
                        st.session_state.editable_ocr = txt
                        st.success("OCR done! Edit & grade below")
        if st.session_state.last_photo_result:
            editable_p = st.text_area("Edit Photo OCR:", value=st.session_state.last_photo_result, height=150, key="photo_edit_1967")
            if st.button("🚀 Grade Photo Essay", type="primary", use_container_width=True, key="photo_grade_1967"):
                if not is_pro() and st.session_state.uses >= FREE_LIMIT:
                    st.error("Free limit reached")
                else:
                    with st.spinner("Grading..."):
                        raw = grade_with_groq(editable_p, t_level_p)
                        parsed = parse_dimensions(raw)
                        score = parsed.get("overall",5); cefr = parsed.get("cefr",t_level_p)
                        ai_risk = detect_ai_risk(editable_p)
                        if s_name_p:
                            save_essay_db(s_name_p, editable_p, t_level_p, score, cefr, raw)
                        st.success(f"Score {score}/10 | {cefr} | {ai_risk}")
                        st.markdown(clean(raw))
                        pdf_b = create_branded_pdf(editable_p, raw, t_level_p, s_name_p or "Photo")
                        st.download_button("📥 PDF", pdf_b, f"{s_name_p or 'Photo'}_{score}.pdf", use_container_width=True, key="photo_pdf_1967")
with tab4:
    st.markdown("### 📦 Batch 50 (v6.91 - Stable)")
    st.caption("Upload up to 50 essays - compressor + cache prevents crash")
    t_level_b = st.selectbox("Batch Level:", ["A1","A2","B1","B2","C1","C2"], index=2, key="batch_level_1967")
    batch_files = st.file_uploader("Upload images (multiple)", type=["jpg","jpeg","png"], accept_multiple_files=True, key="batch_files_1967")
    batch_texts = st.text_area("Or paste multiple essays separated by ---", height=150, key="batch_texts_1967", placeholder="Essay1 text\n---\nEssay2 text")
    if st.button("🚀 Grade Batch (Max 50)", type="primary", use_container_width=True, key="batch_go_1967"):
        items = []
        if batch_files:
            for f in batch_files[:50]:
                items.append(("file", f.name, f.getvalue()))
        if batch_texts and "---" in batch_texts:
            for idx, t in enumerate(batch_texts.split("---")):
                if t.strip(): items.append(("text", f"Essay_{idx+1}", t.strip()))
        if not items:
            st.warning("Upload files or paste essays with --- separator")
        elif not is_pro() and (st.session_state.uses + len(items) > FREE_LIMIT):
            st.error(f"Need {len(items)} grades but you have {FREE_LIMIT - st.session_state.uses} left. Upgrade.")
        else:
            results = []
            prog = st.progress(0)
            for i, (typ, name, data) in enumerate(items[:50]):
                essay_txt = data if typ=="text" else extract_text_from_image(data)
                if "OCR_ERROR" in essay_txt:
                    results.append({"Student Name": name, "Score /10": 0, "CEFR": t_level_b, "Feedback Preview": essay_txt[:200], "AI Risk": "Error"})
                    continue
                raw = grade_with_groq(essay_txt, t_level_b)
                parsed = parse_dimensions(raw)
                score = parsed.get("overall",5); cefr = parsed.get("cefr",t_level_b)
                ai_risk = detect_ai_risk(essay_txt)
                results.append({"Student Name": name, "Level": t_level_b, "Score /10": score, "CEFR": cefr, "AI Risk": ai_risk, "Feedback Preview": clean_feedback_for_excel(raw[:300]), "Full Essay": essay_txt[:1000]})
                save_essay_db(name, essay_txt, t_level_b, score, cefr, raw)
                st.session_state.uses += 1
                prog.progress((i+1)/len(items))
            st.session_state.batch_results = results
            st.success(f"Graded {len(results)} essays")
            if results:
                df_b = pd.DataFrame(results)
                st.dataframe(df_b, use_container_width=True)
                xb, ext = df_to_excel_bytes_safe(df_b, "Batch")
                st.download_button(f"📥 Download Batch Excel.{ext}", xb, file_name=f"TEFLMate_Batch_{datetime.now().strftime('%Y%m%d')}.{ext}", use_container_width=True)
                pdf_principal = create_principal_pdf(results, t_level_b, sum(r["Score /10"] for r in results)/len(results) if results else 0, "School Batch")
                st.download_button("📄 Download Principal PDF (Batch)", pdf_principal, file_name=f"Principal_Batch_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)
with tab5:
    st.markdown("### 📊 Guide")
    st.markdown("""
    **How TEFLMate Works:**
    1. Grade in ✍ or 📸 - Auto-saves to Portfolio
    2. Share student link - Self-submit goes to your Portfolio
    3. Batch 50 - Grade whole class at once
    4. Parent Reports - Each essay gets?parent= link
    """)
    st.divider()
    st.markdown("#### 📈 Earnings Simulator")
    studs = st.slider("How many students you have?", 10, 500, 50)
    price_per = st.number_input("Price you charge per student per month (R):", value=int(st.session_state.geo["monthly"]), step=10)
    earn = studs * price_per
    st.metric("Monthly Earning Potential", f"R{earn:,}")
    st.divider()
    st.markdown("#### 🎯 Grading Generosity (v6.91 fix)")
    st.markdown("""
    - **A1/A2:** 30+ words communicating idea = 6/10 minimum (not 4)
    - **A1/A2:** Good clear A2 = 7-8/10
    - **A1:** <15 words = 4-5/10
    - **B1+:** Cambridge strict, detailed feedback
    """)
with tab6:
    st.markdown("### 💎 SUPER - Full Feature Comparison")
    st.markdown("""
    | Feature | FREE (10) | PRO |
    |---------|-----------|-----|
    | Essay Grading | 10 | Unlimited |
    | Photo OCR (Compressed) | 10 | Unlimited |
    | Batch 50 | ❌ | ✅ |
    | Portfolio Excel + Principal PDF | ✅ | ✅ |
    | Parent Links | ✅ | ✅ |
    | Student Self-Submit | ✅ | ✅ |
    | AI Risk Detection | ✅ | ✅ |
    | Hash Cache (no re-grade cost) | ✅ | ✅ |
    """)
    st.divider()
    if is_pro() or is_admin():
        st.success("You are PRO - all features unlocked")
    else:
        st.warning("Upgrade in sidebar for Unlimited")
with tab7:
    st.markdown("### 🏫 School OS (v6.91)")
    st.caption("For principals & schools - whole class analytics")
    try:
        if st.session_state.teacher_id:
            q = supabase.table("essays").select("*").eq("teacher_id", st.session_state.teacher_id).limit(200).execute()
            rows = q.data if q.data else []
            if not rows:
                st.info("No data yet for School OS")
            else:
                levels = {}
                for r in rows:
                    lvl = r.get("level","B1")
                    levels[lvl] = levels.get(lvl,0)+1
                c1,c2 = st.columns(2)
                with c1:
                    st.metric("Total Students", len(rows))
                    st.metric("Avg Score", f"{sum(r.get('score',0) for r in rows)/len(rows):.1f}/10" if rows else "0")
                with c2:
                    fig2, ax2 = plt.subplots()
                    ax2.bar(levels.keys(), levels.values())
                    ax2.set_title("Essays by Level")
                    st.pyplot(fig2)
                st.divider()
                if st.button("📄 Generate Principal PDF (School OS)", use_container_width=True):
                    avg_s = sum(r.get('score',0) for r in rows)/len(rows) if rows else 0
                    df_rows = [{"Student Name": r.get("student_name",""), "Score /10": r.get("score",0), "CEFR": r.get("cefr","")} for r in rows]
                    pdf_school = create_principal_pdf(df_rows, "All Levels", avg_s, "My School")
                    st.download_button("Download Principal Report", pdf_school, file_name=f"SchoolOS_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)
    except Exception as e:
        st.error(f"School OS error: {e}")
with tab8:
    st.markdown("### 👨🏫 HOD Dashboard (v6.91)")
    st.caption("Head of Department - teacher oversight")
    if not is_admin() and not is_pro():
        st.warning("HOD is PRO feature. Upgrade to view.")
    else:
        try:
            teachers_q = supabase.table("teachers").select("*").limit(50).execute()
            if teachers_q.data:
                st.write(f"Total teachers in system: {len(teachers_q.data)}")
                df_hod = pd.DataFrame([{"Email": t.get("email",""), "Free Uses": t.get("free_uses",0), "Bonus": t.get("bonus_grades",0), "Plan": t.get("active_plan",""), "Expiry": str(t.get("pro_expiry",""))[:10]} for t in teachers_q.data])
                st.dataframe(df_hod, use_container_width=True)
            essays_q = supabase.table("essays").select("id", count="exact").execute()
            total_essays = essays_q.count if essays_q.count is not None else 0
            st.metric("Total Essays Graded System-wide", total_essays)
            if is_admin():
                st.divider()
                st.markdown("#### Admin: Clear Grade Cache")
                if st.button("Clear All Cache (grade_cache table)"):
                    try:
                        supabase.table("grade_cache").delete().neq("hash","xxx").execute()
                        st.success("Cache cleared")
                    except Exception as e:
                        st.error(str(e))
        except Exception as e:
            st.error(f"HOD error: {e}")

st.markdown("---")
st.caption("© 2026 TEFLMate | Made in Durban, ZA | v6.91 FULL - Compressor + Hash Cache + Confidence + 9 Langs + AI Risk + Student Submit + School OS | taahir532@gmail.com")
