import { Rocket, Zap, DollarSign, Terminal, ArrowRight, Play } from 'lucide-react'

export default function Hero() {
  return (
    <section className="hero" id="home">
      <div className="hero-container">
        <div className="hero-badge">
          <Zap size={16} />
          <span>Open Source • Free • Self-Hosted</span>
        </div>

        <h1 className="hero-title">
          Use ChatGPT Without
          <span className="gradient-text"> Paying for API</span>
        </h1>

        <p className="hero-subtitle">
          Turn ChatGPT's web interface into a REST API. Build AI agents, automate workflows,
          and prototype ideas—all running locally on your machine. No monthly fees, no API limits.
        </p>

        <div className="hero-stats">
          <div className="stat">
            <div className="stat-value">$0</div>
            <div className="stat-label">Monthly Cost</div>
          </div>
          <div className="stat">
            <div className="stat-value">∞</div>
            <div className="stat-label">API Requests</div>
          </div>
          <div className="stat">
            <div className="stat-value">100%</div>
            <div className="stat-label">Local & Private</div>
          </div>
        </div>

        <div className="hero-cta">
          <button className="btn btn-primary">
            <Play size={18} />
            <span>Try Demo</span>
          </button>
          <button className="btn btn-secondary">
            <Terminal size={18} />
            <span>View on GitHub</span>
          </button>
        </div>

        <div className="hero-code">
          <div className="code-header">
            <div className="code-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="code-title">Quick Start</span>
          </div>
          <pre className="code-block">
            <code>{`# Install dependencies
pip install flask playwright

# Login once (saves session)
python3 manual_login.py

# Start API server
python3 chatgpt_api_server.py

# Make your first request
curl -X POST http://localhost:5001/chat \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "Hello, world!"}'`}</code>
          </pre>
        </div>
      </div>
    </section>
  )
}
