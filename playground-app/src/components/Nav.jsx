import React from 'react'

export default function Nav() {
  return (
    <>
      <div className="nav-section">Evaluation</div>
      <div className="nav-item active">POST Run LLM Evals</div>
      <p style={{ marginTop: '1rem', fontSize: '0.8rem', color: '#666' }}>
        Configure request in the middle panel →
      </p>
    </>
  )
}
