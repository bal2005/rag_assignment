// App.jsx – Root application component
// ─────────────────────────────────────────────────────────────────────────────
// Example queries:
//   "Show summary about contract with TransContinental Corp"
//   "Which contracts in the EU region are currently in Pending status and what are their risk scores?"
//   "Show me the Data Privacy related contracts in France and summarize their compliance requirements."
//   "What are the service agreement terms with Asiatrade Logistics?"
// ─────────────────────────────────────────────────────────────────────────────
import { useState, useRef, useCallback } from 'react'
import { postQuery } from './api'
import AnswerCard from './components/AnswerCard'
import ChunksSection from './components/ChunksSection'
import RecordsTable from './components/RecordsTable'
import LoadingCard from './components/LoadingCard'
import ErrorCard from './components/ErrorCard'

/* ── Example queries shown in the UI ─────────────────────────────────────── */
const EXAMPLE_QUERIES = [
    {
        short: 'TransContinental summary',
        full: 'Show summary about contract with TransContinental Corp',
    },
    {
        short: 'EU Pending contracts',
        full: 'Which contracts in the EU region are currently in Pending status and what are their risk scores?',
    },
    {
        short: 'France Data Privacy',
        full: 'Show me the Data Privacy related contracts in France and summarize their compliance requirements.',
    },
    {
        short: 'Asiatrade terms',
        full: 'What are the service agreement terms with Asiatrade Logistics?',
    },
]

/* ── Timeout (ms) for the fetch ───────────────────────────────────────────── */
const QUERY_TIMEOUT_MS = 90_000

export default function App() {
    const [query, setQuery] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)   // { answer, retrieved_chunks, structured_records }
    const [error, setError] = useState(null)

    const abortRef = useRef(null)

    /* ── Submit handler ─────────────────────────────────────────────────────── */
    const handleSubmit = useCallback(async () => {
        if (!query.trim() || loading) return

        // Cancel any previous in-flight request
        abortRef.current?.abort()
        const controller = new AbortController()
        abortRef.current = controller

        setLoading(true)
        setError(null)
        setResult(null)

        // Timeout guard
        const timeoutId = setTimeout(() => controller.abort(), QUERY_TIMEOUT_MS)

        try {
            const data = await postQuery(query.trim(), controller.signal)
            setResult(data)
        } catch (err) {
            if (err.name === 'AbortError') {
                setError('Request timed out or was cancelled. Please try again.')
            } else {
                setError(err.message || 'An unexpected error occurred.')
            }
        } finally {
            clearTimeout(timeoutId)
            setLoading(false)
        }
    }, [query, loading])

    /* ── Clear handler ──────────────────────────────────────────────────────── */
    const handleClear = () => {
        abortRef.current?.abort()
        setQuery('')
        setResult(null)
        setError(null)
        setLoading(false)
    }

    /* ── Key handler (Ctrl+Enter / Cmd+Enter submits) ───────────────────────── */
    const handleKeyDown = (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            handleSubmit()
        }
    }

    /* ── Fill example query ─────────────────────────────────────────────────── */
    const fillExample = (text) => {
        setQuery(text)
        setResult(null)
        setError(null)
    }

    const hasResult = result && !loading

    return (
        <div className="app">
            {/* ── Header ─────────────────────────────────────────────────────────── */}
            <header className="header">
                <div className="header-brand">
                    <span className="brand-icon" aria-hidden="true">⚖️</span>
                    <span className="brand-name">Comp-Check Bot</span>
                    <span className="brand-badge">RAG · LEGAL</span>
                </div>
                <div className="header-status">
                    <span className="status-dot" aria-hidden="true" />
                    <span>Live</span>
                </div>
            </header>

            {/* ── Main ───────────────────────────────────────────────────────────── */}
            <main className="main">

                {/* ── Query input ─────────────────────────────────────────────────── */}
                <section className="query-section" aria-label="Query input">
                    <h2>Ask a compliance question</h2>

                    <div className="query-input-wrapper">
                        <textarea
                            id="query-input"
                            className="query-input"
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="e.g. Show me the Data Privacy related contracts in France…"
                            disabled={loading}
                            rows={3}
                            aria-label="Compliance query"
                            autoFocus
                        />
                    </div>

                    <div className="query-actions">
                        {/* Example pills */}
                        <div className="example-hints">
                            <span>Try:</span>
                            {EXAMPLE_QUERIES.map(q => (
                                <button
                                    key={q.short}
                                    className="example-pill"
                                    onClick={() => fillExample(q.full)}
                                    disabled={loading}
                                    title={q.full}
                                >
                                    {q.short}
                                </button>
                            ))}
                        </div>

                        {/* Action buttons */}
                        <div className="button-group">
                            {(query || result || error) && (
                                <button
                                    id="clear-btn"
                                    className="btn btn-ghost"
                                    onClick={handleClear}
                                    disabled={false}
                                    title="Clear query and results"
                                >
                                    ✕ Clear
                                </button>
                            )}
                            <button
                                id="ask-btn"
                                className="btn btn-primary"
                                onClick={handleSubmit}
                                disabled={loading || !query.trim()}
                                title="Submit query (Ctrl+Enter)"
                            >
                                {loading ? (
                                    <>
                                        <span style={{ display: 'inline-block', width: 14, height: 14, border: '2px solid rgba(255,255,255,.4)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin .7s linear infinite' }} />
                                        Running…
                                    </>
                                ) : (
                                    <>⚡ Ask</>
                                )}
                            </button>
                        </div>
                    </div>
                </section>

                {/* ── Loading ─────────────────────────────────────────────────────── */}
                {loading && <LoadingCard />}

                {/* ── Error ───────────────────────────────────────────────────────── */}
                {error && !loading && <ErrorCard message={error} />}

                {/* ── Results ─────────────────────────────────────────────────────── */}
                {hasResult && (
                    <>
                        <AnswerCard answer={result.answer} />
                        <ChunksSection chunks={result.retrieved_chunks} />
                        <RecordsTable records={result.structured_records} />
                    </>
                )}

                {/* ── Welcome / empty state ────────────────────────────────────────── */}
                {!loading && !error && !result && (
                    <div className="welcome-card anim-in">
                        <span className="welcome-icon" role="img" aria-label="scales">⚖️</span>
                        <h2>Legal Contract Compliance Assistant</h2>
                        <p>
                            Ask natural-language questions about contracts, compliance scores, audit
                            statuses, regions, vendors, and policy clauses — powered by RAG.
                        </p>

                        <div className="example-queries-grid">
                            {EXAMPLE_QUERIES.map(q => (
                                <button
                                    key={q.short}
                                    className="example-query-card"
                                    onClick={() => fillExample(q.full)}
                                    title="Click to use this query"
                                >
                                    <div className="eq-label">Example</div>
                                    {q.full}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </main>

            {/* ── Footer ─────────────────────────────────────────────────────────── */}
            <footer className="footer">
                Comp-Check Bot · Powered by BGE-M3 · Milvus · Neon Postgres · Groq
            </footer>
        </div>
    )
}
