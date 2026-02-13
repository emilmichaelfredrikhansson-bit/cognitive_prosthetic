import { Check, X, TrendingDown, Zap } from 'lucide-react'

export default function Pricing() {
  return (
    <section className="pricing" id="pricing">
      <div className="pricing-container">
        <div className="pricing-header">
          <h2 className="section-title">The Math is Simple</h2>
          <p className="section-subtitle">
            Why pay monthly when you can run it locally for free?
          </p>
        </div>

        <div className="pricing-comparison">
          <div className="pricing-card pricing-paid">
            <div className="pricing-tag">Official API</div>
            <div className="pricing-price">
              <span className="price-amount">$20-200</span>
              <span className="price-period">/month</span>
            </div>
            <ul className="pricing-features">
              <li><Check size={18} /> Official OpenAI API</li>
              <li><Check size={18} /> Reliable & Supported</li>
              <li><Check size={18} /> GPT-4 Access</li>
              <li><X size={18} className="feature-negative" /> Costs add up fast</li>
              <li><X size={18} className="feature-negative" /> Rate limits</li>
              <li><X size={18} className="feature-negative" /> Pay per token</li>
              <li><X size={18} className="feature-negative" /> Enterprise only for scale</li>
            </ul>
            <div className="pricing-note">
              <strong>$0.03</strong> per 1K tokens (GPT-4)
              <br />
              <strong>$0.002</strong> per 1K tokens (GPT-3.5)
            </div>
          </div>

          <div className="pricing-card pricing-free highlight">
            <div className="pricing-badge">
              <Zap size={16} />
              <span>BEST VALUE</span>
            </div>
            <div className="pricing-tag">This Project</div>
            <div className="pricing-price">
              <span className="price-amount">$0</span>
              <span className="price-period">forever</span>
            </div>
            <ul className="pricing-features">
              <li><Check size={18} /> Completely Free</li>
              <li><Check size={18} /> Unlimited Requests</li>
              <li><Check size={18} /> Runs Locally</li>
              <li><Check size={18} /> Full Privacy</li>
              <li><Check size={18} /> No Rate Limits*</li>
              <li><Check size={18} /> Open Source</li>
              <li><Check size={18} /> Perfect for Prototypes</li>
            </ul>
            <div className="pricing-note">
              Uses your existing ChatGPT account
              <br />
              * Subject to ChatGPT web UI limits
            </div>
            <button className="btn btn-primary">Get Started Free</button>
          </div>
        </div>

        <div className="savings-calculator">
          <div className="savings-card">
            <TrendingDown size={32} className="savings-icon" />
            <h3>Estimated Savings</h3>
            <div className="savings-grid">
              <div className="saving-item">
                <div className="saving-value">$240</div>
                <div className="saving-label">Saved per year</div>
                <div className="saving-desc">vs $20/month API plan</div>
              </div>
              <div className="saving-item">
                <div className="saving-value">$2,400</div>
                <div className="saving-label">Saved per year</div>
                <div className="saving-desc">vs $200/month usage</div>
              </div>
              <div className="saving-item">
                <div className="saving-value">∞</div>
                <div className="saving-label">Requests</div>
                <div className="saving-desc">No token counting</div>
              </div>
            </div>
          </div>
        </div>

        <div className="pricing-faq">
          <h3>When to Use What?</h3>
          <div className="faq-grid">
            <div className="faq-item">
              <h4>Use This Project When:</h4>
              <ul>
                <li>Building prototypes and MVPs</li>
                <li>Personal automation projects</li>
                <li>Learning and experimentation</li>
                <li>Budget is tight</li>
                <li>Low-medium request volume</li>
                <li>Privacy is important</li>
              </ul>
            </div>
            <div className="faq-item">
              <h4>Use Official API When:</h4>
              <ul>
                <li>Production applications</li>
                <li>High-traffic services</li>
                <li>Need 99.9% uptime</li>
                <li>Enterprise support required</li>
                <li>Sub-second response times</li>
                <li>GPT-4 is essential</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
