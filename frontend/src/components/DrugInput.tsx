import React, { useRef, useState } from 'react';

interface DrugInputProps {
    drugs: string[];
    onDrugsChange: (drugs: string[]) => void;
}

const KNOWN_DRUGS = ['CODEINE', 'WARFARIN', 'CLOPIDOGREL', 'SIMVASTATIN', 'AZATHIOPRINE', 'FLUOROURACIL'];

export default function DrugInput({ drugs, onDrugsChange }: DrugInputProps) {
    const [inputValue, setInputValue] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    const addDrug = (raw: string) => {
        const name = raw.trim().toUpperCase();
        if (!name) return;
        if (drugs.includes(name)) {
            setInputValue('');
            return;
        }
        onDrugsChange([...drugs, name]);
        setInputValue('');
    };

    const removeDrug = (drug: string) => {
        onDrugsChange(drugs.filter((d) => d !== drug));
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === ',' || e.key === 'Enter') {
            e.preventDefault();
            addDrug(inputValue);
        }
        if (e.key === 'Backspace' && inputValue === '' && drugs.length > 0) {
            removeDrug(drugs[drugs.length - 1]);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        if (val.endsWith(',')) {
            addDrug(val.slice(0, -1));
        } else {
            setInputValue(val);
        }
    };

    const handleBlur = () => {
        if (inputValue.trim()) addDrug(inputValue);
    };

    const addSuggested = (drug: string) => {
        if (!drugs.includes(drug)) {
            onDrugsChange([...drugs, drug]);
        }
        inputRef.current?.focus();
    };

    return (
        <div>
            <div className="card-label">Medications to Evaluate</div>
            <div
                className="drug-input-area"
                onClick={() => inputRef.current?.focus()}
                id="drug-input-area"
            >
                {drugs.map((drug) => (
                    <span key={drug} className="drug-tag">
                        {drug}
                        <button
                            className="drug-tag-remove"
                            onClick={(e) => { e.stopPropagation(); removeDrug(drug); }}
                            aria-label={`Remove ${drug}`}
                        >
                            ×
                        </button>
                    </span>
                ))}
                <input
                    ref={inputRef}
                    className="drug-input-field"
                    value={inputValue}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    onBlur={handleBlur}
                    placeholder={drugs.length === 0 ? 'Type drug name, press Enter or comma...' : '+'}
                    aria-label="Drug name input"
                    id="drug-name-input"
                    autoComplete="off"
                    spellCheck={false}
                />
            </div>
            <div className="drug-input-hint">
                Supported: {KNOWN_DRUGS.filter((d) => !drugs.includes(d)).map((d) => (
                    <button
                        key={d}
                        onClick={() => addSuggested(d)}
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--color-text-muted)',
                            fontSize: '11px',
                            textDecoration: 'underline',
                            padding: '0 4px',
                            fontFamily: 'var(--font-sans)',
                        }}
                        aria-label={`Add ${d}`}
                        title={`Click to add ${d}`}
                    >
                        {d}
                    </button>
                ))}
            </div>
        </div>
    );
}
