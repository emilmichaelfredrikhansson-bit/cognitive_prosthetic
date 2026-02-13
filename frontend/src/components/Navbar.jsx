import { Terminal, Github } from 'lucide-react'

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="nav-logo">
          <Terminal size={28} />
          <span>ChatGPT Local API</span>
        </div>
        <div className="nav-links">
          <a href="#home">Home</a>
          <a href="#features">Features</a>
          <a href="#demo">Demo</a>
          <a href="#how-it-works">How It Works</a>
          <a href="#pricing">Pricing</a>
          <a href="https://github.com/yourusername/chatgpt-local-api" className="nav-cta" target="_blank">
            <Github size={18} />
            <span>GitHub</span>
          </a>
        </div>
      </div>
    </nav>
  )
}
