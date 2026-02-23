// ChunksSection.jsx – collapsible retrieved chunks with score color coding
import { useState } from 'react'

/** Returns 'high' / 'medium' / 'low' based on similarity score thresholds */
function scoreLevel(score) {
    if (score >= 0.85) return 'high'
    if (score >= 0.70) return 'medium'
    return 'low'
}

function ScoreBadge({ score }) {
    const level = scoreLevel(score)
    const label = (score * 100).toFixed(1) + '%'

    return (
        <span className={`score-badge ${level}`}>
            <span className={`score-dot ${level}`} />
            {label}
        </span>
    )
}

export default function ChunksSection({ chunks }) {
    const [isOpen, setIsOpen] = useState(true)

    if (!chunks || chunks.length === 0) return null

    return (
        <div className="chunks-card anim-in">
            {/* Collapsible header */}
            <div
                id="chunks-toggle"
                className="chunks-header"
                onClick={() => setIsOpen(o => !o)}
                role="button"
                aria-expanded={isOpen}
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && setIsOpen(o => !o)}
            >
                <div className="chunks-header-left">
                    <span className="card-icon green" style={{ width: 32, height: 32, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, borderRadius: 6, background: '#F0FDF4' }}>📄</span>
                    <span style={{ fontWeight: 700, fontSize: 15 }}>Retrieved Chunks</span>
                    <span className="chunk-count-badge">{chunks.length} chunk{chunks.length !== 1 ? 's' : ''}</span>
                </div>
                <span className={`collapse-icon${isOpen ? ' open' : ''}`}>▲</span>
            </div>

            {/* Chunk list */}
            {isOpen && (
                <div className="chunks-list">
                    {chunks.map((chunk, idx) => (
                        <ChunkItem key={idx} chunk={chunk} index={idx} />
                    ))}
                </div>
            )}
        </div>
    )
}

function ChunkItem({ chunk, index }) {
    return (
        <div
            className="chunk-item anim-in"
            id={`chunk-item-${index}`}
            style={{ animationDelay: `${index * 0.05}s` }}
        >
            <div className="chunk-meta">
                <span className="meta-tag">Contract #{chunk.contract_id}</span>
                <span className="meta-tag" style={{ background: '#F5F3FF', color: '#6D28D9' }}>
                    {chunk.contract_type || 'N/A'}
                </span>
                <ScoreBadge score={chunk.similarity_score} />
            </div>
            <div className="chunk-text">{chunk.chunk_text}</div>
        </div>
    )
}
