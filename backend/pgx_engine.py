"""
PharmaGuard Pharmacogenomics Rule Engine (pgx_engine.py)

CPIC-aligned, deterministic, rule-based risk prediction.
No LLM involvement in risk decisions.

Supported genes:  CYP2D6, CYP2C19, CYP2C9, SLCO1B1, TPMT, DPYD
Supported drugs:  CODEINE, WARFARIN, CLOPIDOGREL, SIMVASTATIN, AZATHIOPRINE, FLUOROURACIL
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from models import (
    AlternativeMedication,
    ClinicalRecommendation,
    DetectedVariant,
    Phenotype,
    PharmacogenomicProfile,
    RiskAssessment,
    RiskLabel,
    Severity,
)
from vcf_parser import VariantRecord

# ---------------------------------------------------------------------------
# Gene → Primary drug mapping
# ---------------------------------------------------------------------------
DRUG_GENE_MAP: Dict[str, str] = {
    "CODEINE":       "CYP2D6",
    "WARFARIN":      "CYP2C9",
    "CLOPIDOGREL":   "CYP2C19",
    "SIMVASTATIN":   "SLCO1B1",
    "AZATHIOPRINE":  "TPMT",
    "FLUOROURACIL":  "DPYD",
}

# ---------------------------------------------------------------------------
# Diplotype → Phenotype tables  (CPIC 2023 guidelines)
# ---------------------------------------------------------------------------

# CYP2D6 diplotype → phenotype
CYP2D6_PHENOTYPE: Dict[str, Phenotype] = {
    "*1/*1":    Phenotype.NM,
    "*1/*2":    Phenotype.NM,
    "*2/*2":    Phenotype.NM,
    "*1/*4":    Phenotype.IM,
    "*1/*5":    Phenotype.IM,
    "*1/*41":   Phenotype.IM,
    "*2/*41":   Phenotype.IM,
    "*4/*41":   Phenotype.IM,
    "*4/*4":    Phenotype.PM,
    "*4/*5":    Phenotype.PM,
    "*5/*5":    Phenotype.PM,
    "*3/*4":    Phenotype.PM,
    "*3/*5":    Phenotype.PM,
    "*1/*1xN":  Phenotype.URM,  # gene duplication
    "*2/*2xN":  Phenotype.URM,
    "*1/*2xN":  Phenotype.URM,
}

# CYP2C19 diplotype → phenotype
CYP2C19_PHENOTYPE: Dict[str, Phenotype] = {
    "*1/*1":    Phenotype.NM,
    "*1/*2":    Phenotype.IM,
    "*1/*3":    Phenotype.IM,
    "*2/*17":   Phenotype.IM,
    "*2/*2":    Phenotype.PM,
    "*2/*3":    Phenotype.PM,
    "*3/*3":    Phenotype.PM,
    "*1/*17":   Phenotype.RM,
    "*17/*17":  Phenotype.RM,
}

# CYP2C9 diplotype → phenotype
CYP2C9_PHENOTYPE: Dict[str, Phenotype] = {
    "*1/*1":    Phenotype.NM,
    "*1/*2":    Phenotype.IM,
    "*1/*3":    Phenotype.IM,
    "*2/*2":    Phenotype.IM,
    "*2/*3":    Phenotype.IM,
    "*3/*3":    Phenotype.PM,
}

# SLCO1B1 diplotype → phenotype  (function-based)
SLCO1B1_PHENOTYPE: Dict[str, Phenotype] = {
    "*1/*1":    Phenotype.NM,
    "*1/*1a":   Phenotype.NM,
    "*1/*1b":   Phenotype.NM,
    "*1/*5":    Phenotype.IM,
    "*1/*15":   Phenotype.IM,
    "*1a/*5":   Phenotype.IM,
    "*5/*5":    Phenotype.PM,
    "*15/*15":  Phenotype.PM,
    "*5/*15":   Phenotype.PM,
}

# TPMT diplotype → phenotype
TPMT_PHENOTYPE: Dict[str, Phenotype] = {
    "*1/*1":    Phenotype.NM,
    "*1/*2":    Phenotype.IM,
    "*1/*3A":   Phenotype.IM,
    "*1/*3B":   Phenotype.IM,
    "*1/*3C":   Phenotype.IM,
    "*2/*3A":   Phenotype.PM,
    "*3A/*3A":  Phenotype.PM,
    "*3A/*3C":  Phenotype.PM,
    "*3B/*3C":  Phenotype.PM,
}

# DPYD diplotype → phenotype
DPYD_PHENOTYPE: Dict[str, Phenotype] = {
    "*1/*1":    Phenotype.NM,
    "*1/*2A":   Phenotype.IM,
    "*1/*13":   Phenotype.IM,
    "*2A/*2A":  Phenotype.PM,
    "*13/*13":  Phenotype.PM,
    "*2A/*13":  Phenotype.PM,
}

GENE_PHENOTYPE_TABLES: Dict[str, Dict[str, Phenotype]] = {
    "CYP2D6":  CYP2D6_PHENOTYPE,
    "CYP2C19": CYP2C19_PHENOTYPE,
    "CYP2C9":  CYP2C9_PHENOTYPE,
    "SLCO1B1": SLCO1B1_PHENOTYPE,
    "TPMT":    TPMT_PHENOTYPE,
    "DPYD":    DPYD_PHENOTYPE,
}


# ---------------------------------------------------------------------------
# Drug-Phenotype → Risk Rule
# Each entry: (risk_label, severity, confidence_score)
# ---------------------------------------------------------------------------

@dataclass
class RiskRule:
    risk_label: RiskLabel
    severity: Severity
    confidence: float
    action: str
    dosage_guidance: str
    monitoring: str
    contraindication: bool


# CODEINE / CYP2D6
CODEINE_RULES: Dict[Phenotype, RiskRule] = {
    Phenotype.PM: RiskRule(
        RiskLabel.INEFFECTIVE,
        Severity.MODERATE,
        0.92,
        "Avoid Codeine. Prescribe alternative analgesic.",
        "Do not prescribe codeine. CYP2D6 PM cannot convert codeine to morphine.",
        "No monitoring needed — switch drug.",
        True,
    ),
    Phenotype.IM: RiskRule(
        RiskLabel.ADJUST_DOSAGE,
        Severity.LOW,
        0.85,
        "Use with caution. Reduced analgesic effect expected.",
        "Start at 50–75% of standard dose. Reassess pain control at 24–48 h.",
        "Monitor pain control and respiratory function.",
        False,
    ),
    Phenotype.NM: RiskRule(
        RiskLabel.SAFE,
        Severity.NONE,
        0.95,
        "Standard codeine therapy appropriate.",
        "Use standard dose as per body weight and pain indication.",
        "Routine monitoring.",
        False,
    ),
    Phenotype.URM: RiskRule(
        RiskLabel.TOXIC,
        Severity.CRITICAL,
        0.97,
        "CONTRAINDICATED. Ultrapid morphine conversion risk.",
        "Do not prescribe codeine. Risk of life-threatening morphine toxicity.",
        "If inadvertently given, monitor for respiratory depression immediately.",
        True,
    ),
    Phenotype.RM: RiskRule(
        RiskLabel.TOXIC,
        Severity.HIGH,
        0.90,
        "Avoid. Elevated morphine levels likely.",
        "Do not prescribe codeine without specialist review.",
        "Monitor for opioid toxicity symptoms.",
        True,
    ),
}

# WARFARIN / CYP2C9
WARFARIN_RULES: Dict[Phenotype, RiskRule] = {
    Phenotype.PM: RiskRule(
        RiskLabel.ADJUST_DOSAGE,
        Severity.HIGH,
        0.93,
        "Significant dose reduction required. High bleeding risk.",
        "Start at 20–40% of standard warfarin dose. Titrate by INR.",
        "Daily INR monitoring until stable. Then weekly.",
        False,
    ),
    Phenotype.IM: RiskRule(
        RiskLabel.ADJUST_DOSAGE,
        Severity.MODERATE,
        0.88,
        "Reduce initial dose by 25–50%.",
        "Use CPIC warfarin dosing algorithm. Target INR 2.0–3.0.",
        "INR monitoring every 3–5 days during initiation.",
        False,
    ),
    Phenotype.NM: RiskRule(
        RiskLabel.SAFE,
        Severity.NONE,
        0.94,
        "Standard warfarin dosing appropriate.",
        "Use standard dosing algorithm (5 mg/day initiation).",
        "Routine INR monitoring (weekly until stable).",
        False,
    ),
    Phenotype.RM: RiskRule(
        RiskLabel.SAFE,
        Severity.LOW,
        0.80,
        "Standard dosing. Monitor for reduced effect.",
        "Use standard initiation dose. Adjust per INR response.",
        "Routine INR monitoring.",
        False,
    ),
}

# CLOPIDOGREL / CYP2C19
CLOPIDOGREL_RULES: Dict[Phenotype, RiskRule] = {
    Phenotype.PM: RiskRule(
        RiskLabel.INEFFECTIVE,
        Severity.HIGH,
        0.95,
        "Clopidogrel likely ineffective. Switch to alternative antiplatelet.",
        "Do not rely on clopidogrel for platelet inhibition. CYP2C19 PM cannot activate prodrug.",
        "If used, monitor platelet reactivity (P2Y12 assay).",
        True,
    ),
    Phenotype.IM: RiskRule(
        RiskLabel.ADJUST_DOSAGE,
        Severity.MODERATE,
        0.87,
        "Reduced clopidogrel efficacy. Consider alternative.",
        "Consider doubling maintenance dose (150 mg/day) or switch to ticagrelor.",
        "Monitor platelet function test at 2 weeks.",
        False,
    ),
    Phenotype.NM: RiskRule(
        RiskLabel.SAFE,
        Severity.NONE,
        0.95,
        "Clopidogrel therapy appropriate at standard dose.",
        "75 mg/day maintenance dose. Standard loading 300–600 mg.",
        "Routine clinical monitoring.",
        False,
    ),
    Phenotype.RM: RiskRule(
        RiskLabel.SAFE,
        Severity.NONE,
        0.88,
        "Standard or enhanced clopidogrel efficacy expected.",
        "Standard 75 mg/day dose.",
        "Routine monitoring.",
        False,
    ),
}

# SIMVASTATIN / SLCO1B1
SIMVASTATIN_RULES: Dict[Phenotype, RiskRule] = {
    Phenotype.PM: RiskRule(
        RiskLabel.TOXIC,
        Severity.HIGH,
        0.91,
        "High myopathy risk. Avoid simvastatin 40–80 mg. Consider alternative statin.",
        "Use simvastatin ≤20 mg/day only if no alternative, or switch to pravastatin/rosuvastatin.",
        "Monitor CK levels. Educate patient on myopathy symptoms.",
        True,
    ),
    Phenotype.IM: RiskRule(
        RiskLabel.ADJUST_DOSAGE,
        Severity.MODERATE,
        0.86,
        "Moderate myopathy risk. Dose limit recommended.",
        "Limit simvastatin to 20 mg/day. Prefer alternative statin.",
        "Monitor CK levels at 4–8 weeks.",
        False,
    ),
    Phenotype.NM: RiskRule(
        RiskLabel.SAFE,
        Severity.NONE,
        0.93,
        "Standard simvastatin therapy appropriate.",
        "Standard dose (20–40 mg/day).",
        "Routine monitoring of liver enzymes and CK.",
        False,
    ),
}

# AZATHIOPRINE / TPMT
AZATHIOPRINE_RULES: Dict[Phenotype, RiskRule] = {
    Phenotype.PM: RiskRule(
        RiskLabel.TOXIC,
        Severity.CRITICAL,
        0.98,
        "CONTRAINDICATED. Severe myelosuppression risk.",
        "Do not prescribe azathioprine. Risk of life-threatening bone marrow suppression.",
        "If inadvertent exposure, daily CBC for at least 4 weeks.",
        True,
    ),
    Phenotype.IM: RiskRule(
        RiskLabel.ADJUST_DOSAGE,
        Severity.HIGH,
        0.90,
        "Start at 30–50% of normal dose. Monitor closely.",
        "Reduce starting dose to 30–50% of standard. Titrate slowly based on CBC.",
        "Weekly CBC for first 2 months, then monthly.",
        False,
    ),
    Phenotype.NM: RiskRule(
        RiskLabel.SAFE,
        Severity.NONE,
        0.95,
        "Standard azathioprine dosing appropriate.",
        "Standard dose (1.5–2.5 mg/kg/day).",
        "Routine CBC monitoring every 1–3 months.",
        False,
    ),
}

# FLUOROURACIL / DPYD
FLUOROURACIL_RULES: Dict[Phenotype, RiskRule] = {
    Phenotype.PM: RiskRule(
        RiskLabel.TOXIC,
        Severity.CRITICAL,
        0.97,
        "CONTRAINDICATED. Severe fluoropyrimidine toxicity risk.",
        "Do not administer 5-FU or capecitabine. DPYD PM at extreme risk of fatal toxicity.",
        "If inadvertently given, immediate discontinuation and intensive supportive care.",
        True,
    ),
    Phenotype.IM: RiskRule(
        RiskLabel.ADJUST_DOSAGE,
        Severity.HIGH,
        0.92,
        "50% dose reduction required. Close toxicity monitoring.",
        "Reduce 5-FU starting dose by 50%. Dose-adjust based on toxicity assessment.",
        "Weekly toxicity assessment (CBC, mucositis, diarrhea) for first 2 cycles.",
        False,
    ),
    Phenotype.NM: RiskRule(
        RiskLabel.SAFE,
        Severity.NONE,
        0.94,
        "Standard fluorouracil therapy appropriate.",
        "Standard dosing per oncology protocol.",
        "Routine toxicity monitoring per protocol.",
        False,
    ),
}

DRUG_RULES: Dict[str, Dict[Phenotype, RiskRule]] = {
    "CODEINE":       CODEINE_RULES,
    "WARFARIN":      WARFARIN_RULES,
    "CLOPIDOGREL":   CLOPIDOGREL_RULES,
    "SIMVASTATIN":   SIMVASTATIN_RULES,
    "AZATHIOPRINE":  AZATHIOPRINE_RULES,
    "FLUOROURACIL":  FLUOROURACIL_RULES,
}

# ---------------------------------------------------------------------------
# Alternative medications (rule-based, not LLM)
# Shown when risk is non-Safe
# ---------------------------------------------------------------------------

ALTERNATIVES: Dict[str, List[AlternativeMedication]] = {
    "CODEINE": [
        AlternativeMedication(
            name="Tramadol (with caution)",
            rationale="Partially metabolized by CYP2D6 but dual mechanism via norepinephrine/serotonin reuptake inhibition maintains efficacy in PM.",
            pgx_advantage="Less dependent on CYP2D6 for analgesic effect than codeine.",
        ),
        AlternativeMedication(
            name="Acetaminophen (Paracetamol)",
            rationale="No CYP2D6 metabolism. Safe and effective for mild-to-moderate pain.",
            pgx_advantage="Pharmacogenomically neutral — not affected by CYP2D6 phenotype.",
        ),
        AlternativeMedication(
            name="NSAIDs (e.g., Ibuprofen)",
            rationale="Non-opioid analgesic with no pharmacogenomic concern for CYP2D6.",
            pgx_advantage="Independent of CYP2D6 metabolizer status.",
        ),
        AlternativeMedication(
            name="Morphine (direct opioid)",
            rationale="Does not require CYP2D6 activation — acts directly on opioid receptors.",
            pgx_advantage="Bypasses CYP2D6 prodrug conversion step entirely.",
        ),
    ],
    "WARFARIN": [
        AlternativeMedication(
            name="Apixaban (Eliquis)",
            rationale="Direct oral anticoagulant (DOAC) not metabolized by CYP2C9. No PGx titration needed.",
            pgx_advantage="Not affected by CYP2C9 or VKORC1 polymorphisms.",
        ),
        AlternativeMedication(
            name="Rivaroxaban (Xarelto)",
            rationale="Factor Xa inhibitor; predictable pharmacokinetics not dependent on CYP2C9.",
            pgx_advantage="Pharmacogenomically neutral anticoagulant.",
        ),
        AlternativeMedication(
            name="Dabigatran (Pradaxa)",
            rationale="Direct thrombin inhibitor. No CYP2C9 involvement in metabolism.",
            pgx_advantage="Fixed dosing without genetic dose adjustment.",
        ),
    ],
    "CLOPIDOGREL": [
        AlternativeMedication(
            name="Ticagrelor (Brilinta)",
            rationale="Direct-acting P2Y12 inhibitor. Does not require CYP2C19 bioactivation.",
            pgx_advantage="Fully effective regardless of CYP2C19 metabolizer status.",
        ),
        AlternativeMedication(
            name="Prasugrel (Effient)",
            rationale="Less dependent on CYP2C19 for activation than clopidogrel.",
            pgx_advantage="Stronger and more consistent platelet inhibition in CYP2C19 PM.",
        ),
    ],
    "SIMVASTATIN": [
        AlternativeMedication(
            name="Pravastatin",
            rationale="Not significantly transported by SLCO1B1, lower myopathy risk.",
            pgx_advantage="Minimal SLCO1B1-related statin accumulation.",
        ),
        AlternativeMedication(
            name="Rosuvastatin (low dose)",
            rationale="Lower myopathy risk than simvastatin at equivalent LDL-lowering doses.",
            pgx_advantage="Reduced SLCO1B1-mediated hepatic uptake variability.",
        ),
        AlternativeMedication(
            name="Fluvastatin",
            rationale="Primarily CYP2C9-metabolized; SLCO1B1 impact minimal.",
            pgx_advantage="Low SLCO1B1 transporter affinity.",
        ),
    ],
    "AZATHIOPRINE": [
        AlternativeMedication(
            name="Mycophenolate Mofetil (MMF)",
            rationale="Immunosuppressant not metabolized via TPMT pathway. Safe in TPMT PM.",
            pgx_advantage="Completely independent of TPMT enzyme activity.",
        ),
        AlternativeMedication(
            name="Methotrexate (low dose)",
            rationale="Antifolate immunosuppressant with no TPMT dependency.",
            pgx_advantage="TPMT-independent mechanism of action.",
        ),
        AlternativeMedication(
            name="Ciclosporin",
            rationale="Calcineurin inhibitor with no TPMT involvement.",
            pgx_advantage="Not affected by TPMT polymorphisms.",
        ),
    ],
    "FLUOROURACIL": [
        AlternativeMedication(
            name="Irinotecan",
            rationale="Topoisomerase I inhibitor; different metabolic pathway (UGT1A1), not DPYD.",
            pgx_advantage="Does not rely on DPYD for detoxification — safe for DPYD-deficient patients.",
        ),
        AlternativeMedication(
            name="Capecitabine (50% dose-adjusted)",
            rationale="Prodrug of 5-FU; same DPYD concern but allows more precise oral dosing with dose reduction.",
            pgx_advantage="Enables 50% dose reduction while maintaining some efficacy — only for IM, not PM.",
        ),
        AlternativeMedication(
            name="Gemcitabine",
            rationale="Nucleoside analog with different enzymatic pathway from fluoropyrimidines.",
            pgx_advantage="Independent of DPYD — no risk of fluoropyrimidine-related toxicity.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# Phenotype inference from detected variants
# ---------------------------------------------------------------------------

def _infer_diplotype(gene: str, variants: List[VariantRecord]) -> str:
    """
    Infer a diplotype string from detected star allele annotations.
    Returns '*1/*1' (NM assumption) if insufficient data.
    """
    stars = [v.star for v in variants if v.star and v.star != "."]
    unique_stars = sorted(set(stars))

    if len(unique_stars) == 0:
        return "*1/*1"
    elif len(unique_stars) == 1:
        return f"{unique_stars[0]}/{unique_stars[0]}"
    else:
        # Take the two most common / most impactful stars
        return f"{unique_stars[0]}/{unique_stars[1]}"


def _lookup_phenotype(gene: str, diplotype: str) -> Phenotype:
    """Look up phenotype from diplotype table. Tries both orientations."""
    table = GENE_PHENOTYPE_TABLES.get(gene, {})

    # Normalize: ensure * prefix on each allele
    if diplotype in table:
        return table[diplotype]

    # Try reversed (e.g., *4/*1 → *1/*4)
    parts = diplotype.split("/")
    if len(parts) == 2:
        reversed_dip = f"{parts[1]}/{parts[0]}"
        if reversed_dip in table:
            return table[reversed_dip]

    # Try uppercase
    upper_dip = diplotype.upper()
    if upper_dip in table:
        return table[upper_dip]

    return Phenotype.UNKNOWN


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

@dataclass
class PgxEngineResult:
    risk_assessment: RiskAssessment
    pgx_profile: PharmacogenomicProfile
    clinical_recommendation: ClinicalRecommendation
    alternative_medications: List[AlternativeMedication]


def analyze_drug(
    drug: str,
    gene_variants: Dict[str, List[VariantRecord]],
) -> PgxEngineResult:
    """
    Analyze a single drug against detected gene variants.
    Returns structured PgxEngineResult with risk, profile, recommendation, and alternatives.
    """
    drug_upper = drug.strip().upper()

    # --- Gene lookup ---
    primary_gene = DRUG_GENE_MAP.get(drug_upper)
    if not primary_gene:
        # Unknown drug
        return _unknown_result(drug_upper)

    # --- Variant extraction ---
    variants = gene_variants.get(primary_gene, [])
    diplotype = _infer_diplotype(primary_gene, variants)
    phenotype = _lookup_phenotype(primary_gene, diplotype)

    # --- Detected variants ---
    detected: List[DetectedVariant] = []
    seen = set()
    for v in variants:
        key = (v.rsid or v.id, v.star)
        if key not in seen and (v.rsid or v.star):
            detected.append(DetectedVariant(
                rsid=v.rsid or v.id or ".",
                star=v.star or ".",
            ))
            seen.add(key)

    # --- Risk rule lookup ---
    rules = DRUG_RULES.get(drug_upper, {})
    rule = rules.get(phenotype)

    if rule is None or phenotype == Phenotype.UNKNOWN:
        # Graceful degradation
        return _unknown_result(drug_upper, primary_gene, diplotype, phenotype, detected)

    risk_assessment = RiskAssessment(
        risk_label=rule.risk_label,
        confidence_score=rule.confidence,
        severity=rule.severity,
    )

    pgx_profile = PharmacogenomicProfile(
        primary_gene=primary_gene,
        diplotype=diplotype,
        phenotype=phenotype,
        detected_variants=detected,
    )

    clinical_rec = ClinicalRecommendation(
        action=rule.action,
        dosage_guidance=rule.dosage_guidance,
        monitoring=rule.monitoring,
        contraindication=rule.contraindication,
        guideline_source="CPIC",
    )

    # Alternatives: only when not Safe
    alternatives: List[AlternativeMedication] = []
    if rule.risk_label != RiskLabel.SAFE:
        alternatives = ALTERNATIVES.get(drug_upper, [])
        # For IM phenotype of FLUOROURACIL, remove "Capecitabine" from PM alternatives
        # (already handled — capecitabine is only listed as IM option in rationale)

    return PgxEngineResult(
        risk_assessment=risk_assessment,
        pgx_profile=pgx_profile,
        clinical_recommendation=clinical_rec,
        alternative_medications=alternatives,
    )


def _unknown_result(
    drug: str,
    gene: str = "UNKNOWN",
    diplotype: str = "*1/*1",
    phenotype: Phenotype = Phenotype.UNKNOWN,
    detected: Optional[List[DetectedVariant]] = None,
) -> PgxEngineResult:
    """Return a graceful Unknown result when data is insufficient."""
    return PgxEngineResult(
        risk_assessment=RiskAssessment(
            risk_label=RiskLabel.UNKNOWN,
            confidence_score=0.0,
            severity=Severity.NONE,
        ),
        pgx_profile=PharmacogenomicProfile(
            primary_gene=gene,
            diplotype=diplotype,
            phenotype=phenotype,
            detected_variants=detected or [],
        ),
        clinical_recommendation=ClinicalRecommendation(
            action="Insufficient pharmacogenomic data. Use standard clinical judgment.",
            dosage_guidance="No genotype-guided dosage adjustment available.",
            monitoring="Standard monitoring per drug labelling.",
            contraindication=False,
            guideline_source="CPIC",
        ),
        alternative_medications=[],
    )
