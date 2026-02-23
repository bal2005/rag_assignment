// LoadingCard.jsx – animated loading indicator with pipeline step badges
import { useState, useEffect } from 'react'

/** RAG pipeline steps shown progressively */
const STEPS = [
    { id: 'filter', label: '🧠 Extracting filters' },
    { id: 'postgres', label: '🐘 Querying Postgres' },
    { id: 'embed', label: '🔢 Creating embedding' },
    { id: 'milvus', label: '🔍 Vector search' },
    { id: 'llm', label: '💡 Generating answer' },
]

// Advance the active step every 2.5 s to give pipeline illusion
function useProgressiveSteps() {
    const [active, setActive] = useState(0)

    useEffect(() => {
        const interval = setInterval(() => {
            setActive(prev => (prev < STEPS.length - 1 ? prev + 1 : prev))
        }, 2200)
        return () => clearInterval(interval)
    }, [])

    return active
}

export default function LoadingCard() {
    const activeIdx = useProgressiveSteps()

    return (
        <div className="loading-card anim-in" role="status" aria-live="polite">
            <div className="spinner-ring" aria-hidden="true" />
            <div className="loading-text">
                <h3>Retrieving context…</h3>
                <p>Running the RAG pipeline — this may take a few seconds.</p>

                <div className="loading-steps">
                    {STEPS.map((step, idx) => {
                        const isDone = idx < activeIdx
                        const isActive = idx === activeIdx
                        if (!isDone && !isActive) return null
                        return (
                            <span
                                key={step.id}
                                className={`step-badge ${isDone ? 'done' : 'active'}`}
                            >
                                {isDone ? '✓' : '●'}
                                {step.label}
                            </span>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}
