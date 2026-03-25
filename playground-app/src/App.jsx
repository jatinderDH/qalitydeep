import React, { useState, useCallback } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import Nav from './components/Nav'
import RequestBuilder from './components/RequestBuilder'
import RequestSection from './components/RequestSection'
import ResponseSection from './components/ResponseSection'

const defaultApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [apiUrl, setApiUrl] = useState(defaultApiUrl)
  const [apiKey, setApiKey] = useState('')
  const [metricCollection, setMetricCollection] = useState('default')
  const [metrics, setMetrics] = useState(['correctness', 'relevancy'])
  const [cases, setCases] = useState([
    { input: 'How tall is Mount Everest?', actualOutput: 'No clue, pretty tall I guess?', expectedOutput: '', name: 'case_1' }
  ])
  const [response, setResponse] = useState(null)
  const [sending, setSending] = useState(false)

  const payload = {
    metricCollection,
    metrics,
    llmTestCases: cases.map(({ input, actualOutput, expectedOutput, name }) => ({
      input,
      actualOutput,
      expectedOutput: expectedOutput || undefined,
      name: name || undefined
    }))
  }

  const sendRequest = useCallback(async () => {
    if (!apiKey.trim()) {
      setResponse({ status: 0, elapsed: 0, size: 0, data: { error: 'Enter API key in Headers' } })
      return
    }
    setSending(true)
    setResponse(null)
    const start = performance.now()
    try {
      const res = await fetch(`${apiUrl.replace(/\/$/, '')}/v1/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey.trim() },
        body: JSON.stringify(payload)
      })
      const elapsed = Math.round(performance.now() - start)
      const text = await res.text()
      let data
      try {
        data = JSON.parse(text)
      } catch {
        data = { raw: text }
      }
      setResponse({
        status: res.status,
        elapsed,
        size: new Blob([text]).size,
        data: res.ok ? data : { error: data.detail || data.error || text }
      })
    } catch (err) {
      setResponse({
        status: 0,
        elapsed: Math.round(performance.now() - start),
        size: 0,
        data: { error: err.message }
      })
    } finally {
      setSending(false)
    }
  }, [apiUrl, apiKey, payload])

  return (
    <div className="app">
      <header className="app-header">
        <span className="app-brand">QAlityDeep</span>
        <span className="app-header-doc">Evals API Playground</span>
      </header>
      <div className="url-bar">
        <span className="method-pill">POST</span>
        <input
          type="text"
          className="url-input"
          value={apiUrl}
          onChange={(e) => setApiUrl(e.target.value)}
          placeholder="https://api.example.com"
        />
        <button className="btn btn-primary btn-send" onClick={sendRequest} disabled={sending}>
          {sending ? 'Sending…' : 'Send request'}
        </button>
        <button type="button" className="icon-btn url-close" title="Clear">✕</button>
      </div>
      <div className="app-body">
        <PanelGroup direction="horizontal">
          <Panel defaultSize={18} minSize={12} maxSize={30} className="panel panel-nav">
            <Nav />
          </Panel>
          <PanelResizeHandle className="resize-handle" />
          <Panel defaultSize={42} minSize={25} className="panel panel-builder">
            <RequestBuilder
              apiKey={apiKey}
              setApiKey={setApiKey}
              metricCollection={metricCollection}
              setMetricCollection={setMetricCollection}
              metrics={metrics}
              setMetrics={setMetrics}
              cases={cases}
              setCases={setCases}
            />
          </Panel>
          <PanelResizeHandle className="resize-handle" />
          <Panel defaultSize={40} minSize={25} className="panel panel-viewer">
            <PanelGroup direction="vertical">
              <Panel defaultSize={50} minSize={20} className="panel panel-request">
                <RequestSection apiUrl={apiUrl} apiKey={apiKey} payload={payload} />
              </Panel>
              <PanelResizeHandle className="resize-handle resize-handle-vertical" />
              <Panel defaultSize={50} minSize={20} className="panel panel-response">
                <ResponseSection response={response} />
              </Panel>
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  )
}
