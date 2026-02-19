import React, { useState } from 'react';
import type { DrugAnalysisResult, RiskLabel } from '../types';
import JsonViewer from './JsonViewer';

interface ResultCardProps {
    result: DrugAnalysisResult;
}

interface SectionProps {
    label: string;
    icon: string;
    id: string;
    defaultOpen?: boolean;
    children: React.ReactNode;
    badge?: React.ReactNode;
}

function ExpandSection({ label, icon, id, defaultOpen = false, badge, children }: SectionProps) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <>
            <button
                className="expand-btn"
                onClick={() => setOpen((o) => !o)}
                aria-expanded={open}
                aria-controls={`section-${id}`}
                id={`btn-${id}`}
            >
                <span className="section-label">
                    <span>{icon}</span>
                    <span>{label}</span>
                    {badge}
                </span>
                <span className={`expand-icon${open ? ' open' : ''}`}>▼</span>
            </button>
            {open && (
                <div className="expand-content" id={`section-${id}`} role="region" aria-labelledby={`btn-${id}`}>
                    {children}
                </div>
            )}
        </>
    );
}

function getRiskClass(label: RiskLabel): string {
    const map: Record<RiskLabel, string> = {
        Safe: 'safe',
        'Adjust Dosage': 'adjust',
        Toxic: 'toxic',
        Ineffective: 'ineffective',
        Unknown: 'unknown',
    };
    return map[label] ?? 'unknown';
}

function getRiskCardClass(label: RiskLabel): string {
    const map: Record<RiskLabel, string> = {
        Safe: 'risk-safe',
        'Adjust Dosage': 'risk-adjust',
        Toxic: 'risk-toxic',
        Ineffective: 'risk-ineffective',
        Unknown: 'risk-unknown',
    };
    return map[label] ?? 'risk-unknown';
}

function getRiskIcon(label: RiskLabel): string {
    const map: Record<RiskLabel, string> = {
        Safe: '✓',
        'Adjust Dosage': '⚠',
        Toxic: '☠',
        Ineffective: '✗',
        Unknown: '?',
    };
    return map[label] ?? '?';
}

function getConfidenceColor(score: number): string {
    if (score >= 0.9) return 'var(--color-safe)';
    if (score >= 0.7) return 'var(--color-adjust)';
    return 'var(--color-toxic)';
}

function getPhenotypeLabel(phenotype: string): string {
    const labels: Record<string, string> = {
        PM: 'Poor Metabolizer',
        IM: 'Intermediate Metabolizer',
        NM: 'Normal Metabolizer',
        RM: 'Rapid Metabolizer',
        URM: 'Ultrarapid Metabolizer',
        Unknown: 'Unknown Phenotype',
    };
    return labels[phenotype] ?? phenotype;
}

