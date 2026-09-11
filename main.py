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
st.set_page_config(page_title="TEFLMate v5.5.2 Fixed", page_icon="📝", layout="centered")
st.markdown("""<style>.stButton>button {background:#111;color:white;border-radius:12px;height:52px;font-weight:bold;width:100%;font-size:15px;} div[data-testid="stLinkButton"]>a{background:#111!important;color:white!important;border-radius:12px!important;height:52px!important;font-weight:bold!important;width:100%!important;display:flex!important;align-items:center!important;justify-content:center!important;font-size:14px!important;}</style>""", unsafe_allow_html=True)

if "uses" not in st.session_state: st.session_state.uses = 0
if "pro_expiry" not in st.session_state: st.session_state.pro_expiry = None
if "pay_links" not in st.session_state: st.session_state.pay_links = {}
if "pay_refs" not in st.session_state: st.session_state.pay_refs = {}
if "last_ref" not in st.session_state: st.session_state.last_ref = None
if "geo" not in st.session_state:
    try: country = requests.get("https://ipapi.co/json/", timeout=3).json().get("country_code","ZA")
    except: country="ZA"
    if country=="ZA": st.session_state.geo={"symbol":"R","weekly":"49","monthly":"99","yearly":"799","once":"10","code":"ZAR"}
    else: st.session_state.geo={"symbol":"$","weekly":"4.99","monthly":"8.50","yearly":"65","once":"0.99","code":"USD"}

def is_pro(): return st.session_state.pro_expiry is not None and datetime.now() < st.session_state.pro_expiry
def get_status():
    if is_pro(): return f"PRO ACTIVE - {(st.session_state.pro_expiry-datetime.now()).days+1} days left"
    else: return f"FREE - {3-st.session_state.uses} left"
def clean(t): return unicodedata.normalize('NFKD', t or "").encode('ascii','ignore').decode('ascii')

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

def unlock(v):
    if not v.get("status"): return False
    d=v.get("data",{})
    if d.get("status")!="success": return False
    amt=d.get("amount",0); plan=d.get("metadata",{}).get("plan",""); now=datetime.now()
    if amt==1000 or plan=="ONCE10": st.session_state.uses=max(0,st.session_state.uses-10); st.session_state.last_ref=None; st.success("R10 received! +10 grades added ✅"); st.balloons(); return True
    elif amt==4900 or plan=="WEEK49": st.session_state.pro_expiry=now+timedelta(days=7); st.session_state.last_ref=None; st.success("R49 Weekly PRO - 7 days + Batch 50 ✅"); st.balloons(); return True
    elif amt==9900 or plan=="MONTH99": st.session_state.pro_expiry=now+timedelta(days=30); st.session_state.last_ref=None; st.success("R99 Monthly PRO - 30 days + Batch 50 ✅"); st.balloons(); return True
    elif amt==79900 or plan=="YEAR799": st.session_state.pro_expiry=now+timedelta(days=365); st.session_state.last_ref=None; st.success("R799 Yearly PRO - 365 days + Batch 50 ✅"); st.balloons(); return True
    return False

q=st.query_params
if "reference" in q:
    if unlock(verify_paystack(q["reference"])): st.query_params.clear()

def grade_with_groq(essay, lvl):
    client=Groq(api_key=st.secrets["GROQ_API_KEY"])
    return client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":f"You are Cambridge TEFL examiner for {lvl}. Grade: {essay}. ASCII only. Include CEFR Level, Score/10 vs Target {lvl}, Summary, 2 Strengths, Table Mistake|Correction|Why, Then corrected version."}]).choices[0].message.content

def create_branded_pdf(orig, ai_res, lvl):
    pdf=FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    pdf.set_fill_color(17,24,39); pdf.rect(0,0,210,32,'F'); pdf.set_y(7)
    pdf.set_font("Arial",'B',14); pdf.set_text_color(255,255,255); pdf.cell(0,8,"Mr Mahomed | Essay Grader Report",align='C',ln=True); pdf.ln(10)
    pdf.set_text_color(0,0,0); pdf.set_font("Arial",'B',11); pdf.cell(0,7,f"Target Level: {lvl} | Date: {datetime.now().strftime('%d %b %Y')}",ln=True); pdf.ln(2)
    pdf.set_font("Arial",'',10); pdf.multi_cell(0,6,clean(ai_res))
    return pdf.output(dest='S').encode('latin-1')

