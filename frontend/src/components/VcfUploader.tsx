import React, { useCallback, useRef, useState } from 'react';

/**
 * validationState reflects the result of BACKEND VCF validation, not just
 * client-side file selection:
 *   - "idle"     → no file has been selected yet
 *   - "pending"  → file chosen locally, awaiting backend response
 *   - "accepted" → backend confirmed the file is a valid VCF
 *   - "rejected" → backend rejected the file (detail in rejectionMessage)
 */
export type VcfValidationState = 'idle' | 'pending' | 'accepted' | 'rejected';

interface VcfUploaderProps {
    onFileSelect: (file: File | null) => void;
    selectedFile: File | null;
    /** Driven by the parent after the /analyze call completes */
    validationState?: VcfValidationState;
    /** Error message returned by the backend when validationState === "rejected" */
    rejectionMessage?: string | null;
}

const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

export default function VcfUploader({
    onFileSelect,
    selectedFile,
    validationState = 'idle',
    rejectionMessage = null,
}: VcfUploaderProps) {
    const [dragOver, setDragOver] = useState(false);
    const [clientError, setClientError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Client-side pre-flight: extension, size, non-empty.
    // Does NOT validate VCF content — that is the backend's responsibility.
    const validateFileLocally = (file: File): string | null => {
        if (!file.name.toLowerCase().endsWith('.vcf')) {
            return 'Only .vcf files are accepted.';
        }
        if (file.size > MAX_SIZE_BYTES) {
            return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum is 5 MB.`;
        }
        if (file.size === 0) {
            return 'File is empty.';
        }
        return null;
    };

    const handleFile = useCallback(
        (file: File) => {
            const error = validateFileLocally(file);
            if (error) {
                setClientError(error);
                onFileSelect(null);
            } else {
                setClientError(null);
                onFileSelect(file);
            }
        },
        [onFileSelect],
    );

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
        },
        [handleFile],
    );

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
    };

    const handleClear = (e: React.MouseEvent) => {
        e.stopPropagation();
        setClientError(null);
        onFileSelect(null);
        if (inputRef.current) inputRef.current.value = '';
    };

    const formatSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
    };

    // Determine active display state (client errors take priority)
    const hasClientError = clientError !== null;
    const isAccepted = !hasClientError && validationState === 'accepted';
    const isRejected =
        !hasClientError && (validationState === 'rejected' || hasClientError);
    const isPending =
        !hasClientError &&
        validationState === 'pending' &&
        selectedFile !== null;
    const isSelected =
        !hasClientError &&
        validationState === 'idle' &&
        selectedFile !== null;

    const zoneClass = [
        'drop-zone',
        dragOver ? 'drag-over' : '',
        isAccepted ? 'valid' : '',
        hasClientError || validationState === 'rejected' ? 'error' : '',
        isPending ? 'pending' : '',
    ]
        .filter(Boolean)
        .join(' ');

    return (
        <div>
            <div className="card-label">Genomic VCF File</div>
            <div
                className={zoneClass}
                role="button"
                tabIndex={0}
                aria-label="Click or drag to upload VCF file"
                onClick={() => inputRef.current?.click()}
                onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept=".vcf"
                    style={{ display: 'none' }}
                    onChange={handleInputChange}
                    aria-label="VCF file input"
                    id="vcf-file-input"
                />

                {/* ── 1. No file selected ── */}
                {!selectedFile && !hasClientError && (
                    <>
                        <span className="drop-zone-icon">🧬</span>
                        <div className="drop-zone-text">
                            {dragOver ? 'Drop your VCF file here' : 'Drag & drop VCF file'}
                        </div>
                        <div className="drop-zone-hint">or click to browse · VCF v4.x · max 5 MB</div>
                    </>
                )}

                {/* ── 2. File chosen locally, waiting for backend ── */}
                {isPending && (
                    <>
                        <span className="drop-zone-icon" style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⏳</span>
                        <div className="drop-zone-text" style={{ color: 'var(--color-text-muted)' }}>
                            Validating VCF…
                        </div>
                        <div className="drop-zone-file-info">
                            <span className="filename">{selectedFile!.name}</span>
                            <span className="filesize">{formatSize(selectedFile!.size)}</span>
                        </div>
                        <div className="drop-zone-hint" style={{ marginTop: 6 }}>
                            Strict backend validation in progress
                        </div>
                    </>
                )}

                {/* ── 3. File selected but not yet submitted (idle) ── */}
                {isSelected && (
                    <>
                        <span className="drop-zone-icon">📂</span>
                        <div className="drop-zone-text">{selectedFile!.name}</div>
                        <div className="drop-zone-file-info">
                            <span className="filename">{selectedFile!.name}</span>
                            <span className="filesize">{formatSize(selectedFile!.size)}</span>
                            <button
                                onClick={handleClear}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    color: 'var(--color-text-muted)',
                                    fontSize: '14px',
                                    padding: '0 0 0 4px',
                                }}
                                title="Remove file"
                                aria-label="Remove file"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="drop-zone-hint" style={{ marginTop: 6 }}>
                            Click &quot;Analyze&quot; to validate and process
                        </div>
                    </>
                )}

                {/* ── 4. Backend confirmed: valid VCF ── */}
                {isAccepted && (
                    <>
                        <span className="drop-zone-icon">✅</span>
                        <div className="drop-zone-text">{selectedFile!.name}</div>
                        <div className="drop-zone-file-info">
                            <span className="filename">{selectedFile!.name}</span>
                            <span className="filesize">{formatSize(selectedFile!.size)}</span>
                            <button
                                onClick={handleClear}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    color: 'var(--color-text-muted)',
                                    fontSize: '14px',
                                    padding: '0 0 0 4px',
                                }}
                                title="Remove file"
                                aria-label="Remove file"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="drop-zone-hint" style={{ marginTop: 6, color: 'var(--color-safe)' }}>
                            VCF validated by backend ✓
                        </div>
                    </>
                )}

                {/* ── 5. Client-side pre-flight rejection ── */}
                {hasClientError && (
                    <>
                        <span className="drop-zone-icon">⚠️</span>
                        <div className="drop-zone-text" style={{ color: 'var(--color-toxic)' }}>
                            File Rejected
                        </div>
                        <div className="drop-zone-error">{clientError}</div>
                        <div className="drop-zone-hint" style={{ marginTop: 8 }}>
                            Click to choose a different file
                        </div>
                    </>
                )}

                {/* ── 6. Backend rejected the VCF content ── */}
                {!hasClientError && validationState === 'rejected' && (
                    <>
                        <span className="drop-zone-icon">❌</span>
                        <div className="drop-zone-text" style={{ color: 'var(--color-toxic)' }}>
                            VCF Validation Failed
                        </div>
                        <div className="drop-zone-error">
                            {rejectionMessage ?? 'The backend rejected this file as an invalid VCF.'}
                        </div>
                        <div className="drop-zone-hint" style={{ marginTop: 8 }}>
                            Click to choose a different file
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
