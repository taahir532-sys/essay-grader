# TEFLMate v6.91 — Class Portfolio OS

AI essay grader for TEFL teachers. Photo → OCR → Grade → Portfolio. Live.

**Live:** https://essay-grader-3atbxqeqdfpdh9huwezx57.streamlit.app/

## Stack
- **Frontend:** Streamlit, Python
- **LLM:** Groq `openai/gpt-oss-20b` for grading, `qwen2.5-vl-32b` for OCR
- **DB & Auth:** Supabase (teachers, essays, essay_cache hash)
- **Payments:** Paystack (ZAR), PayShap, PayPal — geo-pricing (R/£/€/$)
- **PDF/Excel:** FPDF, openpyxl
- **Infra:** Hash cache (MD5 essay+level+lang+standard), image compressor (1024px, 85% JPEG), UptimeRobot ping

## What it does
- 📸 Grade 40 handwritten books in 2 mins — camera + OCR + editable
- ✍️ Score 0-10 + CEFR + confidence + AI risk (delve/tapestry/leverage)
- 📚 School OS — auto saves to Supabase, search, filter, history graph, parent share links
- 📦 Batch 50 via CSV `Student,Essay,Level`
- 📄 CV, Cover Letter, Lesson Plan, Principal & HOD reports (PDF/Excel)
- 🎁 Referral `TEFLxxxx` + Student self-submit `?submit=teacher_id`

## Code Quality
- 995 lines, single `main.py`, no duplicate functions
- Mobile fix: black-on-white enforced @768px
- Install prompt: PWA beforeinstallprompt
- Cache: local `st.session_state.grade_cache` + Supabase `essay_cache`

## Run
```bash
pip install -r requirements.txt
streamlit run main.py
