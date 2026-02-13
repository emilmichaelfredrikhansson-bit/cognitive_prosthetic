import { useState } from 'react'
import { Copy, Check } from 'lucide-react'

const examples = {
  python: {
    name: 'Python',
    code: `import requests

def ask_chatgpt(prompt):
    response = requests.post('http://localhost:5001/chat', json={
        "prompt": prompt
    })
    return response.json()['response']

# Use it
answer = ask_chatgpt("What is machine learning?")
print(answer)

# Batch processing
questions = [
    "What is Python?",
    "Explain async/await",
    "What are decorators?"
]

for q in questions:
    answer = ask_chatgpt(q)
    print(f"Q: {q}")
    print(f"A: {answer}\\n")`
  },
  javascript: {
    name: 'JavaScript',
    code: `// Node.js
const axios = require('axios');

async function askChatGPT(prompt) {
  const response = await axios.post('http://localhost:5001/chat', {
    prompt: prompt
  });
  return response.data.response;
}

// Use it
const answer = await askChatGPT('Explain async/await');
console.log(answer);

// Browser fetch API
fetch('http://localhost:5001/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ prompt: 'Hello!' })
})
.then(r => r.json())
.then(data => console.log(data.response));`
  },
  curl: {
    name: 'cURL',
    code: `# Simple request
curl -X POST http://localhost:5001/chat \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "What is REST API?"}'

# Save response to file
curl -X POST http://localhost:5001/chat \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "Explain Docker"}' \\
  | jq '.response' > response.txt

# Health check
curl http://localhost:5001/health

# Start new conversation
curl -X POST http://localhost:5001/new-chat`
  },
  go: {
    name: 'Go',
    code: `package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

type ChatRequest struct {
    Prompt string \`json:"prompt"\`
}

type ChatResponse struct {
    Success  bool   \`json:"success"\`
    Response string \`json:"response"\`
}

func askChatGPT(prompt string) (string, error) {
    reqBody, _ := json.Marshal(ChatRequest{Prompt: prompt})

    resp, err := http.Post(
        "http://localhost:5001/chat",
        "application/json",
        bytes.NewBuffer(reqBody),
    )
    if err != nil {
        return "", err
    }
    defer resp.Body.Close()

    var chatResp ChatResponse
    json.NewDecoder(resp.Body).Decode(&chatResp)

    return chatResp.Response, nil
}`
  }
}

export default function CodeExamples() {
  const [activeTab, setActiveTab] = useState('python')
  const [copied, setCopied] = useState(false)

  const copyToClipboard = () => {
    navigator.clipboard.writeText(examples[activeTab].code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section className="code-examples" id="docs">
      <div className="examples-container">
        <div className="examples-header">
          <h2 className="section-title">Code Examples</h2>
          <p className="section-subtitle">
            Works with any language that can make HTTP requests
          </p>
        </div>

        <div className="examples-tabs">
          {Object.keys(examples).map((key) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`tab-btn ${activeTab === key ? 'active' : ''}`}
            >
              {examples[key].name}
            </button>
          ))}
        </div>

        <div className="examples-code">
          <div className="code-header">
            <span className="code-lang">{examples[activeTab].name}</span>
            <button onClick={copyToClipboard} className="copy-btn">
              {copied ? <Check size={18} /> : <Copy size={18} />}
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </button>
          </div>
          <pre className="code-block">
            <code>{examples[activeTab].code}</code>
          </pre>
        </div>

        <div className="examples-grid">
          <div className="example-card">
            <h3>🤖 Build AI Agents</h3>
            <p>Create autonomous agents that can research, write, and make decisions</p>
          </div>
          <div className="example-card">
            <h3>📝 Content Generation</h3>
            <p>Automate blog posts, social media, documentation, and more</p>
          </div>
          <div className="example-card">
            <h3>💬 Chatbots</h3>
            <p>Build custom chatbots for Slack, Discord, Telegram, or your website</p>
          </div>
          <div className="example-card">
            <h3>🔄 Data Processing</h3>
            <p>Analyze, categorize, and transform large datasets with AI</p>
          </div>
        </div>
      </div>
    </section>
  )
}
