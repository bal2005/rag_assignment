// AnswerCard.jsx – renders the LLM-generated markdown answer
//
// Uses:
//   remark-gfm   → GitHub Flavored Markdown: tables, strikethrough, checkboxes
//   rehype-raw   → Allows raw HTML inside markdown (e.g. <br> in table cells)
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

export default function AnswerCard({ answer }) {
    const [copied, setCopied] = useState(false)

    const handleCopy = async () => {
        await navigator.clipboard.writeText(answer)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div className="answer-card anim-in">
            <div className="card-header">
                <div className="card-title">
                    <span className="card-icon blue" aria-hidden="true">💡</span>
                    AI Answer
                </div>
                <button
                    id="copy-answer-btn"
                    className={`copy-btn${copied ? ' copied' : ''}`}
                    onClick={handleCopy}
                    title="Copy answer to clipboard"
                >
                    {copied ? '✓ Copied' : '⧉ Copy'}
                </button>
            </div>

            <div className="answer-content">
                <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeRaw]}
                >
                    {answer}
                </ReactMarkdown>
            </div>
        </div>
    )
}
