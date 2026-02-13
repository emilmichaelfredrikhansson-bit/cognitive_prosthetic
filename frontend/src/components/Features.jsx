import {
  Zap,
  Shield,
  Code,
  Lock,
  Repeat,
  Terminal,
  Cpu,
  Globe,
  CheckCircle2
} from 'lucide-react'

const features = [
  {
    icon: <Zap />,
    title: 'Zero Monthly Costs',
    description: 'No API fees. Use your existing ChatGPT account. Perfect for bootstrappers and builders.',
    color: '#fbbf24'
  },
  {
    icon: <Shield />,
    title: 'Fully Local',
    description: 'Runs entirely on your machine. Your data never leaves your computer. Complete privacy.',
    color: '#34d399'
  },
  {
    icon: <Code />,
    title: 'REST API',
    description: 'Standard HTTP endpoints. Works with any programming language or HTTP client.',
    color: '#60a5fa'
  },
  {
    icon: <Repeat />,
    title: 'Persistent Sessions',
    description: 'Login once, use forever. Browser profile persists your ChatGPT session automatically.',
    color: '#a78bfa'
  },
  {
    icon: <Terminal />,
    title: 'Thread-Safe',
    description: 'Handle multiple requests safely. Built with proper async architecture for reliability.',
    color: '#f87171'
  },
  {
    icon: <Cpu />,
    title: 'Smart Response Detection',
    description: 'Automatically waits for complete responses. Handles long outputs and streaming.',
    color: '#fb923c'
  },
  {
    icon: <Globe />,
    title: 'Any Platform',
    description: 'Works on macOS, Linux, and Windows. Cross-platform browser automation.',
    color: '#22d3ee'
  },
  {
    icon: <Lock />,
    title: 'No Tracking',
    description: 'Zero analytics, zero telemetry. Your usage data stays 100% private on your machine.',
    color: '#c084fc'
  }
]

export default function Features() {
  return (
    <section className="features" id="features">
      <div className="features-container">
        <div className="features-header">
          <h2 className="section-title">Why Choose Local API?</h2>
          <p className="section-subtitle">
            Everything you need to build AI-powered applications without breaking the bank
          </p>
        </div>

        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-card">
              <div className="feature-icon" style={{ backgroundColor: `${feature.color}20`, color: feature.color }}>
                {feature.icon}
              </div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
            </div>
          ))}
        </div>

        <div className="features-cta">
          <div className="cta-card">
            <div className="cta-content">
              <h3>Perfect for AI Agents & Automation</h3>
              <p>Build chatbots, content generators, data processors, and more—without worrying about API costs</p>
              <ul className="cta-list">
                <li><CheckCircle2 size={18} /> Build unlimited prototypes</li>
                <li><CheckCircle2 size={18} /> Test ideas before investing in official API</li>
                <li><CheckCircle2 size={18} /> No credit card required</li>
              </ul>
            </div>
            <button className="btn btn-primary">Get Started Free</button>
          </div>
        </div>
      </div>
    </section>
  )
}
