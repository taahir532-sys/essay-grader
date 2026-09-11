import streamlit as st, streamlit.components.v1 as components
from groq import Groq
from datetime import datetime, timedelta
from fpdf import FPDF
import unicodedata, pandas as pd, base64, requests
try: import fitz
except: fitz=None
YOUR_EMAIL="taahir532@gmail.com"
PAYPAL_ME="https://paypal.me/TaahirMahomed"
st.set_page_config(page_title="TEFLMate v5.3 Auto", page_icon="📝", layout="centered")
st.markdown("""<style>.stButton>button{background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;}</style>""", unsafe_allow_html=True)
if "uses" not in st.session_state: st.session_state.uses=0
if "pro_expiry" not in st.session_state: st.session_state.pro_expiry=None
if "geo" not in st.session_state:
    try: country=requests.get("https://ipapi.co/json/", timeout=3).json().get("country_code","ZA")
    except: country="ZA"
    if country=="ZA": st.session_state.geo={"symbol":"R","weekly":"49","monthly":"99","yearly":"799","once":"10","code":"ZAR"}
    elif country=="GB": st.session_state.geo={"symbol":"£","weekly":"3.99","monthly":"6.99","yearly":"55","once":"0.99","code":"GBP"}
    elif country in ["DE","FR","NL","IT","ES","PT","IE"]: st.session_state.geo={"symbol":"€","weekly":"4.99","monthly":"8.50","yearly":"65","once":"0.99","code":"EUR"}
    else: st.session_state.geo={"symbol":"$","weekly":"4.99","monthly":"8.50","yearly":"65","once":"0.99","code":"USD"}

def is_pro(): return st.session_state.pro_expiry is not None and datetime.now() < st.session_state.pro_expiry
def get_status():
    if is_pro(): return f"PRO ACTIVE - {(st.session_state.pro_expiry-datetime.now()).days+1} days left"
    else: return f"FREE - {3-st.session_state.uses} left"
def clean(t): return unicodedata.normalize('NFKD', t or "").encode('ascii','ignore').decode('ascii')

def verify_paystack(ref):
    try:
        secret=st.secrets["PAYSTACK_SECRET_KEY"]
        r=requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers={"Authorization": f"Bearer {secret}"}, timeout=10)
        return r.json()
    except Exception as e: return {"status":False,"message":str(e)}

def unlock_from_verify(v):
    if not v.get("status"): return False
    d=v.get("data",{})
    if d.get("status")!="success": return False
    amt=d.get("amount",0); plan=d.get("metadata",{}).get("plan",""); now=datetime.now()
    if amt==1000 or plan=="ONCE10": st.session_state.uses=max(0,st.session_state.uses-10); st.success("R10 received! +10 grades ✅"); st.balloons(); return True
    elif amt==4900 or plan=="WEEK49": st.session_state.pro_expiry=now+timedelta(days=7); st.success("R49 Weekly PRO - 7 days ✅"); st.balloons(); return True
    elif amt==9900 or plan=="MONTH99": st.session_state.pro_expiry=now+timedelta(days=30); st.success("R99 Monthly PRO - 30 days + Batch 50 ✅"); st.balloons(); return True
    elif amt==79900 or plan=="YEAR799": st.session_state.pro_expiry=now+timedelta(days=365); st.success("R799 Yearly PRO - 365 days ✅"); st.balloons(); return True
    return False

# Check for auto-verify from inline popup
q=st.query_params
if "reference" in q:
    if unlock_from_verify(verify_paystack(q["reference"])): st.query_params.clear()

def paystack_inline_button(email, amount_kobo, plan_code, label):
    public_key = st.secrets.get("PAYSTACK_PUBLIC_KEY", "")
    # If you only have secret key, derive public from dashboard - ask user to add it
    # For now we use secret to init and get public from secrets
    # We need PUBLIC key for inline - add PAYSTACK_PUBLIC_KEY to secrets
    ref = f"TEFL_{plan_code}_{int(datetime.now().timestamp())}"
    html = f"""
    <script src="https://js.paystack.co/v1/inline.js"></script>
    <button style="background:#111;color:white;border-radius:10px;height:45px;font-weight:bold;width:100%;border:none;cursor:pointer;">{label}</button>
    <script>
    document.currentScript.previousElementSibling.onclick = function(){{
        var handler = PaystackPop.setup({{
            key: '{public_key}',
            email: '{email}',
            amount: {amount_kobo},
            currency: 'ZAR',
            ref: '{ref}',
            metadata: {{plan:'{plan_code}'}},
            callback: function(response){{
                window.location.href = window.location.origin + window.location.pathname + '?reference=' + response.reference;
            }},
            onClose: function(){{}}
        }});
        handler.openIframe();
    }}
    </script>
    """
    components.html(html, height=60)

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

