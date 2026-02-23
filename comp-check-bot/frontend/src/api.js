// api.js – all backend communication

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

/**
 * POST /api/v1/query
 * Sends a natural-language query to the RAG backend.
 *
 * @param {string} query
 * @param {AbortSignal} [signal]
 * @returns {Promise<{answer:string, retrieved_chunks:Array, structured_records:Array}>}
 */
export async function postQuery(query, signal) {
    const url = `${API_BASE}/api/v1/query`

    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
        signal,
    })

    if (!response.ok) {
        let detail = `HTTP ${response.status} – ${response.statusText}`
        try {
            const err = await response.json()
            detail = err.detail || detail
        } catch (_) { }
        throw new Error(detail)
    }

    return response.json()
}

/**
 * GET /api/v1/health
 * Quick health check.
 */
export async function getHealth() {
    const url = `${API_BASE}/api/v1/health`
    const res = await fetch(url)
    if (!res.ok) throw new Error('Backend unreachable')
    return res.json()
}
