# PharmaGuard 🧬

> **AI-Powered Pharmacogenomic Risk Intelligence System**
> Built for national-level hackathon. CPIC-aligned, deterministic, explainable.

---

## What It Does

PharmaGuard analyzes a patient's genetic VCF file alongside a list of prescribed drugs and generates **personalized pharmacogenomic risk assessments** with:

- **Deterministic CPIC-aligned risk labels** — Safe / Adjust Dosage / Toxic / Ineffective / Unknown
- **Gene-diplotype-phenotype profiling** — for CYP2D6, CYP2C19, CYP2C9, SLCO1B1, TPMT, DPYD
- **Clinical dosage recommendations**
- **Curated alternative medications** — safer pharmacogenomic alternatives for non-Safe drugs
- **AI-generated explanations** — via Google Gemini (degrades gracefully to deterministic fallback)
- **Structured JSON output** — exact schema per the specification

---

## Architecture

```
┌────────────────────┐     HTTP POST /analyze     ┌──────────────────────────────────┐
│  React + Vite      │ ──(file + drugs)──────────▶ │  FastAPI Backend                 │
│  Frontend          │                             │                                  │
│  (Vercel/Netlify)  │ ◀──── AnalysisResponse ───  │  vcf_parser.py  → pysam / pure-Py│
└────────────────────┘                             │  pgx_engine.py  → CPIC rules     │
                                                   │  llm_explainer  → Gemini API     │
                                                   │  models.py      → Pydantic v2    │
                                                   └──────────────────────────────────┘
```

### Risk is always rule-based (never LLM):
1. VCF → parse → gene variants
2. Variants → diplotype inference → phenotype lookup (CPIC tables)
3. Phenotype + drug → risk rule → label + recommendation + alternatives
4. *(LLM only)* Risk data → Gemini → human-readable summary

---

## Supported Genes & Drugs

| Drug | Gene | PM Risk | IM Risk | NM Risk | UM/RM Risk |
|---|---|---|---|---|---|
| CODEINE | CYP2D6 | Ineffective | Adjust Dosage | Safe | **Toxic** |
| WARFARIN | CYP2C9 | Adjust Dosage | Adjust Dosage | Safe | Safe |
| CLOPIDOGREL | CYP2C19 | Ineffective | Adjust Dosage | Safe | Safe |
| SIMVASTATIN | SLCO1B1 | **Toxic** | Adjust Dosage | Safe | Safe |
| AZATHIOPRINE | TPMT | **Toxic** | Adjust Dosage | Safe | Safe |
| FLUOROURACIL | DPYD | **Toxic** | Adjust Dosage | Safe | Safe |

---

## Project Structure

```
HealthTech/
├── backend/
│   ├── main.py            # FastAPI app + /analyze endpoint
│   ├── models.py          # Pydantic v2 schema
│   ├── vcf_parser.py      # pysam + pure-Python fallback
│   ├── pgx_engine.py      # CPIC rule engine + alternatives
│   ├── llm_explainer.py   # Isolated Gemini explanation module
│   ├── Dockerfile         # Production Linux container
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Root component
│   │   ├── types.ts           # TypeScript schema types
│   │   ├── index.css          # Medical-grade design system
│   │   └── components/
│   │       ├── VcfUploader.tsx
│   │       ├── DrugInput.tsx
│   │       ├── ResultCard.tsx  # (includes Alternatives section)
│   │       └── JsonViewer.tsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── sample_vcf/
│   └── sample_patient.vcf     # Realistic VCF with all 6 PGx variants
├── .env.example
└── README.md
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) Google Gemini API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy ..\\.env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run development server
uvicorn main:app --reload --port 8000
```

**API docs**: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

**App**: http://localhost:5173

### Test with Sample VCF

1. Open http://localhost:5173
2. Drag `sample_vcf/sample_patient.vcf` into the upload zone
3. Click all 6 suggested drugs in the medication field
4. Click **Analyze Pharmacogenomic Risk**

Expected results:
- **CODEINE** → Ineffective (CYP2D6 PM, *4/*4)
- **WARFARIN** → Adjust Dosage (CYP2C9 IM, *2/*3)
- **CLOPIDOGREL** → Ineffective (CYP2C19 PM, *2/*2)
- **SIMVASTATIN** → Toxic (SLCO1B1 PM, *5/*5)
- **AZATHIOPRINE** → Adjust Dosage (TPMT IM, *1/*3A)
- **FLUOROURACIL** → Adjust Dosage (DPYD IM, *1/*2A)

---

## Deployment

### Backend — Render (free tier)

1. Push to GitHub
2. Create New Web Service on [render.com](https://render.com)
3. Set **Root Directory** → `backend`
4. Set **Build Command** → `pip install -r requirements.txt && pip install pysam`
5. Set **Start Command** → `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variable: `GEMINI_API_KEY=your_key_here`
7. Add: `ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app`

Or use the included **Dockerfile**:
```bash
cd backend
docker build -t pharma-guard-api .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key pharma-guard-api
```

### Frontend — Vercel

```bash
cd frontend
npm run build        # Build production bundle

# Or deploy directly:
npx vercel --prod
```

Set environment variable in Vercel dashboard:
```
VITE_API_URL=https://your-render-backend.onrender.com
```

### Frontend — Netlify

```toml
# netlify.toml (create in frontend/)
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | No | — | Google Gemini API key for AI explanations |
| `ALLOWED_ORIGINS` | Yes | localhost | Comma-separated CORS origins |
| `MAX_VCF_SIZE_MB` | No | 5 | Max VCF upload size |
| `PORT` | No | 8000 | Backend server port |
| `VITE_API_URL` | No | (proxy) | Frontend: backend API base URL |

---

## Clinical Disclaimer

PharmaGuard is a **clinical decision support tool** designed for research and educational purposes. All recommendations are based on CPIC (Clinical Pharmacogenomics Implementation Consortium) guidelines. Final clinical decisions must be made by a qualified healthcare professional. This tool does not replace professional medical advice.

---

## Guideline Sources

- [CPIC Guidelines](https://cpicpgx.org/) — Clinical Pharmacogenomics Implementation Consortium
- [PharmGKB](https://www.pharmgkb.org/) — Pharmacogenomics Knowledge Base
- [dbSNP](https://www.ncbi.nlm.nih.gov/snp/) — NCBI variant database