def create_branded_pdf(orig, ai_res, lvl):
    pdf=FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    pdf.set_fill_color(17,24,39); pdf.rect(0,0,210,32,'F'); pdf.set_y(7)
    pdf.set_font("Arial",'B',14); pdf.set_text_color(255,255,255); pdf.cell(0,8,"Mr Mahomed | Essay Grader Report",align='C',ln=True); pdf.ln(10)
    pdf.set_text_color(0,0,0); pdf.set_font("Arial",'B',11); pdf.cell(0,7,f"Target Level: {lvl} | Date: {datetime.now().strftime('%d %b %Y')}",ln=True); pdf.ln(2)
    pdf.set_font("Arial",'',10); pdf.multi_cell(0,6,clean(ai_res))
    return pdf.output(dest='S').encode('latin-1')

def grade_with_groq(essay, lvl):
    client=Groq(api_key=st.secrets["GROQ_API_KEY"])
    prompt=f"You are Cambridge TEFL examiner for {lvl}. Grade: {essay}. ASCII only. Include CEFR Level, Score/10 vs Target {lvl}, Summary, 2 Strengths, Table Mistake|Correction|Why, Then corrected version."
    return client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}]).choices[0].message.content

st.title("📝 TEFLMate v5.3 - Batch Grader")
st.caption(f"Auto-unlock • Pricing in {st.session_state.geo['code']}")
with st.sidebar:
    st.markdown("### 🔑 Your Plan"); st.info(get_status()); g=st.session_state.geo
    st.markdown(f"**Pricing ({g['code']})**\n- FREE: 3\n- Once {g['symbol']}{g['once']}=+10\n- Weekly {g['symbol']}{g['weekly']}\n- Monthly {g['symbol']}{g['monthly']}=Batch 50\n- Yearly {g['symbol']}{g['yearly']}")
    st.divider()
    if g['code']=="ZAR":
        st.markdown("#### 🇿🇦 Instant Card/EFT (Auto)")
        email=st.text_input("Email for receipt:", value=YOUR_EMAIL, key="pay_email")
        # IMPORTANT: Add your Paystack PUBLIC key to Streamlit Secrets as PAYSTACK_PUBLIC_KEY
        if "PAYSTACK_PUBLIC_KEY" not in st.secrets:
            st.warning("Add PAYSTACK_PUBLIC_KEY to Secrets (pk_...) for auto popup")
            st.markdown("Go to Paystack Dashboard → Settings → API Keys → Copy PUBLIC key")
        else:
            c1,c2=st.columns(2)
            with c1:
                paystack_inline_button(email,1000,"ONCE10",f"Once R{g['once']}")
                st.write("")
                paystack_inline_button(email,9900,"MONTH99",f"Monthly R{g['monthly']} ⭐")
            with c2:
                paystack_inline_button(email,4900,"WEEK49",f"Weekly R{g['weekly']}")
                st.write("")
                paystack_inline_button(email,79900,"YEAR799",f"Yearly R{g['yearly']}")
        st.caption("Popup opens here → Pay → Auto unlocks, no redirect")
        st.divider()
    st.link_button("💳 PayPal", PAYPAL_ME)
    st.divider()
    code=st.text_input("Got a code?", placeholder="Paste code", type="password").strip().upper()
    if st.button("Unlock Code"):
        now=datetime.now()
        mp={"TEACH10":lambda:setattr(st.session_state,'uses',max(0,st.session_state.uses-10)),"WEEK49":lambda:setattr(st.session_state,'pro_expiry',now+timedelta(days=7)),"MONTH99":lambda:setattr(st.session_state,'pro_expiry',now+timedelta(days=30)),"YEAR799":lambda:setattr(st.session_state,'pro_expiry',now+timedelta(days=365)),"TEFL2026":lambda:setattr(st.session_state,'pro_expiry',now+timedelta(days=30))}
        if code in mp: mp[code](); st.success("Unlocked!"); st.rerun()
        else: st.error("Bad code")

