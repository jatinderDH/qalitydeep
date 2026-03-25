import React, { useState, useCallback } from 'react'

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).catch(() => {})
}

function genCurl(apiUrl, apiKey, payload) {
  const url = `${apiUrl.replace(/\/$/, '')}/v1/evaluate`
  const key = apiKey || '<API-KEY>'
  const body = JSON.stringify(payload, null, 2).replace(/'/g, "'\\''")
  return `curl -X POST "${url}" \\
  -H "X-API-Key: ${key}" \\
  -H "Content-Type: application/json" \\
  -d '${body}'`
}

function genTypescript(apiUrl, apiKey, payload) {
  const url = `${apiUrl.replace(/\/$/, '')}/v1/evaluate`
  const key = apiKey || '<API-KEY>'
  return `const payload = ${JSON.stringify(payload)};
const response = await fetch("${url}", {
  method: "POST",
  headers: {
    "X-API-Key": "${key}",
    "Content-Type": "application/json",
  },
  body: JSON.stringify(payload),
});
const data = await response.json();`
}

function genPython(apiUrl, apiKey, payload) {
  const url = `${apiUrl.replace(/\/$/, '')}/v1/evaluate`
  const key = apiKey || '<API-KEY>'
  const payloadStr = JSON.stringify(payload).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, ' ')
  return `import requests
import json

payload = json.loads('${payloadStr}')
response = requests.post(
    "${url}",
    headers={"X-API-Key": "${key}", "Content-Type": "application/json"},
    json=payload,
)
data = response.json()`
}

export default function RequestSection({ apiUrl, apiKey, payload }) {
  const [requestTab, setRequestTab] = useState('curl')
  const requestCode = {
    curl: genCurl(apiUrl, apiKey, payload),
    ts: genTypescript(apiUrl, apiKey, payload),
    py: genPython(apiUrl, apiKey, payload)
  }[requestTab]
  const copyRequest = useCallback(() => copyToClipboard(requestCode), [requestCode])

  return (
    <>
      <div className="section-title">REQUEST</div>
      <div className="tabs">
        {['curl', 'ts', 'py'].map((t) => (
          <button
            key={t}
            type="button"
            className={`tab ${requestTab === t ? 'active' : ''}`}
            onClick={() => setRequestTab(t)}
          >
            {t === 'curl' ? 'cURL' : t === 'ts' ? 'TypeScript' : 'Python'}
          </button>
        ))}
      </div>
      <div className="viewer-toolbar">
        <span className="viewer-title" />
        <div className="viewer-actions">
          <button type="button" className="icon-btn" onClick={copyRequest} title="Copy">⎘ Copy</button>
        </div>
      </div>
      <pre className="code-block">{requestCode}</pre>
    </>
  )
}