def extract_text_from_image(b):
    client=Groq(api_key=st.secrets["GROQ_API_KEY"]); b64=base64.b64encode(b).decode('utf-8')
    try:
        res=client.chat.completions.create(model="qwen/qwen3-32b", messages=[{"role":"user","content":[{"type":"text","text":"OCR: Extract handwritten text EXACTLY as written, keep mistakes. Return only text."},{"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}]}])
        txt=res.choices[0].message.content
        if "</think>" in txt: txt=txt.split("</think>")[-1].strip()
        return txt.strip()
    except Exception as e: return f"OCR_ERROR: {e}"

def extract_text_from_pdf(b):
    if not fitz: return "Add PyMuPDF"
    try:
        doc=fitz.open(stream=b, filetype="pdf"); t="\n".join([p.get_text() for p in doc[:3]])
        if len(t.strip())<30 and len(doc)>0:
            pix=doc[0].get_pixmap(dpi=200); t=extract_text_from_image(pix.tobytes("jpeg"))
        return t
    except Exception as e: return f"PDF_ERROR: {e}"

# SIDEBAR - NO LOOP
with st.sidebar:
    st.markdown("### 🔑 Your Plan"); st.info(get_status()); g=st.session_state.geo
    if g['code']=="ZAR":
        st.markdown("#### 🇿🇦 Choose Your Plan")
        st.caption("1 click → Pay on Paystack → Return here → Click Unlock")
        email = st.text_input("Email for receipt:", value=YOUR_EMAIL, key="pay_email")

        # Create links once
        if not st.session_state.pay_links and email:
            with st.spinner("Loading pay options..."):
                for plan, amt in [("ONCE10",1000),("WEEK49",4900),("MONTH99",9900),("YEAR799",79900)]:
                    res = init_paystack(email, amt, plan)
                    if res.get("status"):
                        st.session_state.pay_links[plan] = res["data"]["authorization_url"]
                        st.session_state.pay_refs[plan] = res["data"]["reference"]

        if st.session_state.pay_links:
            if "ONCE10" in st.session_state.pay_links:
                st.link_button("💳 Pay Once R10 - +10 grades (No Batch)", st.session_state.pay_links["ONCE10"], use_container_width=True)
            if "WEEK49" in st.session_state.pay_links:
                st.link_button("💳 Pay Weekly R49 - 7 days + Batch 50", st.session_state.pay_links["WEEK49"], use_container_width=True)
            if "MONTH99" in st.session_state.pay_links:
                st.link_button("⭐ Pay Monthly R99 - 30 days + Batch 50", st.session_state.pay_links["MONTH99"], use_container_width=True)
            if "YEAR799" in st.session_state.pay_links:
                st.link_button("💳 Pay Yearly R799 - 365 days + Batch 50", st.session_state.pay_links["YEAR799"], use_container_width=True)

            # Save last ref based on which link was last generated - user will paste or we use latest
            # Simplified: store all refs, verify button checks latest
            if st.session_state.pay_refs:
                st.session_state.last_ref = list(st.session_state.pay_refs.values())[-1]

            st.write("")
            # MANUAL VERIFY - NO AUTO LOOP, so page never goes blank
            st.markdown("---")
            st.markdown("**After paying on Paystack:**")
            if st.button("✅ I PAID - Click to Unlock PRO", type="primary", use_container_width=True):
                if st.session_state.last_ref:
                    v = verify_paystack(st.session_state.last_ref)
                    if unlock(v):
                        st.rerun()
                    else:
                        st.warning("Not confirmed yet. Wait 10 sec after Paystack Success, then click again.")
                        # Optional: allow pasting ref
                        with st.expander("Paste Paystack Reference"):
                            ref_input = st.text_input("Reference (e.g. T...)", key="ref_manual")
                            if st.button("Verify Reference"):
                                if unlock(verify_paystack(ref_input.strip())):
                                    st.rerun()
                else:
                    st.warning("No payment found. Click a Pay button first.")

        if st.button("🔄 Refresh Pay Links"):
            st.session_state.pay_links = {}
            st.session_state.pay_refs = {}
            st.session_state.last_ref = None
            st.rerun()
        st.divider()
    st.link_button("🌍 PayPal", PAYPAL_ME)
    st.divider()
    code=st.text_input("Got a code?", type="password").strip().upper()
    if st.button("Unlock Code"):
        now=datetime.now()
        m={"TEACH10":lambda:setattr(st.session_state,'uses',max(0,st.session_state.uses-10)),"WEEK49":lambda:setattr(st.session_state,'pro_expiry',now+timedelta(days=7)),"MONTH99":lambda:setattr(st.session_state,'pro_expiry',now+timedelta(days=30)),"YEAR799":lambda:setattr(st.session_state,'pro_expiry',now+timedelta(days=365)),"TEFL2026":lambda:setattr(st.session_state,'pro_expiry',now+timedelta(days=30))}
        if code in m: m[code](); st.success("Unlocked!"); st.rerun()
        else: st.error("Bad code")

# MAIN PAGE - WILL ALWAYS SHOW NOW
st.title("📝 TEFLMate v5.5.2")
st.caption("One click to pay - auto unlocks")

tab1,tab2,tab3,tab4=st.tabs(["Single Essay","Batch 50 (PRO)","📸 Photo/PDF","📘 Guide"])
with tab1:
    essay=st.text_area("Paste Essay:",height=180,placeholder="I broken my leg")
    lvl=st.selectbox("Target:",["A1","A2","B1","B2","C1","C2"],key="single")
    if st.button("GRADE ESSAY ->"):
        if not is_pro() and st.session_state.uses>=3: st.error("Free limit - pay in sidebar"); st.stop()
        with st.spinner("Grading..."): res=grade_with_groq(essay,lvl)
        if not is_pro(): st.session_state.uses+=1
        st.markdown(res); st.download_button("📄 PDF",create_branded_pdf(essay,res,lvl),f"Report_{lvl}.pdf")
with tab2:
    st.markdown("### Upload 50 At Once")
    st.info("✅ Any PRO plan (Weekly / Monthly / Yearly) unlocks Batch 50 • Once R10 is single grades only")
    df=pd.DataFrame({"student_name":["S1","S2"],"essay":["I go yesterday.","My friend is Thandi."]})
    st.download_button("📥 Template",df.to_csv(index=False).encode('utf-8'),"Template.csv","text/csv")
    lvl2=st.selectbox("Level:",["A1","A2","B1","B2","C1","C2"],key="batch")
    up=st.file_uploader("Upload CSV/TXT",type=["csv","txt"])
    if st.button("GRADE BATCH 50 ->"):
        if not is_pro(): st.error("Batch 50 needs any PRO plan (Weekly/Monthly/Yearly)"); st.stop()
        if not up: st.warning("Upload first"); st.stop()
        ess=[]
        if up.name.endswith(".csv"):
            d=pd.read_csv(up); col="essay" if "essay" in d.columns else d.columns[0]; ess=d[col].dropna().astype(str).tolist()[:50]
        else: ess=[e.strip() for e in up.read().decode("utf-8",errors="ignore").split("\n") if e.strip()][:50]
        st.info(f"Grading {len(ess)}..."); results=[]; prog=st.progress(0)
        for i,e in enumerate(ess): results.append({"Essay":e[:100],"Result":grade_with_groq(e[:2000],lvl2)}); prog.progress((i+1)/len(ess))
        st.success("Done!"); st.dataframe(pd.DataFrame(results))
with tab3:
    st.markdown("### 📸 Photo / PDF"); lvl3=st.selectbox("Level:",["A1","A2","B1","B2","C1","C2"],key="photo")
    cam=st.camera_input("Take photo"); upI=st.file_uploader("Upload Image",type=["jpg","jpeg","png"],key="img"); upP=st.file_uploader("Upload PDF",type=["pdf"],key="pdf")
    ib=None
    if cam: ib=cam.getvalue()
    elif upI: ib=upI.getvalue()
    if ib: st.image(ib,use_container_width=True)
    if upP:
        ext=extract_text_from_pdf(upP.getvalue()); st.text_area("From PDF:",value=ext,height=150,key="pdf_area")
        if st.button("GRADE PDF TEXT ->"): r=grade_with_groq(ext,lvl3); st.markdown(r)
    if ib and st.button("READ & GRADE PHOTO ->"):
        with st.spinner("Reading..."): ext=extract_text_from_image(ib)
        if "OCR_ERROR" in ext: st.error(ext)
        else: st.session_state['last_ocr']=ext; st.rerun()
    if 'last_ocr' in st.session_state:
        ed=st.text_area("We read — edit:",value=st.session_state['last_ocr'],height=150)
        if st.button("GRADE THIS TEXT ->"): r=grade_with_groq(ed,lvl3); st.markdown(r)
with tab4:
    st.table(pd.DataFrame([{"Level":"A1","Use":"Gr1-3 ABET"},{"Level":"A2","Use":"Gr4-6 Primary"},{"Level":"B1","Use":"Gr7-9 High"},{"Level":"B2","Use":"Matric"},{"Level":"C1","Use":"Uni"},{"Level":"C2","Use":"Teachers"}]))
