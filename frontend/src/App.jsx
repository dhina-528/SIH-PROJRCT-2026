import { useState, useEffect } from 'react'

const API_BASE = '' // empty = same origin; Vite proxy routes to localhost:8000

const EXAMPLE_ADDRESSES = [
  'near KGiSL college, Saravanampatti, Coimbatore, Tamil Nadu',
  'saravanampatty cbe tn',
  'Anna Nagar, Chennai, Tamil Nadu',
  'Saravanampatti, Coimbatore, 641035',
  'Saravanampatti, Coimbatore, 641001',  // wrong PIN demo
  'peelamedu tamilnadu',
  'RS Puram CBE TamilNadu 641002',
]

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function ConfidenceBadge({ level }) {
  const icons = { high: '●', medium: '◑', low: '○' }
  return (
    <span className={`confidence-badge ${level}`}>
      <span className="confidence-dot" />
      {level} confidence
    </span>
  )
}

function ScoreBar({ score, level }) {
  return (
    <div className="score-bar-wrap">
      <div className="score-label">
        <span>Matching Confidence (heuristic score)</span>
        <span>{score}%</span>
      </div>
      <div className="score-bar">
        <div
          className={`score-fill ${level}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  )
}

function NormalizedAddressCard({ norm, parserUsed }) {
  const fields = [
    { label: 'Landmark', value: norm.landmark },
    { label: 'Locality',  value: norm.locality },
    { label: 'City',      value: norm.city },
    { label: 'District',  value: norm.district },
    { label: 'State',     value: norm.state },
    { label: 'PIN',       value: norm.pincode },
  ]
  return (
    <div className="normalized-card">
      <h3>AI-Understood Address <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>— parsed by <strong>{parserUsed === 'llm' ? 'AI (LLM)' : 'rule-based fallback'}</strong></span></h3>
      <div className="normalized-grid">
        {fields.map(f => (
          <div className="norm-field" key={f.label}>
            <span className="nf-label">{f.label}</span>
            {f.value
              ? <span className="nf-value">{f.value}</span>
              : <span className="nf-null">—</span>
            }
          </div>
        ))}
      </div>
    </div>
  )
}

function AltCard({ alt }) {
  return (
    <div className="alt-card">
      <div className="alt-office">{alt.post_office}</div>
      <div className="alt-pin">{alt.pincode}</div>
      <div className="alt-meta">{alt.district}, {alt.state}</div>
      {alt.office_type && <div className="alt-meta" style={{ marginTop: 2 }}>{alt.office_type}</div>}
      <div className="alt-score">
        <ScoreBar score={alt.confidence} level={
          alt.confidence >= 80 ? 'high' : alt.confidence >= 60 ? 'medium' : 'low'
        } />
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Screen: Input
// ─────────────────────────────────────────────────────────────────────────────

function InputScreen({ onSubmit, parserStatus }) {
  const [text, setText] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) { setError('Please enter an address.'); return }
    if (trimmed.length < 5) { setError('Address is too short. Add more details.'); return }
    setError('')
    onSubmit(trimmed)
  }

  return (
    <div className="input-card">
      <form onSubmit={handleSubmit}>
        <label htmlFor="address-input">
          Enter a postal address — complete, partial, or messy
        </label>
        <textarea
          id="address-input"
          value={text}
          onChange={e => { setText(e.target.value); setError('') }}
          placeholder="e.g. near KGiSL college, Saravanampatti, Coimbatore, Tamil Nadu"
          aria-label="Postal address input"
          aria-describedby={error ? 'address-error' : undefined}
        />
        {error && (
          <div className="input-error" id="address-error" role="alert">
            {error}
          </div>
        )}
        <button
          type="submit"
          className="btn-primary"
          disabled={!text.trim()}
          aria-label="Find Post Office"
        >
          Find Post Office
        </button>
      </form>

      <div className="examples" aria-label="Example addresses">
        <p>Try an example</p>
        <div className="example-chips" role="list">
          {EXAMPLE_ADDRESSES.map(addr => (
            <button
              key={addr}
              className="chip"
              onClick={() => { setText(addr); setError('') }}
              role="listitem"
              aria-label={`Use example: ${addr}`}
            >
              {addr.length > 45 ? addr.slice(0, 44) + '…' : addr}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Screen: Loading
// ─────────────────────────────────────────────────────────────────────────────

function LoadingScreen() {
  return (
    <div className="loading-card" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p style={{ fontWeight: 600, color: '#333', marginBottom: 8 }}>Processing address…</p>
      <ul className="loading-steps" aria-label="Processing steps">
        <li>🧠 Understanding address…</li>
        <li>🔍 Searching postal records…</li>
        <li>📊 Ranking possible matches…</li>
      </ul>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Screen: Result
// ─────────────────────────────────────────────────────────────────────────────

function ResultScreen({ data, onBack }) {
  const { input_address, normalized_address, parser_used,
          result, confidence_level, explanation,
          alternatives, warning, needs_more_info, prompt_fields } = data

  return (
    <div>
      <div className="result-header">
        <h2>Results</h2>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <ConfidenceBadge level={confidence_level} />
          <button className="btn-back" onClick={onBack} aria-label="Search again">
            ← Search Again
          </button>
        </div>
      </div>

      {/* Input echo */}
      <div style={{ marginBottom: 16, fontSize: '0.85rem', color: '#888' }}>
        Input: <em style={{ color: '#444' }}>"{input_address}"</em>
      </div>

      {/* Normalized address — the AI Understanding step */}
      <NormalizedAddressCard norm={normalized_address} parserUsed={parser_used} />

      {/* Warning: wrong PIN */}
      {warning && (
        <div className="warning-card" role="alert" aria-label="PIN mismatch warning">
          <span className="warn-icon">⚠️</span>
          <div>
            <strong>PIN Code Mismatch</strong>
            <p style={{ marginTop: 4 }}>{warning}</p>
          </div>
        </div>
      )}

      {/* LOW confidence — no confident recommendation */}
      {needs_more_info && (
        <div className="low-card" role="alert">
          <h3>🔍 More Information Needed</h3>
          <p>
            We couldn't identify a Post Office with enough confidence from this address.
            Please provide more details:
          </p>
          {prompt_fields?.length > 0 && (
            <ul className="prompt-fields" aria-label="Missing address fields">
              {prompt_fields.map(f => <li key={f}>{f}</li>)}
            </ul>
          )}
        </div>
      )}

      {/* HIGH / MEDIUM — best result */}
      {result && (
        <div className="best-result-card" aria-label="Best matching post office">
          <div className="office-name">📮 {result.post_office}</div>
          <div className="pin-code">{result.pincode}</div>
          <div className="meta-row">
            <div className="meta-item">🏛 <strong>{result.district}</strong></div>
            <div className="meta-item">📍 {result.state}</div>
            {result.office_type && (
              <div className="meta-item">🏷 {result.office_type}</div>
            )}
          </div>
          <ScoreBar score={result.confidence} level={confidence_level} />
        </div>
      )}

      {/* Explanation */}
      {explanation?.length > 0 && (
        <div className="explanation-card">
          <h3>Why was this selected?</h3>
          <ul className="explanation-list" aria-label="Match explanation">
            {explanation.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Alternatives */}
      {alternatives?.length > 0 && (
        <div>
          <div className="section-title">
            {confidence_level === 'medium'
              ? 'Other possible matches — please verify'
              : 'Possible candidates'}
          </div>
          <div className="alt-grid" role="list" aria-label="Alternative post offices">
            {alternatives.map((alt, i) => (
              <AltCard key={i} alt={alt} />
            ))}
          </div>
        </div>
      )}

      {/* Data disclaimer */}
      <div className="data-note" role="note">
        ⚠ This is a <strong>prototype system</strong> using a small demo dataset.
        Results may not reflect the actual India Post network.
        Confidence scores are heuristic matching scores, not guaranteed accuracy.
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main App
// ─────────────────────────────────────────────────────────────────────────────

export default function App() {
  const [screen, setScreen] = useState('input')   // 'input' | 'loading' | 'result'
  const [result, setResult] = useState(null)
  const [parserStatus, setParserStatus] = useState(null)
  const [apiError, setApiError] = useState('')

  // Fetch parser status on mount
  useEffect(() => {
    fetch(`${API_BASE}/parser-status`)
      .then(r => r.json())
      .then(d => setParserStatus(d))
      .catch(() => setParserStatus({ parser: 'unknown' }))
  }, [])

  async function handleSubmit(address) {
    setApiError('')
    setScreen('loading')
    try {
      const res = await fetch(`${API_BASE}/find-post-office`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Server error (${res.status})`)
      }
      const data = await res.json()
      setResult(data)
      setScreen('result')
    } catch (err) {
      setApiError(err.message || 'Could not connect to the backend. Is it running?')
      setScreen('input')
    }
  }

  function handleBack() {
    setResult(null)
    setApiError('')
    setScreen('input')
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="logo-line">
          <span className="logo-icon" aria-hidden="true">📮</span>
          <h1>AI Post Office Identifier</h1>
        </div>
        <p>Enter any Indian postal address — complete, partial, or messy</p>
        {parserStatus && (
          <div>
            <span
              className={`parser-badge ${parserStatus.parser === 'llm' ? 'llm' : 'fallback'}`}
              title={parserStatus.description}
            >
              {parserStatus.parser === 'llm'
                ? '🤖 AI Parser Active'
                : '⚙️ Rule-based Parser Active'}
            </span>
          </div>
        )}
      </header>

      {/* API error banner */}
      {apiError && (
        <div className="input-error" role="alert" style={{ marginBottom: 16 }}>
          ⚠ {apiError}
        </div>
      )}

      {/* Screens */}
      <main>
        {screen === 'input'   && <InputScreen   onSubmit={handleSubmit} parserStatus={parserStatus} />}
        {screen === 'loading' && <LoadingScreen />}
        {screen === 'result'  && result && <ResultScreen data={result} onBack={handleBack} />}
      </main>
    </div>
  )
}
