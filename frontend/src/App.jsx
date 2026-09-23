import { useState, useEffect, useRef, useCallback } from 'react'
import Tesseract from 'tesseract.js'

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
      <h3>AI-Understood Address <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, color: 'var(--text-muted)' }}>— parsed by <strong style={{ color: 'var(--text-secondary)' }}>{parserUsed === 'llm' ? 'AI (LLM)' : 'rule-based fallback'}</strong></span></h3>
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
// Screen: Camera Scanner
// ─────────────────────────────────────────────────────────────────────────────

function CameraScreen({ onCapture, onCancel }) {
  const videoRef = useRef(null)
  const fileInputRef = useRef(null)
  const [stream, setStream] = useState(null)
  const [error, setError] = useState('')
  const [loadingCamera, setLoadingCamera] = useState(true)
  const [cameraAttempt, setCameraAttempt] = useState(0)

  const stopStream = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }, [stream])

  useEffect(() => {
    let active = true
    let mediaStream = null

    async function startCamera() {
      setLoadingCamera(true)
      setError('')

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (active) {
          setError('This browser does not support camera access. Please upload an image instead.')
          setLoadingCamera(false)
        }
        return
      }

      if (window.location.protocol !== 'http:' && window.location.protocol !== 'https:') {
        if (active) {
          setError('Camera access requires a web page served over localhost or HTTPS. Please upload an image instead.')
          setLoadingCamera(false)
        }
        return
      }

      try {
        const permission = await navigator.permissions.query({ name: 'camera' })
        if (permission.state === 'denied') {
          if (active) {
            setError('Camera is blocked for this site in your browser. Allow Camera in the address-bar site settings, then click Try Camera Again.')
            setLoadingCamera(false)
          }
          return
        }
      } catch {
      }

      try {
        // Try back camera first on mobile
        try {
          mediaStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: 'environment' } }
          })
        } catch (e1) {
          // Fallback to any available camera (webcam, laptop camera, etc.)
          mediaStream = await navigator.mediaDevices.getUserMedia({
            video: true
          })
        }

        if (!active) {
          if (mediaStream) mediaStream.getTracks().forEach(t => t.stop())
          return
        }

        setStream(mediaStream)
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream
          videoRef.current.muted = true
          videoRef.current.play().catch(() => {})
        }
      } catch (err) {
        if (active) {
          setError('Camera permission was denied or no camera is available. You can upload an image instead.')
        }
      } finally {
        if (active) setLoadingCamera(false)
      }
    }

    startCamera()
    return () => {
      active = false
      if (mediaStream) mediaStream.getTracks().forEach(t => t.stop())
    }
  }, [cameraAttempt])

  const handleCapture = useCallback(() => {
    if (!videoRef.current) return
    const video = videoRef.current
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      setError('Camera is not ready yet. Please wait a moment or upload an image instead.')
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      setError('Unable to capture the camera frame. Please upload an image instead.')
      return
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    stopStream()
    onCapture(canvas.toDataURL('image/jpeg'))
  }, [onCapture, stopStream])

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (event) => {
      stopStream()
      onCapture(event.target.result)
    }
    reader.readAsDataURL(file)
  }

  const handleCancel = () => {
    stopStream()
    onCancel()
  }

  return (
    <div className="camera-card screen-enter">
      <h2 id="camera-title">Scan Postal Address</h2>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: 16 }}>
        Capture a live photo of the address label or upload an image file
      </p>

      <div className="video-container">
        {loadingCamera && (
          <div style={{ color: '#fff', padding: 40, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
            <div className="spinner" style={{ width: 32, height: 32, margin: 0 }} />
            <span>Accessing camera…</span>
          </div>
        )}
        {error ? (
          <div style={{ color: '#ff6b7a', padding: '36px 20px', background: 'rgba(255, 107, 122, 0.08)' }}>
            <div style={{ fontSize: '2rem', marginBottom: 8 }}>📷</div>
            <p style={{ fontWeight: 600, color: '#e84393' }}>{error}</p>
            <button
              type="button"
              className="btn-secondary"
              style={{ maxWidth: 260, margin: '18px auto 0' }}
              onClick={() => setCameraAttempt(attempt => attempt + 1)}
            >
              Try Camera Again
            </button>
          </div>
        ) : (
          <video ref={videoRef} className="video-feed" autoPlay playsInline muted />
        )}
      </div>

      <input
        type="file"
        ref={fileInputRef}
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      <div className="button-group" style={{ marginTop: 16 }}>
        {!error && (
          <button className="btn-primary" onClick={handleCapture} disabled={loadingCamera || !stream}>
            📸 Capture Photo
          </button>
        )}
        <button
          type="button"
          className="btn-secondary"
          onClick={() => fileInputRef.current?.click()}
        >
          📁 Upload Image File
        </button>
      </div>

      <button className="btn-cancel" onClick={handleCancel}>
        Cancel & Return
      </button>
    </div>
  )
}

