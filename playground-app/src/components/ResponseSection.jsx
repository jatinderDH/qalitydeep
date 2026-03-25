import React, { useState, useCallback } from 'react'

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).catch(() => {})
}

export default function ResponseSection({ response }) {
  const [expanded, setExpanded] = useState(true)
  const copyResponse = useCallback(() => {
    if (response?.data) copyToClipboard(JSON.stringify(response.data, null, 2))
  }, [response])

  return (
    <>
      <div className="section-title">RESPONSE</div>
      {response ? (
        <>
          <div className="response-meta">
            <span className={response.status >= 200 && response.status < 300 ? 'status-ok' : 'status-err'}>
              status: {response.status}
            </span>
            <span>time: {response.elapsed} ms</span>
            <span>size: {response.size}b</span>
          </div>
          <div className="viewer-toolbar">
            <button
              type="button"
              className="icon-btn"
              onClick={() => setExpanded(!expanded)}
              title={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? '▼' : '▶'} View full response
            </button>
            <button type="button" className="icon-btn" onClick={copyResponse} title="Copy">⎘ Copy</button>
          </div>
          {expanded && (
            <pre className="code-block response-expanded">
              {JSON.stringify(response.data, null, 2)}
            </pre>
          )}
        </>
      ) : (
        <div className="code-block response-placeholder">
          <p style={{ color: '#666', margin: 0, textAlign: 'center' }}>No response yet.</p>
          <p style={{ color: '#555', fontSize: '0.85rem', margin: '0.5rem 0 0', textAlign: 'center' }}>
            Click <strong>Send request</strong> in the bar above to see the JSON response here.
          </p>
        </div>
      )}
    </>
  )
}
