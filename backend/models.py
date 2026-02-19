"""
Pydantic v2 models for PharmaGuard API response schema.
Strictly enforces the output structure per specification.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field  # knjokjml 


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLabel(str, Enum):
    SAFE = "Safe"
    ADJUST_DOSAGE = "Adjust Dosage"
    TOXIC = "Toxic"
    INEFFECTIVE = "Ineffective"
    UNKNOWN = "Unknown"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Phenotype(str, Enum):
    PM = "PM"      # Poor Metabolizer
    IM = "IM"      # Intermediate Metabolizer
    NM = "NM"      # Normal Metabolizer
    RM = "RM"      # Rapid Metabolizer
    URM = "URM"    # Ultrarapid Metabolizer
    UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class DetectedVariant(BaseModel):
    rsid: str = Field(..., description="dbSNP rsID (e.g. rs1065852)")
    star: str = Field(..., description="Star allele designation (e.g. *4)")


class PharmacogenomicProfile(BaseModel):
    primary_gene: str = Field(..., description="Primary PGx gene symbol")
    diplotype: str = Field(..., description="Diplotype string (e.g. *1/*4)")
    phenotype: Phenotype = Field(..., description="Metabolizer phenotype")
    detected_variants: List[DetectedVariant] = Field(
        default_factory=list,
        description="List of detected pharmacogenomic variants"
    )


class RiskAssessment(BaseModel):
    risk_label: RiskLabel = Field(..., description="Clinical risk classification")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    severity: Severity = Field(..., description="Clinical severity level")


class AlternativeMedication(BaseModel):
    name: str = Field(..., description="Alternative medication name")
    rationale: str = Field(..., description="Why this is a safer alternative")
    pgx_advantage: str = Field(..., description="Pharmacogenomic advantage over the original drug")


class ClinicalRecommendation(BaseModel):
    action: str = Field(..., description="Primary recommended action")
    dosage_guidance: str = Field(..., description="Dosage adjustment guidance")
    monitoring: str = Field(..., description="Monitoring requirements")
    contraindication: bool = Field(..., description="Whether drug is contraindicated")
    guideline_source: str = Field(default="CPIC", description="Clinical guideline source")


class QualityMetrics(BaseModel):
    vcf_parsing_success: bool = Field(..., description="Whether VCF was successfully parsed")
    variants_found: int = Field(default=0, description="Number of PGx variants found")
    gene_coverage: List[str] = Field(default_factory=list, description="Genes with detected variants")


# ---------------------------------------------------------------------------
# Main per-drug result model
# ---------------------------------------------------------------------------

class DrugAnalysisResult(BaseModel):
    patient_id: str = Field(..., description="Patient identifier derived from VCF sample")
    drug: str = Field(..., description="Drug name (uppercase)")
    timestamp: str = Field(..., description="ISO 8601 analysis timestamp")
    risk_assessment: RiskAssessment
    pharmacogenomic_profile: PharmacogenomicProfile
    clinical_recommendation: ClinicalRecommendation
    alternative_medications: List[AlternativeMedication] = Field(
        default_factory=list,
        description="Pharmacogenomically safer alternatives (populated when risk is non-Safe)"
    )
    llm_generated_explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Human-readable AI-generated explanation"
    )
    quality_metrics: QualityMetrics


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class AnalysisResponse(BaseModel):
    results: List[DrugAnalysisResult]
    total_drugs_analyzed: int
    analysis_timestamp: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int
