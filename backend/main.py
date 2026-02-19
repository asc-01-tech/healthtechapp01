"""
PharmaGuard FastAPI Backend — main.py

Endpoint: POST /analyze
  - multipart/form-data
  - field 'file': VCF file (≤5 MB, .vcf extension)
  - field 'drugs': comma-separated drug names
  - Returns: AnalysisResponse (list of DrugAnalysisResult per drug)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from llm_explainer import generate_explanation
from models import (
    AnalysisResponse,
    DrugAnalysisResult,
    ErrorResponse,
    QualityMetrics,
)
from pgx_engine import analyze_drug
from vcf_parser import extract_patient_id, parse_vcf

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("pharma_guard")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PharmaGuard API",
    description="AI-powered pharmacogenomic risk prediction system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Limits
MAX_VCF_SIZE_MB = int(os.getenv("MAX_VCF_SIZE_MB", "5"))
MAX_VCF_BYTES = MAX_VCF_SIZE_MB * 1024 * 1024

SUPPORTED_DRUGS = {
    "CODEINE", "WARFARIN", "CLOPIDOGREL",
    "SIMVASTATIN", "AZATHIOPRINE", "FLUOROURACIL",
}


# ---------------------------------------------------------------------------
# Serve static frontend
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).parent.parent / "frontend_static"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "PharmaGuard API. Visit /docs for API documentation."}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "PharmaGuard API", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Main analysis endpoint
# ---------------------------------------------------------------------------
@app.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    tags=["Analysis"],
    summary="Analyze pharmacogenomic risk from VCF file and drug list",
)
async def analyze(
    file: UploadFile = File(..., description="VCF v4.2 genomic file (≤5 MB)"),
    drugs: str = Form(..., description="Comma-separated list of drug names"),
):
    # ---- File extension validation ----
    if not file.filename or not file.filename.lower().endswith(".vcf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a VCF file (.vcf extension).",
        )

    vcf_bytes = await file.read()
    if len(vcf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded VCF file is empty.")
    if len(vcf_bytes) > MAX_VCF_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"VCF file exceeds maximum size of {MAX_VCF_SIZE_MB} MB.",
        )

    # ---- Strict VCF content validation (runs BEFORE anything else) ----
    # Do NOT catch this — a bad VCF must be rejected immediately with HTTP 400.
    # Validation and upload success are NOT the same thing.
    try:
        gene_variants = parse_vcf(vcf_bytes)
        patient_id = extract_patient_id(vcf_bytes)
    except ValueError as exc:
        logger.warning(f"VCF validation rejected file '{file.filename}': {exc}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid VCF file: {exc}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error parsing VCF '{file.filename}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"VCF file could not be parsed: {exc}",
        )

    genes_with_data = [g for g, v in gene_variants.items() if v]
    logger.info(
        f"VCF validated and parsed | file={file.filename} "
        f"| patient={patient_id} | genes with data={genes_with_data}"
    )

    # ---- Drug list validation ----
    drug_list_raw = [d.strip().upper() for d in drugs.split(",") if d.strip()]
    if not drug_list_raw:
        raise HTTPException(status_code=400, detail="No drugs specified. Provide at least one drug name.")

    # Deduplicate while preserving order
    seen_drugs: set = set()
    drug_list: List[str] = []
    for d in drug_list_raw:
        if d not in seen_drugs:
            drug_list.append(d)
            seen_drugs.add(d)

    logger.info(f"Received analysis request | file={file.filename} | drugs={drug_list}")

    # ---- Per-drug analysis ----
    results: List[DrugAnalysisResult] = []
    analysis_ts = datetime.now(timezone.utc).isoformat()
    gene_coverage = [g for g, v in gene_variants.items() if v]

    for drug in drug_list:
        try:
            engine_result = analyze_drug(drug, gene_variants)

            quality = QualityMetrics(
                vcf_parsing_success=True,  # We would not reach here if parsing failed
                variants_found=len(engine_result.pgx_profile.detected_variants),
                gene_coverage=gene_coverage,
            )

            # LLM explanation (isolated, does not affect risk)
            alt_dicts = [
                {"name": a.name, "rationale": a.rationale}
                for a in engine_result.alternative_medications
            ]
            llm_explanation = generate_explanation(
                drug=drug,
                gene=engine_result.pgx_profile.primary_gene,
                diplotype=engine_result.pgx_profile.diplotype,
                phenotype=engine_result.pgx_profile.phenotype.value,
                risk_label=engine_result.risk_assessment.risk_label.value,
                severity=engine_result.risk_assessment.severity.value,
                action=engine_result.clinical_recommendation.action,
                alternatives=alt_dicts,
            )

            drug_result = DrugAnalysisResult(
                patient_id=patient_id,
                drug=drug,
                timestamp=analysis_ts,
                risk_assessment=engine_result.risk_assessment,
                pharmacogenomic_profile=engine_result.pgx_profile,
                clinical_recommendation=engine_result.clinical_recommendation,
                alternative_medications=engine_result.alternative_medications,
                llm_generated_explanation=llm_explanation,
                quality_metrics=quality,
            )
            results.append(drug_result)

        except Exception as e:
            # Propagate analysis engine failures — do not silently produce UNKNOWN results.
            logger.error(f"Analysis engine failed for drug '{drug}': {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed for drug '{drug}': {str(e)[:200]}",
            )

    response = AnalysisResponse(
        results=results,
        total_drugs_analyzed=len(results),
        analysis_timestamp=analysis_ts,
    )

    logger.info(f"Analysis complete | {len(results)} drugs processed")
    return response


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again.",
            "status_code": 500,
        },
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
