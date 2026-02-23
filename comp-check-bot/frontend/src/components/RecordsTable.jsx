// RecordsTable.jsx – renders Postgres contract records as a styled table
export default function RecordsTable({ records }) {
    if (!records || records.length === 0) return null

    return (
        <div className="records-card anim-in">
            <div className="records-header">
                <span
                    style={{
                        width: 32, height: 32, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 16, borderRadius: 6, background: '#FFFBEB'
                    }}
                >🗃️</span>
                <span style={{ fontWeight: 700, fontSize: 15 }}>Matching Contract Records</span>
                <span className="chunk-count-badge">{records.length} record{records.length !== 1 ? 's' : ''}</span>
            </div>

            <div className="table-wrapper">
                <table className="records-table" aria-label="Contract records">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Vendor</th>
                            <th>Type</th>
                            <th>Region</th>
                            <th>Jurisdiction</th>
                            <th>Policy</th>
                            <th>Score</th>
                            <th>Status</th>
                            <th>Duration</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {records.map((rec) => (
                            <RecordRow key={rec.contract_id} rec={rec} />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

function statusClass(status) {
    const s = (status || '').toLowerCase()
    if (s === 'passed') return 'passed'
    if (s === 'failed') return 'failed'
    return 'pending'
}

function scoreColor(score) {
    if (score >= 85) return '#22C55E'
    if (score >= 70) return '#F59E0B'
    return '#EF4444'
}

function RecordRow({ rec }) {
    const sc = rec.compliance_score
    const fill = scoreColor(sc)

    return (
        <tr id={`record-row-${rec.contract_id}`}>
            <td><span className="contract-id-tag">#{rec.contract_id}</span></td>
            <td style={{ fontWeight: 600 }}>{rec.vendor_name}</td>
            <td>{rec.contract_type}</td>
            <td>{rec.region}</td>
            <td>{rec.jurisdiction}</td>
            <td style={{ fontSize: 12 }}>{rec.policy_name}</td>
            <td>
                <div className="score-bar-cell">
                    <div className="score-bar-bg">
                        <div className="score-bar-fill" style={{ width: `${sc}%`, background: fill }} />
                    </div>
                    <span className="score-val" style={{ color: fill }}>{sc}</span>
                </div>
            </td>
            <td>
                <span className={`status-pill ${statusClass(rec.audit_status)}`}>
                    {statusClass(rec.audit_status) === 'passed' && '✓ '}
                    {statusClass(rec.audit_status) === 'failed' && '✕ '}
                    {statusClass(rec.audit_status) === 'pending' && '⏳ '}
                    {rec.audit_status}
                </span>
            </td>
            <td>{rec.duration_months}mo</td>
            <td style={{ fontSize: 12, color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                {rec.contract_date}
            </td>
        </tr>
    )
}
