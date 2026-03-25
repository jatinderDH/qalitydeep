import React from 'react'

const METRIC_OPTS = ['correctness', 'relevancy', 'hallucination']

export default function RequestBuilder({
  apiKey,
  setApiKey,
  metricCollection,
  setMetricCollection,
  metrics,
  setMetrics,
  cases,
  setCases
}) {
  const updateCase = (i, field, value) => {
    const next = [...cases]
    next[i] = { ...next[i], [field]: value }
    setCases(next)
  }
  const addCase = () => {
    setCases([...cases, { input: '', actualOutput: '', expectedOutput: '', name: `case_${cases.length + 1}` }])
  }
  const removeCase = (i) => {
    if (cases.length <= 1) return
    setCases(cases.filter((_, j) => j !== i))
  }

  return (
    <>
      <div className="section-title">Headers</div>
      <div className="label">X-API-Key <span>(required)</span></div>
      <input
        type="password"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        placeholder="qd_... or &lt;API-KEY&gt;"
      />

      <div className="section-title">Body parameters</div>
      <div className="label">metricCollection <span>(required)</span></div>
      <input
        value={metricCollection}
        onChange={(e) => setMetricCollection(e.target.value)}
        placeholder="Collection Name"
      />

      <div className="label">metrics</div>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {METRIC_OPTS.map((m) => (
          <label key={m} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <input
              type="checkbox"
              checked={metrics.includes(m)}
              onChange={(e) => setMetrics(e.target.checked ? [...metrics, m] : metrics.filter((x) => x !== m))}
            />
            {m}
          </label>
        ))}
      </div>

      <div className="label">llmTestCases (list)</div>
      {cases.map((c, i) => (
        <div key={i} className="case-item">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4>Item {i + 1}</h4>
            {cases.length > 1 && (
              <button type="button" className="icon-btn" onClick={() => removeCase(i)} title="Remove">✕</button>
            )}
          </div>
          <div className="label">input *</div>
          <textarea value={c.input} onChange={(e) => updateCase(i, 'input', e.target.value)} placeholder="LLM input" />
          <div className="label">actualOutput *</div>
          <textarea value={c.actualOutput} onChange={(e) => updateCase(i, 'actualOutput', e.target.value)} placeholder="LLM output" />
          <div className="label">expectedOutput (optional)</div>
          <input value={c.expectedOutput} onChange={(e) => updateCase(i, 'expectedOutput', e.target.value)} />
          <div className="label">name (optional)</div>
          <input value={c.name} onChange={(e) => updateCase(i, 'name', e.target.value)} />
        </div>
      ))}
      <button type="button" className="btn btn-secondary add-case" onClick={addCase}>+ Add item</button>
    </>
  )
}
