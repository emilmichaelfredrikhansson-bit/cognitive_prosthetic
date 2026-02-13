import { Github, Twitter, Mail, Heart, Terminal } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-top">
          <div className="footer-brand">
            <div className="footer-logo">
              <Terminal size={32} />
              <span>ChatGPT Local API</span>
            </div>
            <p>Free, open-source ChatGPT API for builders and makers</p>
            <div className="footer-social">
              <a href="https://github.com" target="_blank" rel="noopener noreferrer">
                <Github size={20} />
              </a>
              <a href="https://twitter.com" target="_blank" rel="noopener noreferrer">
                <Twitter size={20} />
              </a>
              <a href="mailto:hello@example.com">
                <Mail size={20} />
              </a>
            </div>
          </div>

          <div className="footer-links">
            <div className="footer-column">
              <h4>Product</h4>
              <a href="#features">Features</a>
              <a href="#demo">Demo</a>
              <a href="#how-it-works">How It Works</a>
              <a href="#pricing">Pricing</a>
            </div>

            <div className="footer-column">
              <h4>Resources</h4>
              <a href="#docs">Documentation</a>
              <a href="https://github.com">GitHub</a>
              <a href="#examples">Examples</a>
              <a href="#faq">FAQ</a>
            </div>

            <div className="footer-column">
              <h4>Community</h4>
              <a href="https://github.com/issues">Issues</a>
              <a href="https://github.com/discussions">Discussions</a>
              <a href="https://discord.com">Discord</a>
              <a href="#contribute">Contribute</a>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <p>
            Made with <Heart size={16} className="heart" /> by developers, for developers
          </p>
          <p>
            Open source under MIT License • Not affiliated with OpenAI
          </p>
        </div>
      </div>
    </footer>
  )
}