function OCRLoadingScreen({ imageData }) {
  return (
    <div className="loading-card screen-enter" role="status" aria-live="polite">
      {imageData && (
        <img
          src={imageData}
          alt="Captured address"
          style={{ width: '100%', maxHeight: 280, objectFit: 'contain', borderRadius: 10, marginBottom: 18 }}
        />
      )}
      <div className="spinner" aria-hidden="true" />
      <p style={{ fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>Extracting address from image…</p>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>OCR is scanning postal text with AI…</p>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Screen: Input
// ─────────────────────────────────────────────────────────────────────────────

function InputScreen({ onSubmit, parserStatus, onOpenScanner, onUploadImage, initialText = '' }) {
  const [text, setText] = useState(initialText)
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (initialText) setText(initialText)
  }, [initialText])

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) { setError('Please enter an address.'); return }
    if (trimmed.length < 5) { setError('Address is too short. Add more details.'); return }
    setError('')
    onSubmit(trimmed)
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (event) => {
      onUploadImage(event.target.result)
    }
    reader.readAsDataURL(file)
  }

  return (
    <div className="input-card screen-enter">
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
        
        <input
          type="file"
          ref={fileInputRef}
          accept="image/*"
          capture="environment"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        <div className="button-group">
          <button
            type="button"
            className="btn-secondary"
            onClick={onOpenScanner}
            aria-label="Scan Address with Camera"
          >
            📷 Scan / Upload Image
          </button>
          <button
            type="submit"
            className="btn-primary"
            disabled={!text.trim()}
            aria-label="Find Post Office"
          >
            Find Post Office
          </button>
        </div>
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
      <p style={{ fontWeight: 600, marginBottom: 8 }}>Processing address…</p>
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
    <div className="screen-enter">
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
      <div style={{ marginBottom: 16, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
        Input: <em style={{ color: 'var(--text-secondary)' }}>"{input_address}"</em>
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
  const [screen, setScreen] = useState('input')
  const [result, setResult] = useState(null)
  const [parserStatus, setParserStatus] = useState(null)
  const [apiError, setApiError] = useState('')
  const [scannedText, setScannedText] = useState('')
  const [capturedImage, setCapturedImage] = useState('')

  useEffect(() => {
    fetch(`${API_BASE}/parser-status`)
      .then(r => r.json())
      .then(d => setParserStatus(d))
      .catch(() => setParserStatus({ parser: 'unknown' }))
  }, [])

  async function handleCapture(imageData) {
    setApiError('')
    setCapturedImage(imageData)
    setScreen('ocr-loading')
    try {
      const image = await loadImage(imageData)
      if (!hasUsableImageContent(image)) {
        throw new Error('The photo appears blank or too dark. Please point the camera at the address label and try again.')
      }
      const processedImage = preprocessForOcr(image)
      const [originalResult, processedResult] = await Promise.all([
        Tesseract.recognize(imageData, 'eng', { logger: () => {} }),
        Tesseract.recognize(processedImage, 'eng', { logger: () => {} }),
      ])
      const candidates = [originalResult, processedResult]
        .map(result => ({
          text: result.data.text.replace(/\s+/g, ' ').trim(),
          confidence: Number(result.data.confidence) || 0,
        }))
        .filter(candidate => isUsableOcr(candidate.text, candidate.confidence))
        .sort((a, b) => ocrScore(b) - ocrScore(a))
      if (!candidates[0]) {
        throw new Error('No clear address text was found. Please retake the photo with the label in focus.')
      }
      setScannedText(candidates[0].text)
      setScreen('input')
    } catch (err) {
      setApiError(err.message || 'Failed to extract readable text from image.')
      setScreen('input')
    }
  }

  function loadImage(imageData) {
    return new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => resolve(image)
      image.onerror = () => reject(new Error('The captured image could not be loaded. Please try again.'))
      image.src = imageData
    })
  }

  function preprocessForOcr(image) {
    const scale = Math.max(1, Math.min(3, 1800 / image.width))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(image.width * scale)
    canvas.height = Math.round(image.height * scale)
    const context = canvas.getContext('2d', { willReadFrequently: true })
    context.filter = 'grayscale(1) contrast(1.35)'
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/png')
  }

  function hasUsableImageContent(image) {
    const canvas = document.createElement('canvas')
    const size = 120
    canvas.width = size
    canvas.height = size
    const context = canvas.getContext('2d', { willReadFrequently: true })
    context.drawImage(image, 0, 0, size, size)
    const pixels = context.getImageData(0, 0, size, size).data
    let sum = 0
    let sumSquares = 0
    let minimum = 255
    let maximum = 0
    for (let index = 0; index < pixels.length; index += 4) {
      const brightness = (pixels[index] * 0.299) + (pixels[index + 1] * 0.587) + (pixels[index + 2] * 0.114)
      sum += brightness
      sumSquares += brightness * brightness
      minimum = Math.min(minimum, brightness)
      maximum = Math.max(maximum, brightness)
    }
    const count = pixels.length / 4
    const variance = (sumSquares / count) - ((sum / count) ** 2)
    return maximum - minimum >= 24 && variance >= 45
  }

  function isUsableOcr(text, confidence) {
    const words = text.match(/[A-Za-z]{2,}/g) || []
    const letters = (text.match(/[A-Za-z]/g) || []).length
    const usefulCharacters = (text.match(/[A-Za-z0-9 ,.-]/g) || []).length
    const hasPostalSignal = /\b\d{6}\b/.test(text) || words.length >= 3
    return confidence >= 35 && words.length >= 2 && hasPostalSignal && letters >= 8 && usefulCharacters / Math.max(text.length, 1) >= 0.55
  }

  function ocrScore(candidate) {
    const postalBonus = /\b\d{6}\b/.test(candidate.text) ? 25 : 0
    return candidate.confidence + postalBonus + Math.min(candidate.text.length, 100) / 10
  }

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
    setScannedText('')
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
        {screen === 'input'   && <InputScreen onSubmit={handleSubmit} parserStatus={parserStatus} onOpenScanner={() => setScreen('camera')} onUploadImage={handleCapture} initialText={scannedText} />}
        {screen === 'loading' && <LoadingScreen />}
        {screen === 'result'  && result && <ResultScreen data={result} onBack={handleBack} />}
        {screen === 'camera'  && <CameraScreen onCapture={handleCapture} onCancel={() => setScreen('input')} />}
        {screen === 'ocr-loading' && <OCRLoadingScreen imageData={capturedImage} />}
      </main>
    </div>
  )
}
