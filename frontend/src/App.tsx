import React, { useState } from 'react';
import type { AnalysisResponse, DrugAnalysisResult } from './types';
import VcfUploader, { type VcfValidationState } from './components/VcfUploader';
import DrugInput from './components/DrugInput';
import ResultCard from './components/ResultCard';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export default function App() {
    const [vcfFile, setVcfFile] = useState<File | null>(null);
    const [drugs, setDrugs] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [response, setResponse] = useState<AnalysisResponse | null>(null);

    /**
     * vcfValidationState drives the VcfUploader visual feedback:
     *   "idle"     → file selected locally, not yet submitted
     *   "pending"  → /analyze in-flight
     *   "accepted" → backend returned 200 (VCF validated + parsed OK)
     *   "rejected" → backend returned 4xx (VCF failed strict validation)
     */
    const [vcfValidationState, setVcfValidationState] =
        useState<VcfValidationState>('idle');
    const [vcfRejectionMessage, setVcfRejectionMessage] = useState<
        string | null
    >(null);

    const canAnalyze = vcfFile !== null && drugs.length > 0 && !loading;

    /** Reset validation feedback whenever the user picks a new file */
    const handleFileSelect = (file: File | null) => {
        setVcfFile(file);
        setVcfValidationState('idle');
        setVcfRejectionMessage(null);
        setError(null);
        setResponse(null);
    };

    const handleAnalyze = async () => {
        if (!canAnalyze) return;

        setLoading(true);
        setError(null);
        setResponse(null);
        // Signal that we are waiting for backend validation
        setVcfValidationState('pending');
        setVcfRejectionMessage(null);

        const formData = new FormData();
        formData.append('file', vcfFile);
        formData.append('drugs', drugs.join(','));

        try {
            // Updated to use Netlify Functions path
            const endpoint = API_BASE ? `${API_BASE}/analyze` : '/.netlify/functions/analyze';
            const res = await fetch(endpoint, {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                // Extract the backend error message to show the user
                let detail = `Server error (${res.status})`;
                try {
                    const err = await res.json();
                    detail = err.detail ?? detail;
                } catch {
                    // ignore JSON parse failures
                }

                // Distinguish VCF validation failures (400) from other errors
                if (res.status === 400 && detail.toLowerCase().includes('vcf')) {
                    // Backend explicitly rejected the VCF content
                    setVcfValidationState('rejected');
                    setVcfRejectionMessage(detail);
                } else {
                    // Other client/server error — reset to idle so user can retry
                    setVcfValidationState('idle');
                }

                throw new Error(detail);
            }

            // 200 OK → VCF was accepted AND parsed successfully by the backend
            const data: AnalysisResponse = await res.json();
            setVcfValidationState('accepted');
            setResponse(data);
        } catch (err: unknown) {
            const msg =
                err instanceof Error
                    ? err.message
                    : 'An unexpected error occurred.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const firstResult = response?.results?.[0];

    return (
        <div className="app-container">
            {/* ── Header ── */}
            <header className="app-header" role="banner">
                <div className="header-brand">
                    <div className="header-logo" aria-hidden="true">⬡</div>
                    <h1 className="header-title">PharmaGuard</h1>
                </div>
                <p className="header-subtitle">AI-Powered Pharmacogenomic Risk Intelligence System</p>
                <div className="header-badges">
                    <span className="header-badge cpic">CPIC Guidelines</span>
                    <span className="header-badge vcf">VCF v4.2</span>
                    <span className="header-badge ai">Gemini AI</span>
                </div>
            </header>

            <main role="main">
                {/* ── Upload Section ── */}
                <section aria-label="Input Section">
                    <div className="upload-section">
                        <div className="card">
                            <VcfUploader
                                onFileSelect={handleFileSelect}
                                selectedFile={vcfFile}
                                validationState={vcfValidationState}
                                rejectionMessage={vcfRejectionMessage}
                            />
                        </div>
                        <div className="card">
                            <DrugInput drugs={drugs} onDrugsChange={setDrugs} />
                        </div>
                    </div>

                    <button
                        className="analyze-btn"
                        onClick={handleAnalyze}
                        disabled={!canAnalyze}
                        id="analyze-button"
                        aria-label="Analyze pharmacogenomic risk"
                        aria-busy={loading}
                    >
                        {loading ? (
                            <>
                                <span className="spinner" role="status" aria-label="Analyzing" />
                                Validating VCF &amp; Analyzing…
                            </>
                        ) : (
                            <>⬡ Analyze Pharmacogenomic Risk</>
                        )}
                    </button>
                </section>

                {/* ── Error Banner ── */}
                {error && (
                    <div className="error-banner" role="alert" aria-live="assertive">
                        <span>⚠️</span>
                        <span>{error}</span>
                    </div>
                )}

                {/* ── Results ── */}
                {response && (
                    <section aria-label="Analysis Results">
                        {/* Patient info bar */}
                        {firstResult && (
                            <div className="patient-info-bar" role="complementary" aria-label="Patient information">
                                <div className="patient-info-item">
                                    <span>🪪</span>
                                    <span>Patient ID: <strong>{firstResult.patient_id}</strong></span>
                                </div>
                                <div className="patient-info-item">
                                    <span>🕐</span>
                                    <span>Analyzed: <strong>{new Date(response.analysis_timestamp).toLocaleString()}</strong></span>
                                </div>
                                <div className="patient-info-item">
                                    <span>💊</span>
                                    <span>Drugs analyzed: <strong>{response.total_drugs_analyzed}</strong></span>
                                </div>
                            </div>
                        )}

                        <div className="results-header">
                            <h2 className="results-title">Risk Assessment Results</h2>
                            <span className="results-count">{response.total_drugs_analyzed} drug{response.total_drugs_analyzed !== 1 ? 's' : ''}</span>
                        </div>

                        <div className="results-grid" role="list" aria-label="Drug risk assessment cards">
                            {response.results.map((result: DrugAnalysisResult) => (
                                <div role="listitem" key={result.drug}>
                                    <ResultCard result={result} />
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* ── Empty state ── */}
                {!response && !loading && !error && (
                    <div className="empty-state" aria-label="No results yet">
                        <span className="empty-state-icon">🧬</span>
                        <p className="empty-state-text">
                            Upload a VCF file and enter medications to receive your personalized pharmacogenomic risk report.
                        </p>
                    </div>
                )}
            </main>
        </div>
    );
}
