import React, { useCallback, useState } from 'react';
import type { DrugAnalysisResult } from '../types';

interface JsonViewerProps {
    data: DrugAnalysisResult;
}

function syntaxHighlight(json: string): string {
    return json
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(
            /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
            (match) => {
                let cls = 'json-number';
                if (/^"/.test(match)) {
                    cls = /:$/.test(match) ? 'json-key' : 'json-string';
                } else if (/true|false/.test(match)) {
                    cls = 'json-bool';
                } else if (/null/.test(match)) {
                    cls = 'json-null';
                }
                return `<span class="${cls}">${match}</span>`;
            },
        );
}

export default function JsonViewer({ data }: JsonViewerProps) {
    const [copied, setCopied] = useState(false);

    const jsonString = JSON.stringify(data, null, 2);
    const highlighted = syntaxHighlight(jsonString);

    const handleCopy = useCallback(() => {
        navigator.clipboard.writeText(jsonString).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    }, [jsonString]);

    const handleDownload = useCallback(() => {
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pharma_guard_${data.drug}_${data.patient_id}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }, [jsonString, data.drug, data.patient_id]);

    return (
        <div className="json-viewer-wrap">
            <div className="json-viewer-actions">
                <button
                    className={`json-action-btn${copied ? ' copied' : ''}`}
                    onClick={handleCopy}
                    id={`copy-json-${data.drug}`}
                    aria-label="Copy JSON to clipboard"
                >
                    {copied ? '✓ Copied!' : '📋 Copy JSON'}
                </button>
                <button
                    className="json-action-btn"
                    onClick={handleDownload}
                    id={`download-json-${data.drug}`}
                    aria-label="Download JSON"
                >
                    ⬇ Download
                </button>
            </div>
            <pre
                className="json-pre"
                dangerouslySetInnerHTML={{ __html: highlighted }}
                aria-label={`JSON output for ${data.drug}`}
            />
        </div>
    );
}