export default function ResultCard({ result }: ResultCardProps) {
    const { risk_assessment, pharmacogenomic_profile, clinical_recommendation, alternative_medications, llm_generated_explanation } = result;
    const riskClass = getRiskClass(risk_assessment.risk_label);
    const cardRiskClass = getRiskCardClass(risk_assessment.risk_label);
    const isNonSafe = risk_assessment.risk_label !== 'Safe' && risk_assessment.risk_label !== 'Unknown';

    return (
        <div className={`result-card ${cardRiskClass}`} role="article" aria-label={`Result for ${result.drug}`}>
            {/* ── Header ── */}
            <div className="result-card-header">
                <div>
                    <div className="drug-name">{result.drug}</div>
                </div>
                <span className="drug-gene-chip">{pharmacogenomic_profile.primary_gene}</span>
                <span className={`risk-badge ${riskClass}`}>
                    <span>{getRiskIcon(risk_assessment.risk_label)}</span>
                    {risk_assessment.risk_label}
                </span>
                <div className="confidence-bar-wrap">
                    <span className="confidence-label">Confidence</span>
                    <div className="confidence-bar">
                        <div
                            className="confidence-bar-fill"
                            style={{
                                width: `${Math.round(risk_assessment.confidence_score * 100)}%`,
                                background: getConfidenceColor(risk_assessment.confidence_score),
                            }}
                        />
                    </div>
                    <span className="confidence-value">{Math.round(risk_assessment.confidence_score * 100)}%</span>
                </div>
            </div>

            {/* ── PGx Profile ── */}
            <ExpandSection
                label="Pharmacogenomic Profile"
                icon="🧬"
                id={`pgx-${result.drug}`}
                defaultOpen={true}
            >
                <div className="pgx-grid">
                    <div className="pgx-cell">
                        <div className="pgx-cell-label">Primary Gene</div>
                        <div className="pgx-cell-value">{pharmacogenomic_profile.primary_gene}</div>
                    </div>
                    <div className="pgx-cell">
                        <div className="pgx-cell-label">Diplotype</div>
                        <div className="pgx-cell-value">{pharmacogenomic_profile.diplotype}</div>
                    </div>
                    <div className="pgx-cell">
                        <div className="pgx-cell-label">Phenotype</div>
                        <div className="pgx-cell-value">
                            <span className={`phenotype-badge ${pharmacogenomic_profile.phenotype}`}>
                                {pharmacogenomic_profile.phenotype}
                            </span>{' '}
                            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)', fontFamily: 'var(--font-sans)', fontWeight: 400 }}>
                                {getPhenotypeLabel(pharmacogenomic_profile.phenotype)}
                            </span>
                        </div>
                    </div>
                    <div className="pgx-cell">
                        <div className="pgx-cell-label">Severity</div>
                        <div className="pgx-cell-value" style={{ textTransform: 'capitalize' }}>{risk_assessment.severity}</div>
                    </div>
                </div>

                {pharmacogenomic_profile.detected_variants.length > 0 && (
                    <>
                        <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--color-text-muted)', marginBottom: 8 }}>
                            Detected Variants
                        </div>
                        <table className="variants-table">
                            <thead>
                                <tr>
                                    <th>rsID</th>
                                    <th>Star Allele</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pharmacogenomic_profile.detected_variants.map((v, i) => (
                                    <tr key={i}>
                                        <td><a href={`https://www.ncbi.nlm.nih.gov/snp/${v.rsid}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-accent)', textDecoration: 'none' }}>{v.rsid}</a></td>
                                        <td>{v.star}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </>
                )}

                {pharmacogenomic_profile.detected_variants.length === 0 && (
                    <p style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>No specific variants detected — using reference diplotype assumption.</p>
                )}
            </ExpandSection>

            {/* ── Clinical Recommendation ── */}
            <ExpandSection
                label="Clinical Recommendation"
                icon="📋"
                id={`rec-${result.drug}`}
                defaultOpen={true}
            >
                <p className="rec-action">{clinical_recommendation.action}</p>

                {clinical_recommendation.contraindication && (
                    <div className="contraindication-banner" style={{ marginBottom: 14 }}>
                        <span>🚫</span>
                        CONTRAINDICATED — Drug is not recommended for this patient
                    </div>
                )}

                <div className="rec-grid">
                    <div className="rec-item">
                        <div className="rec-item-label">Dosage Guidance</div>
                        <div className="rec-item-value">{clinical_recommendation.dosage_guidance}</div>
                    </div>
                    <div className="rec-item">
                        <div className="rec-item-label">Monitoring</div>
                        <div className="rec-item-value">{clinical_recommendation.monitoring}</div>
                    </div>
                </div>

                <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                    Guideline Source: <span className="guideline-chip">{clinical_recommendation.guideline_source}</span>
                </div>
            </ExpandSection>

            {/* ── Alternative Medications ── (prominent when non-Safe) */}
            {alternative_medications.length > 0 && (
                <ExpandSection
                    label="Alternative Medications"
                    icon="💊"
                    id={`alt-${result.drug}`}
                    defaultOpen={isNonSafe}
                    badge={
                        <span style={{
                            marginLeft: 8,
                            fontSize: 11,
                            fontWeight: 700,
                            padding: '2px 8px',
                            background: 'var(--color-alt-bg)',
                            border: '1px solid var(--color-alt-border)',
                            borderRadius: 20,
                            color: 'var(--color-alt)',
                        }}>
                            {alternative_medications.length} options
                        </span>
                    }
                >
                    <p className="alternatives-intro">
                        Given the pharmacogenomic risk profile for <strong>{result.drug}</strong>, the following alternatives have a more favorable genetic interaction for this patient:
                    </p>
                    <div className="alt-list">
                        {alternative_medications.map((alt, i) => (
                            <div key={i} className="alt-item">
                                <div className="alt-item-header">
                                    <span style={{ fontSize: 16 }}>💊</span>
                                    <span className="alt-item-name">{alt.name}</span>
                                </div>
                                <p className="alt-item-rationale">{alt.rationale}</p>
                                <span className="alt-item-advantage">{alt.pgx_advantage}</span>
                            </div>
                        ))}
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 14, lineHeight: 1.5 }}>
                        ⚕️ These alternatives are provided for clinical consideration only. Final prescribing decisions must be made by a qualified healthcare professional.
                    </p>
                </ExpandSection>
            )}

            {/* ── AI Explanation ── */}
            <ExpandSection
                label="AI-Generated Explanation"
                icon="🤖"
                id={`llm-${result.drug}`}
                defaultOpen={false}
            >
                <div className="llm-explanation">
                    <div className={`llm-source-badge ${llm_generated_explanation.source === 'gemini' ? 'gemini' : 'fallback'}`}>
                        {llm_generated_explanation.source === 'gemini' ? '✦ Google Gemini' : '⚙ Deterministic Fallback'}
                    </div>
                    <p>{llm_generated_explanation.summary}</p>
                </div>
            </ExpandSection>

            {/* ── JSON Output ── */}
            <ExpandSection
                label="Raw JSON Output"
                icon="{ }"
                id={`json-${result.drug}`}
                defaultOpen={false}
            >
                <JsonViewer data={result} />
            </ExpandSection>
        </div>
    );
}
