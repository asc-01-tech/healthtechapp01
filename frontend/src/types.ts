// PharmaGuard TypeScript types — mirrors the Pydantic backend schema exactly

export type RiskLabel = 'Safe' | 'Adjust Dosage' | 'Toxic' | 'Ineffective' | 'Unknown';
export type Severity = 'none' | 'low' | 'moderate' | 'high' | 'critical';
export type Phenotype = 'PM' | 'IM' | 'NM' | 'RM' | 'URM' | 'Unknown';

export interface DetectedVariant {
    rsid: string;
    star: string;
}

export interface PharmacogenomicProfile {
    primary_gene: string;
    diplotype: string;
    phenotype: Phenotype;
    detected_variants: DetectedVariant[];
}

export interface RiskAssessment {
    risk_label: RiskLabel;
    confidence_score: number;
    severity: Severity;
}

export interface AlternativeMedication {
    name: string;
    rationale: string;
    pgx_advantage: string;
}

export interface ClinicalRecommendation {
    action: string;
    dosage_guidance: string;
    monitoring: string;
    contraindication: boolean;
    guideline_source: string;
}

export interface LLMExplanation {
    summary: string;
    source: string;
    model?: string;
}

export interface QualityMetrics {
    vcf_parsing_success: boolean;
    variants_found: number;
    gene_coverage: string[];
}

export interface DrugAnalysisResult {
    patient_id: string;
    drug: string;
    timestamp: string;
    risk_assessment: RiskAssessment;
    pharmacogenomic_profile: PharmacogenomicProfile;
    clinical_recommendation: ClinicalRecommendation;
    alternative_medications: AlternativeMedication[];
    llm_generated_explanation: LLMExplanation;
    quality_metrics: QualityMetrics;
}

export interface AnalysisResponse {
    results: DrugAnalysisResult[];
    total_drugs_analyzed: number;
    analysis_timestamp: string;
}
