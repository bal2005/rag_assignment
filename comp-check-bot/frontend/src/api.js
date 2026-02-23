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

    let response
    try {
        response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
            signal,
        })
    } catch (networkErr) {
        // AbortError or network failure (e.g. Render cold start, CORS block)
        if (networkErr.name === 'AbortError') throw networkErr
        throw new Error(
            `Network error – could not reach the backend. ` +
            `Is it deployed and running? (${networkErr.message})`
        )
    }

    // Try to parse the body as JSON regardless of status, for error detail
    let body = null
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
        try {
            body = await response.json()
        } catch (_) {
            body = null
        }
    } else {
        // Non-JSON body (e.g. Render 502 HTML page or empty body)
        const text = await response.text().catch(() => '')
        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status} – Backend returned a non-JSON response. ` +
                (text ? text.slice(0, 200) : response.statusText)
            )
        }
    }

    if (!response.ok) {
        const detail =
            (body && (body.detail || body.message)) ||
            `HTTP ${response.status} – ${response.statusText}`
        throw new Error(detail)
    }

    if (!body) {
        throw new Error('Backend returned an empty response body.')
    }

    return body
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
