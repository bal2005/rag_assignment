// ErrorCard.jsx – clean error display
export default function ErrorCard({ message }) {
    return (
        <div className="error-card anim-in" role="alert">
            <span className="error-icon" aria-hidden="true">⛔</span>
            <div className="error-content">
                <h3>Query Failed</h3>
                <p>{message || 'An unexpected error occurred. Please try again.'}</p>
            </div>
        </div>
    )
}