tab1,tab2,tab3,tab4=st.tabs(["Single","Batch 50 (PRO)","📸 Photo/PDF","📘 Guide"])
with tab1:
    essay=st.text_area("Paste Essay:",height=180,placeholder="I broken my leg")
    lvl=st.selectbox("Target:",["A1","A2","B1","B2","C1","C2"],key="single")
    if st.button("GRADE ESSAY ->"):
        if not is_pro() and st.session_state.uses>=3: st.error("Free limit - pay in sidebar"); st.stop()
        with st.spinner("Grading..."): res=grade_with_groq(essay,lvl);
        if not is_pro(): st.session_state.uses+=1
        st.markdown(res); st.download_button("📄 PDF",create_branded_pdf(essay,res,lvl),file_name=f"Report_{lvl}.pdf")
with tab2:
    st.markdown("### Upload 50 At Once"); st.info(f"Monthly {g['symbol']}{g['monthly']} unlocks")
    df=pd.DataFrame({"student_name":["S1","S2"],"essay":["I go yesterday.","My friend is Thandi."]})
    st.download_button("📥 Template",df.to_csv(index=False).encode('utf-8'),"Template.csv","text/csv")
    lvl2=st.selectbox("Level:",["A1","A2","B1","B2","C1","C2"],key="batch")
    up=st.file_uploader("Upload CSV/TXT",type=["csv","txt"])
    if st.button("GRADE BATCH 50 ->"):
        if not is_pro(): st.error("Needs Monthly PRO"); st.stop()
        if not up: st.warning("Upload first"); st.stop()
        ess=[]
        if up.name.endswith(".csv"):
            d=pd.read_csv(up); col="essay" if "essay" in d.columns else d.columns[0]; ess=d[col].dropna().astype(str).tolist()[:50]
        else: ess=[e.strip() for e in up.read().decode("utf-8",errors="ignore").split("\n") if e.strip()][:50]
        st.info(f"Grading {len(ess)}..."); results=[]; prog=st.progress(0)
        for i,e in enumerate(ess): results.append({"Essay":e[:100],"Result":grade_with_groq(e[:2000],lvl2)}); prog.progress((i+1)/len(ess))
        st.success("Done!"); st.dataframe(pd.DataFrame(results))
        pdf=FPDF(); pdf.set_auto_page_break(auto=True,margin=15)
        for idx,r in enumerate(results): pdf.add_page(); pdf.set_font("Arial",'B',12); pdf.cell(0,10,f"Essay {idx+1}",ln=True); pdf.set_font("Arial",'',10); pdf.multi_cell(0,6,clean(r["Result"]))
        st.download_button("📄 Download All 50 PDF",pdf.output(dest='S').encode('latin-1'),"Batch_50.pdf")
with tab3:
    st.markdown("### 📸 Photo / PDF"); lvl3=st.selectbox("Level:",["A1","A2","B1","B2","C1","C2"],key="photo")
    cA,cB=st.columns(2)
    with cA: cam=st.camera_input("Take photo"); upI=st.file_uploader("Upload Image",type=["jpg","jpeg","png"],key="img")
    with cB: upP=st.file_uploader("Upload PDF",type=["pdf"],key="pdf")
    ib=None
    if cam: ib=cam.getvalue()
    elif upI: ib=upI.getvalue()
    if ib: st.image(ib,use_container_width=True)
    if upP:
        ext=extract_text_from_pdf(upP.getvalue()); st.text_area("From PDF:",value=ext,height=150,key="pdf_area")
        if st.button("GRADE PDF TEXT ->"): r=grade_with_groq(ext,lvl3); st.markdown(r); st.download_button("📄 PDF",create_branded_pdf(ext,r,lvl3),f"PDF_{lvl3}.pdf")
    if ib and st.button("READ & GRADE PHOTO ->"):
        with st.spinner("Reading..."): ext=extract_text_from_image(ib)
        if "OCR_ERROR" in ext: st.error(ext)
        else: st.session_state['last_ocr']=ext; st.rerun()
    if 'last_ocr' in st.session_state:
        ed=st.text_area("We read — edit:",value=st.session_state['last_ocr'],height=150)
        if st.button("GRADE THIS TEXT ->"): r=grade_with_groq(ed,lvl3); st.markdown(r); st.download_button("📄 PDF",create_branded_pdf(ed,r,lvl3),f"Photo_{lvl3}.pdf")
with tab4:
    st.table(pd.DataFrame([{"Level":"A1","Class":"Gr1-3","Use":"ABET"},{"Level":"A2","Class":"Gr4-6","Use":"Primary"},{"Level":"B1","Class":"Gr7-9","Use":"High"},{"Level":"B2","Class":"Matric","Use":"Matric"},{"Level":"C1","Class":"Uni","Use":"Uni/Work"},{"Level":"C2","Class":"Mastery","Use":"Teachers"}]))
