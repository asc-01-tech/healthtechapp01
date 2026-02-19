"""
LLM Explanation Module for PharmaGuard.

ISOLATED: This module only generates human-readable explanations.
It does NOT make any risk decisions or dosage recommendations.
All clinical logic is in pgx_engine.py.

Uses Google Gemini API. Degrades gracefully to deterministic fallback
if API is unavailable or key is missing.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Load Gemini API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _build_prompt(
    drug: str,
    gene: str,
    diplotype: str,
    phenotype: str,
    risk_label: str,
    severity: str,
    action: str,
    alternatives: list,
) -> str:
    """Construct the structured prompt sent to the LLM."""
    alt_names = ", ".join(a.get("name", "") for a in alternatives) if alternatives else "none identified"
    return f"""You are a pharmacogenomics clinical interpretation engine.
Your task is to analyze a humman pharmacogenomics result and generate a scientifically accurate, conservative, CPIC compliant report segment.

CORE RULES:
1. Do not assume diplotypes unless fully supported.
2. If variants are absent or homozygous reference, state that no actionable alleles were detected.
3. Interpret genotype explicitly. For every clinically relevant allele mentioned, avoid implying it was tested if not provided.
4. Avoid absolute safety language. Never use words like 'safe', 'no risk', or 'guaranteed'.
5. Use clinical phrasing: "No actionable pharmacogenomic variants detected", "Standard dosing per CPIC guidelines recommended".
6. For high risk genes (DPYD, TPMT, SLCO1B1, CYP2D6) always add: "Non genetic risk factors still apply. Clinical monitoring remains mandatory."
7. Follow CPIC guideline hierarchy (Level 1A > 1B).

CONTEXT:
- Drug: {drug}
- Primary Gene: {gene}
- Diplotype: {diplotype if diplotype and diplotype != 'Unknown' else 'Not determined (assuming *1/*1 based on absence of variants)'}
- Metabolizer Phenotype: {phenotype}
- Risk Classification: {risk_label} (Severity: {severity})
- Clinical Action: {action}
- Available Alternatives: {alt_names}

TASK:
Write a clinical interpretation summary (max 4-5 sentences) that:
- States the phenotype clearly based on the provided data.
- Explains the implications for {drug} metabolism/safety.
- Provides the specific dosing recommendation (e.g. "Standard dosing", "Reduce dose by 50%").
- Lists any explicit monitoring requirements.
- Mentions pertinent limitations (e.g. "Phasing not performed", "Structural variants not assessed").

OUTPUT FORMAT:
Return ONLY the text paragraph. Do not use Markdown headers. Do not include 'Raw JSON' or other artifacts. Keep the tone professional and suitable for a clinician."""


def _fallback_explanation(
    drug: str,
    gene: str,
    diplotype: str,
    phenotype: str,
    risk_label: str,
) -> Dict[str, Any]:
    """
    Deterministic fallback explanation when LLM is unavailable.
    """
    texts = {
        "Safe": (
            f"Your genetic profile ({diplotype}) for the {gene} gene indicates normal metabolizer status. "
            f"{drug.capitalize()} is expected to be processed by your body at the standard rate, "
            f"meaning the drug should be effective and well-tolerated at standard doses."
        ),
        "Adjust Dosage": (
            f"Your genetic variant ({diplotype}) in the {gene} gene affects how your body processes {drug.lower()}. "
            f"As a {phenotype} metabolizer, you may process this drug more slowly or quickly than average, "
            f"which means your doctor should adjust the dose to ensure safety and effectiveness."
        ),
        "Toxic": (
            f"Your genetic profile ({diplotype}) for {gene} indicates a significantly altered ability to metabolize {drug.lower()}. "
            f"This creates a high risk of drug accumulation and toxicity at standard doses. "
            f"Your healthcare provider should be informed immediately, and alternative medications reviewed."
        ),
        "Ineffective": (
            f"Due to your genetic variant ({diplotype}) in {gene}, your body cannot properly activate {drug.lower()} into its active form. "
            f"This means the medication is unlikely to provide the intended therapeutic benefit. "
            f"Your doctor should consider pharmacogenomically compatible alternatives."
        ),
        "Unknown": (
            f"Insufficient pharmacogenomic data was available for {gene} to make a specific prediction about {drug.lower()}. "
            f"Standard clinical dosing guidelines should be applied, and your physician should be aware of this limitation."
        ),
    }
    text = texts.get(risk_label, texts["Unknown"])
    return {
        "summary": text,
        "source": "deterministic_fallback",
        "model": "none",
    }


def generate_explanation(
    drug: str,
    gene: str,
    diplotype: str,
    phenotype: str,
    risk_label: str,
    severity: str,
    action: str,
    alternatives: list,
) -> Dict[str, Any]:
    """
    Generate a human-readable explanation for the pharmacogenomic risk assessment.

    Returns dict with keys: summary, source, model
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        logger.info("No Gemini API key configured. Using deterministic fallback explanation.")
        return _fallback_explanation(drug, gene, diplotype, phenotype, risk_label)

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = _build_prompt(
            drug, gene, diplotype, phenotype, risk_label, severity, action, alternatives
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=300,
            ),
        )

        summary = response.text.strip()
        return {
            "summary": summary,
            "source": "gemini",
            "model": "gemini-1.5-flash",
        }

    except ImportError:
        logger.warning("google-generativeai not installed. Using fallback explanation.")
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}. Using fallback explanation.")

    return _fallback_explanation(drug, gene, diplotype, phenotype, risk_label)
