import { useState } from 'react'
import './App.css'
import { Terminal, Send, Loader, CheckCircle2, XCircle, Github, Code2, Zap } from 'lucide-react'
import axios from 'axios'

function App() {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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
        timeout: 120000
      })

      if (res.data.success) {
        setResponse(res.data.response)
      } else {
        setError(res.data.error || 'Unknown error')
      }
    } catch (err) {
      if (err.code === 'ECONNREFUSED') {
        setError('Server not running. Start it with: python3 chatgpt_api_server.py')
      } else {
        setError(err.response?.data?.error || err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <Terminal size={32} />
            <h1>ChatGPT Local API</h1>
          </div>
          <a href="https://github.com" className="github-btn" target="_blank" rel="noopener noreferrer">
            <Github size={20} />
            <span>GitHub</span>
          </a>
        </div>
      </header>

      {/* Hero */}
      <section className="hero">
        <div className="gradient-orb orb-1"></div>
        <div className="gradient-orb orb-2"></div>

        <h2 className="hero-title">
          I built this because <span className="gradient-text">I couldn't afford the API</span>
        </h2>

        <p className="hero-subtitle">
          If you're like me—building AI agents, experimenting with automation, or just learning—you've hit the wall of API costs.
          <strong> $20-200/month adds up fast.</strong>
        </p>

        <p className="hero-subtitle">
          So I built this. It turns ChatGPT's web interface into a REST API running on your machine.
          <strong> Free. Local. Unlimited.</strong>
        </p>

        <div className="stats">
          <div className="stat">
            <div className="stat-value">$0</div>
            <div className="stat-label">Monthly Cost</div>
          </div>
          <div className="stat">
            <div className="stat-value">∞</div>
            <div className="stat-label">Requests</div>
          </div>
          <div className="stat">
            <div className="stat-value">100%</div>
            <div className="stat-label">Local</div>
          </div>
        </div>
      </section>

      {/* Why */}
      <section className="section">
        <h3 className="section-title">Why This Exists</h3>
        <div className="reason-grid">
          <div className="reason-card">
            <Zap className="reason-icon" />
            <h4>API Costs Kill Side Projects</h4>
            <p>At $0.03/1K tokens for GPT-4, a simple chatbot costs $100+/month. That's unsustainable for indie builders.</p>
          </div>
          <div className="reason-card">
            <Code2 className="reason-icon" />
            <h4>I Wanted to Experiment</h4>
            <p>Building AI agents means lots of trial and error. Token counting made me hesitant to iterate.</p>
          </div>
          <div className="reason-card">
            <CheckCircle2 className="reason-icon" />
            <h4>You Already Pay for ChatGPT</h4>
            <p>If you have a ChatGPT account, why pay twice? Use what you're already subscribed to.</p>
          </div>
        </div>
      </section>

      {/* Try It */}
      <section className="section demo-section">
        <h3 className="section-title">Try It Right Now</h3>
        <p className="section-subtitle">This connects to your local API server on port 5001</p>

        <div className="demo-container">
          <div className="demo-input">
            <form onSubmit={handleSubmit}>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask anything... (Make sure your server is running)"
                rows={6}
                disabled={loading}
              />
              <button
                type="submit"
                className="btn-primary"
                disabled={loading || !prompt.trim()}
              >
                {loading ? (
                  <>
                    <Loader size={20} className="spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <Send size={20} />
                    <span>Send</span>
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="demo-output">
            {error && (
              <div className="error">
                <XCircle size={20} />
                <p>{error}</p>
              </div>
            )}
            {response && (
              <div className="response">
                <CheckCircle2 size={20} className="success-icon" />
                <pre>{response}</pre>
              </div>
            )}
            {!response && !error && !loading && (
              <div className="placeholder">
                <Terminal size={48} />
                <p>Response will appear here</p>
              </div>
            )}
            {loading && (
              <div className="placeholder">
                <Loader size={48} className="spin" />
                <p>Waiting for ChatGPT...</p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Setup */}
      <section className="section">
        <h3 className="section-title">How to Use This</h3>
        <div className="setup-steps">
          <div className="step">
            <div className="step-number">1</div>
            <div className="step-content">
              <h4>Install Dependencies</h4>
              <code>pip install flask playwright flask-cors</code>
              <code>playwright install chromium</code>
            </div>
          </div>

          <div className="step">
            <div className="step-number">2</div>
            <div className="step-content">
              <h4>Login Once</h4>
              <code>python3 manual_login.py</code>
              <p>This saves your ChatGPT session</p>
            </div>
          </div>

          <div className="step">
            <div className="step-number">3</div>
            <div className="step-content">
              <h4>Start Server</h4>
              <code>python3 chatgpt_api_server.py</code>
              <p>Runs on http://localhost:5001</p>
            </div>
          </div>

          <div className="step">
            <div className="step-number">4</div>
            <div className="step-content">
              <h4>Use It</h4>
              <code>curl -X POST http://localhost:5001/chat \<br/>  -d '&#123;"prompt": "Hello!"&#125;'</code>
            </div>
          </div>
        </div>
      </section>

      {/* Code */}
      <section className="section">
        <h3 className="section-title">Use It From Any Language</h3>
        <div className="code-examples">
          <div className="code-example">
            <div className="code-header">Python</div>
            <pre className="code-block">{`import requests

response = requests.post(
    'http://localhost:5001/chat',
    json={"prompt": "What is AI?"}
)
print(response.json()['response'])`}</pre>
          </div>

          <div className="code-example">
            <div className="code-header">JavaScript</div>
            <pre className="code-block">{`const response = await fetch(
  'http://localhost:5001/chat',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      prompt: "What is AI?"
    })
  }
);
const data = await response.json();
console.log(data.response);`}</pre>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <p>Made for builders who can't afford API costs</p>
        <p>Open source • MIT License • Not affiliated with OpenAI</p>
      </footer>
    </div>
  )
}

export default App
