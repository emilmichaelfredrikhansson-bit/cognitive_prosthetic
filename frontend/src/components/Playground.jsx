import { useState } from 'react'
import axios from 'axios'
import { Send, Loader, CheckCircle2, XCircle, Play } from 'lucide-react'

export default function Playground() {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [serverStatus, setServerStatus] = useState('unknown')

  const checkServerStatus = async () => {
    try {
      const res = await axios.get('http://localhost:5001/health')
      setServerStatus(res.data.ready ? 'online' : 'starting')
      setError('')
    } catch (err) {
      setServerStatus('offline')
      setError('Server is not running. Start it with: python3 chatgpt_api_server.py')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!prompt.trim()) return

    setLoading(true)
    setError('')
    setResponse('')

    try {
      const res = await axios.post('http://localhost:5001/chat', {
        prompt: prompt.trim()
      }, {
        timeout: 120000 // 2 minute timeout
      })

      if (res.data.success) {
        setResponse(res.data.response)
      } else {
        setError(res.data.error || 'Unknown error occurred')
      }
    } catch (err) {
      if (err.code === 'ECONNREFUSED') {
        setError('Cannot connect to server. Make sure the API server is running on localhost:5001')
      } else if (err.code === 'ETIMEDOUT') {
        setError('Request timed out. The response may have taken too long.')
      } else {
        setError(err.response?.data?.error || err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  const examplePrompts = [
    "Explain quantum computing in simple terms",
    "Write a haiku about coding",
    "What's the difference between REST and GraphQL?",
    "Generate a Python function to calculate fibonacci"
  ]

  return (
    <section className="playground" id="demo">
      <div className="playground-container">
        <div className="playground-header">
          <h2 className="section-title">Try It Live</h2>
          <p className="section-subtitle">
            Test the API directly from your browser (requires local server running)
          </p>
        </div>

        <div className="playground-status">
          <button onClick={checkServerStatus} className="status-check-btn">
            Check Server Status
          </button>
          <div className={`status-indicator status-${serverStatus}`}>
            {serverStatus === 'online' && (
              <>
                <CheckCircle2 size={18} />
                <span>Server Online</span>
              </>
            )}
            {serverStatus === 'offline' && (
              <>
                <XCircle size={18} />
                <span>Server Offline</span>
              </>
            )}
            {serverStatus === 'starting' && (
              <>
                <Loader size={18} className="spin" />
                <span>Server Starting...</span>
              </>
            )}
            {serverStatus === 'unknown' && (
              <span>Status Unknown</span>
            )}
          </div>
        </div>

        <div className="playground-content">
          <div className="playground-input">
            <h3>Send a Prompt</h3>
            <form onSubmit={handleSubmit}>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter your prompt here... (e.g., 'Explain AI in simple terms')"
                rows={6}
                disabled={loading}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading || !prompt.trim()}
              >
                {loading ? (
                  <>
                    <Loader size={18} className="spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <Send size={18} />
                    <span>Send Request</span>
                  </>
                )}
              </button>
            </form>

            <div className="example-prompts">
              <span className="example-label">Try an example:</span>
              {examplePrompts.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setPrompt(ex)}
                  className="example-btn"
                  disabled={loading}
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>

          <div className="playground-output">
            <h3>Response</h3>
            {error && (
              <div className="error-message">
                <XCircle size={18} />
                <span>{error}</span>
              </div>
            )}
            {response && (
              <div className="response-box">
                <pre>{response}</pre>
              </div>
            )}
            {!response && !error && !loading && (
              <div className="response-placeholder">
                <Play size={48} />
                <p>Send a prompt to see the response here</p>
              </div>
            )}
            {loading && (
              <div className="response-placeholder">
                <Loader size={48} className="spin" />
                <p>Waiting for ChatGPT response...</p>
              </div>
            )}
          </div>
        </div>

        <div className="playground-note">
          <p>
            <strong>Note:</strong> The server must be running locally for this demo to work.
            Start it with <code>python3 chatgpt_api_server.py</code>
          </p>
        </div>
      </div>
    </section>
  )
}
