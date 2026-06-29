import csv, io, re
import streamlit as st
import pdfplumber, spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="Resume Screening AI", page_icon="🎯", layout="wide")

with open("css/theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

@st.cache_resource
def load_nlp():
    try: return spacy.load("en_core_web_sm")
    except: import subprocess; subprocess.run(["python","-m","spacy","download","en_core_web_sm"]); return spacy.load("en_core_web_sm")

nlp = load_nlp()

SKILLS = [
    r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|go|swift|kotlin|scala)\b',
    r'\b(react|angular|vue|django|flask|fastapi|node\.?js|express|laravel)\b',
    r'\b(sql|mysql|postgresql|mongodb|redis|elasticsearch|sqlite|cassandra)\b',
    r'\b(aws|gcp|azure|docker|kubernetes|terraform|jenkins|github actions)\b',
    r'\b(machine learning|deep learning|nlp|tensorflow|pytorch|scikit.learn)\b',
    r'\b(html|css|tailwind|bootstrap|graphql|rest api|microservices)\b',
    r'\b(git|linux|agile|scrum|jira|figma|tableau|power bi)\b',
]

def get_text(f):
    with pdfplumber.open(f) as p: return "\n".join(pg.extract_text() or "" for pg in p.pages).strip()

def get_skills(text):
    found = set()
    for p in SKILLS: found.update(re.findall(p, text.lower()))
    return sorted(found)

def get_name(text):
    skip = {"resume","curriculum vitae","cv","profile","contact","summary","objective"}
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:6]:
        words = line.split()
        if (2 <= len(words) <= 4
                and all(w[0].isupper() for w in words)
                and not any(ch.isdigit() or ch in "@|/\\:," for ch in line)
                and line.lower() not in skip):
            return line
    doc = nlp(text[:1500])
    return next((e.text for e in doc.ents if e.label_=="PERSON"), "Candidate")

def get_score(resume, jd):
    v = TfidfVectorizer(stop_words="english", ngram_range=(1,2))
    m = v.fit_transform([jd, resume])
    return round(cosine_similarity(m[0:1], m[1:2])[0][0]*100, 1)

def color(s): return "#4ade80" if s>=60 else "#facc15" if s>=35 else "#f87171"

st.markdown('<div class="hero"><div class="hero-badge">🎯 AI Recruitment Tool</div><h1>Resume Screening AI</h1><p>Upload resumes & paste a job description to instantly rank candidates.</p></div><hr class="divider">', unsafe_allow_html=True)

c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown('<div class="card-label">📄 Step 1 — Upload Resumes</div>', unsafe_allow_html=True)
    files = st.file_uploader("PDFs", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
with c2:
    st.markdown('<div class="card-label">💼 Step 2 — Job Description</div>', unsafe_allow_html=True)
    jd = st.text_area("JD", height=160, placeholder="Paste job description here...", label_visibility="collapsed")

st.markdown('<hr class="divider">', unsafe_allow_html=True)
_, mid, _ = st.columns(3)
run = mid.button("⚡ Rank Candidates", type="primary", use_container_width=True)

if run:
    if not files: st.warning("Upload at least one resume."); st.stop()
    if not jd.strip(): st.warning("Paste a job description."); st.stop()

    jd_skills, results = get_skills(jd), []
    with st.spinner("Analysing..."):
        for f in files:
            txt = get_text(f)
            if not txt: continue
            skills = get_skills(txt)
            results.append({"name": get_name(txt), "file": f.name, "score": get_score(txt, jd),
                            "skills": skills, "matched": [s for s in skills if s in jd_skills]})
    results.sort(key=lambda x: x["score"], reverse=True)

    st.markdown('<div class="card-label" style="margin-bottom:1rem">🏆 Rankings</div>', unsafe_allow_html=True)
    for i, r in enumerate(results):
        st.markdown(f"""<div class="score-row">
            <div class="rank-badge">{"🥇" if i==0 else f"#{i+1}"}</div>
            <div><div class="score-name">{r['name']}</div><div style="font-size:.75rem;color:#555e78">{r['file']}</div></div>
            <div class="bar-bg"><div class="bar-fill" style="width:{min(r['score'],100)}%"></div></div>
            <div class="score-pct" style="color:{color(r['score'])}">{r['score']}%</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="divider"><div class="card-label" style="margin-bottom:1rem">📊 Breakdown</div>', unsafe_allow_html=True)
    for i, r in enumerate(results):
        with st.expander(f"{'🥇 ' if i==0 else ''}{r['name']} — {r['score']}% ({r['file']})", expanded=(i==0)):
            chips = "".join(f'<span class="chip {"matched" if s in r["matched"] else ""}">{s}</span>' for s in r["skills"])
            st.markdown(f'<div class="chip-wrap">{chips}</div><div style="font-size:.75rem;color:#4ade80;margin-top:.5rem">✓ {len(r["matched"])} skills match JD</div>', unsafe_allow_html=True)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Rank","Name","File","Score","Matched Skills","All Skills"])
    for i,r in enumerate(results): w.writerow([i+1,r["name"],r["file"],r["score"],", ".join(r["matched"]),", ".join(r["skills"])])
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.download_button("⬇ Download CSV", buf.getvalue(), "rankings.csv", "text/csv", use_container_width=True)
