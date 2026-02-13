import { Download, LogIn, Rocket, MessageSquare } from 'lucide-react'

const steps = [
  {
    icon: <Download />,
    title: 'Install',
    description: 'Clone the repo and install dependencies with pip',
    code: 'pip install flask playwright',
    number: '01'
  },
  {
    icon: <LogIn />,
    title: 'Login',
    description: 'Run setup script once to save your ChatGPT session',
    code: 'python3 manual_login.py',
    number: '02'
  },
  {
    icon: <Rocket />,
    title: 'Launch',
    description: 'Start the API server on localhost:5001',
    code: 'python3 chatgpt_api_server.py',
    number: '03'
  },
  {
    icon: <MessageSquare />,
    title: 'Use',
    description: 'Send requests from any app or script',
    code: 'curl -X POST http://localhost:5001/chat',
    number: '04'
  }
]

export default function HowItWorks() {
  return (
    <section className="how-it-works" id="how-it-works">
      <div className="how-container">
        <div className="how-header">
          <h2 className="section-title">How It Works</h2>
          <p className="section-subtitle">
            Get up and running in under 5 minutes
          </p>
        </div>

        <div className="steps-container">
          {steps.map((step, index) => (
            <div key={index} className="step-card">
              <div className="step-number">{step.number}</div>
              <div className="step-icon">{step.icon}</div>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-description">{step.description}</p>
              <div className="step-code">
                <code>{step.code}</code>
              </div>
              {index < steps.length - 1 && <div className="step-arrow">→</div>}
            </div>
          ))}
        </div>

        <div className="how-diagram">
          <div className="diagram-card">
            <h3>Architecture</h3>
            <div className="diagram-flow">
              <div className="diagram-node">
                <span className="node-title">Your App</span>
                <span className="node-desc">Python, JS, any language</span>
              </div>
              <div className="diagram-arrow">→</div>
              <div className="diagram-node">
                <span className="node-title">Local API</span>
                <span className="node-desc">Flask Server (Port 5001)</span>
              </div>
              <div className="diagram-arrow">→</div>
              <div className="diagram-node">
                <span className="node-title">Playwright</span>
                <span className="node-desc">Browser Automation</span>
              </div>
              <div className="diagram-arrow">→</div>
              <div className="diagram-node">
                <span className="node-title">ChatGPT</span>
                <span className="node-desc">Web Interface</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
