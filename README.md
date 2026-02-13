# ChatGPT Local API

Turn ChatGPT's web interface into a REST API running on your machine. **Free. Local. Unlimited.**

Built for developers who can't afford $20-200/month for OpenAI's API but still want to build AI agents, automate workflows, and experiment with ChatGPT.

---

## 🎯 What This Does

This project converts ChatGPT's web interface into a REST API server that runs locally on your computer. Instead of paying for API access, you use your existing ChatGPT account.

**Perfect for:**
- Building AI agents and chatbots
- Experimenting without token counting
- Prototyping before investing in official API
- Learning AI development on a budget
- Personal automation projects

**Trade-offs:**
- Subject to ChatGPT web UI rate limits
- Requires your machine to be running
- Not for production apps needing 99.9% uptime

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites

You need:
- Python 3.8 or higher
- A ChatGPT account (free or paid)
- macOS, Linux, or Windows

### Step 1: Clone & Install

```bash
# Clone the repository
git clone <your-repo-url>
cd cognitive_prosthetic

# Install Python dependencies
pip install flask flask-cors playwright

# Install Chromium browser (used for automation)
playwright install chromium
```

**What this does:** Installs the web server (Flask), enables cross-origin requests (CORS), and sets up browser automation (Playwright).

---

### Step 2: Login to ChatGPT (One-Time Setup)

Run the login script to save your ChatGPT session:

```bash
python3 manual_login.py
```

**What happens:**
1. A Chrome browser window opens
2. You'll see ChatGPT's login page
3. Log in with your credentials (email/password or Google)
4. Wait for the chat interface to fully load
5. Come back to the terminal and press **ENTER**
6. Your session is saved in `default_profile/` folder

**Important:**
- Don't close the browser manually - let the script close it
- Make sure you see the chat input box before pressing ENTER
- This only needs to be done once (session persists)

---

### Step 3: Start the API Server

```bash
python3 chatgpt_api_server.py
```

**What you'll see:**
```
============================================================
ChatGPT API Server (Thread-Safe)
============================================================

Initializing browser...
✓ Chat interface ready!

🚀 Server is running on http://localhost:5001
============================================================
```

**Leave this terminal window open** - the server needs to keep running.

---

### Step 4: Test It

Open a **new terminal window** and try:

```bash
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hello!"}'
```

**Expected response:**
```json
{
  "success": true,
  "response": "Hello! How can I help you today?",
  "prompt": "Say hello!"
}
```

**If you see this, it's working!** 🎉

---

## 📖 How to Use the API

### Send a Prompt

**Endpoint:** `POST http://localhost:5001/chat`

**Request:**
```bash
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing in simple terms"}'
```

**Response:**
```json
{
  "success": true,
  "response": "Quantum computing uses quantum bits...",
  "prompt": "Explain quantum computing in simple terms"
}
```

### Start New Conversation

**Endpoint:** `POST http://localhost:5001/new-chat`

Clears the conversation history and starts fresh.

```bash
curl -X POST http://localhost:5001/new-chat
```

### Check Server Health

**Endpoint:** `GET http://localhost:5001/health`

```bash
curl http://localhost:5001/health
```

**Response:**
```json
{
  "status": "running",
  "ready": true
}
```

---

## 💻 Use It From Your Code

### Python

```python
import requests

def ask_chatgpt(prompt):
    response = requests.post(
        'http://localhost:5001/chat',
        json={"prompt": prompt}
    )
    return response.json()['response']

# Use it
answer = ask_chatgpt("What is machine learning?")
print(answer)
```

### JavaScript/Node.js

```javascript
async function askChatGPT(prompt) {
  const response = await fetch('http://localhost:5001/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt })
  });
  const data = await response.json();
  return data.response;
}

// Use it
const answer = await askChatGPT('What is machine learning?');
console.log(answer);
```

### Any Language

The API uses standard HTTP/JSON, so it works with:
- Go
- Ruby
- PHP
- Java
- Rust
- Any language that can make HTTP requests

---

## 🎨 Web Interface (Optional)

A React-based web UI is included for testing and demos.

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser to:
- Test the API interactively
- See live examples
- View documentation

---

## 🔧 Troubleshooting

### "Server not running" error

**Problem:** The frontend can't connect to the API.

**Solution:**
1. Make sure the API server is running: `python3 chatgpt_api_server.py`
2. Check it's on port 5001: `curl http://localhost:5001/health`
3. Verify CORS is working (should see success response)

---

### "Could not find chat input" error

**Problem:** The browser automation can't locate ChatGPT's input box.

**Solution:**
1. Re-run the login: `python3 manual_login.py`
2. Make sure you're logged in (check the browser window)
3. Wait for the page to fully load before pressing ENTER
4. If still failing, ChatGPT's UI may have changed (check for updates)

---

### "Session expired" or login page appears

**Problem:** Your ChatGPT session has expired.

**Solution:**
1. Stop the server (Ctrl+C)
2. Re-login: `python3 manual_login.py`
3. Restart the server: `python3 chatgpt_api_server.py`

---

### Browser window keeps appearing

**Problem:** The browser is not running in headless mode.

**Why:** This is intentional! Headless mode often triggers bot detection.

**To minimize the window:**
- Just minimize it to the background
- Don't close it - the server needs it
- It will stay out of your way while you work

---

### Requests timing out

**Problem:** Responses take too long and timeout occurs.

**Solution:**
1. Check your internet connection
2. Try a simpler prompt to test
3. Increase timeout in your client code (default is 120 seconds)
4. ChatGPT might be slow - this is normal sometimes

---

### Port 5001 already in use

**Problem:** Another service is using port 5001.

**Solution:**
Edit `chatgpt_api_server.py` line ~367:
```python
app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
```
Change `5001` to any available port (e.g., `5002`, `8000`, etc.)

---

## 📋 API Reference

### POST /chat

Send a prompt to ChatGPT and get a response.

**Request Body:**
```json
{
  "prompt": "Your question here"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "response": "ChatGPT's answer",
  "prompt": "Your original question"
}
```

**Error Response (500):**
```json
{
  "success": false,
  "error": "Error description"
}
```

**Timeout:** 120 seconds default

---

### POST /new-chat

Start a new conversation (clears history).

**Success Response (200):**
```json
{
  "success": true,
  "message": "New chat started"
}
```

---

### GET /health

Check if the server is running and ready.

**Response (200):**
```json
{
  "status": "running",
  "ready": true
}
```

---

### GET /status

Get detailed server information.

**Response (200):**
```json
{
  "server": "running",
  "browser_ready": true,
  "profile_path": "./default_profile"
}
```

---

## ⚙️ Configuration

### Run in Background (Headless Mode)

Edit `chatgpt_api_server.py` line ~50:

```python
headless=True,  # Change from False to True
```

**Warning:** Headless mode may trigger bot detection. Test thoroughly!

---

### Change Profile Location

Edit `profile_config.txt`:
```
./my_custom_profile
```

Or specify when running `manual_login.py` (choose option 3 for custom name).

---

### Adjust Timeouts

If responses are timing out, edit `chatgpt_api_server.py` line ~248:

```python
result = result_queue.get(timeout=300)  # Increase from 200 to 300 seconds
```

---

## 🛡️ Best Practices

### 1. Rate Limiting
Don't send requests faster than **1 per 3 seconds** to avoid rate limits.

```python
import time

for question in questions:
    answer = ask_chatgpt(question)
    print(answer)
    time.sleep(3)  # Wait 3 seconds between requests
```

### 2. Error Handling
Always handle errors gracefully:

```python
def safe_ask(prompt):
    try:
        response = requests.post('http://localhost:5001/chat',
                               json={"prompt": prompt},
                               timeout=120)
        data = response.json()
        if data.get('success'):
            return data['response']
        else:
            print(f"Error: {data.get('error')}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None
```

### 3. Session Management
- Re-login every few days/weeks when session expires
- Keep the browser window minimized (don't close it)
- Don't interact with the ChatGPT window manually while server is running

---

## 📁 Project Structure

```
.
├── chatgpt_api_server.py    # Main API server (Flask + Playwright)
├── manual_login.py           # One-time login helper
├── requirements.txt          # Python dependencies
├── profile_config.txt        # Stores profile path
├── default_profile/          # Your saved ChatGPT session
├── frontend/                 # React web UI (optional)
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   └── App.css          # Styling
│   └── package.json
└── README.md                 # This file
```

---

## 🆘 Getting Help

### Common Issues

1. **Browser won't close:**
   ```bash
   pkill -f chatgpt_api_server
   pkill -f chromium
   ```

2. **Profile corrupted:**
   ```bash
   rm -rf default_profile/
   python3 manual_login.py
   ```

3. **Server won't start:**
   ```bash
   pip install --upgrade flask flask-cors playwright
   playwright install chromium
   ```

### Still Stuck?

1. Check if ChatGPT website is accessible in your regular browser
2. Verify you're logged in to ChatGPT
3. Make sure no firewall is blocking localhost:5001
4. Try restarting your computer
5. Check GitHub Issues for similar problems

---

## 📝 Requirements

- **Python:** 3.8+
- **OS:** macOS, Linux, or Windows
- **RAM:** 2GB+ recommended
- **Internet:** Stable connection required
- **ChatGPT Account:** Free or paid (any tier works)

---

## ⚖️ Legal & Terms of Service

**Important:** This tool automates ChatGPT's web interface for personal use. Please review OpenAI's Terms of Service.

- **NOT** an official OpenAI product
- **NOT** recommended for commercial production use
- **MAY** violate OpenAI's ToS (check current terms)
- For **personal/educational** use only
- Use at your own risk

For production applications, use the [official OpenAI API](https://platform.openai.com/docs/api-reference).

---

## 🎯 Use Cases

### Build AI Agents
```python
# Example: Research assistant
def research_topic(topic):
    questions = [
        f"What is {topic}?",
        f"What are the key concepts of {topic}?",
        f"What are real-world applications of {topic}?"
    ]

    for q in questions:
        answer = ask_chatgpt(q)
        print(f"Q: {q}\nA: {answer}\n")
        time.sleep(3)
```

### Content Automation
```python
# Example: Blog post generator
def generate_post(title):
    outline = ask_chatgpt(f"Create an outline for: {title}")
    intro = ask_chatgpt(f"Write an intro based on: {outline}")
    conclusion = ask_chatgpt(f"Write a conclusion for: {title}")

    return f"{intro}\n\n{conclusion}"
```

### Data Processing
```python
# Example: Categorize customer feedback
feedback_list = ["Great product!", "Shipping was slow", "Love it!"]

for feedback in feedback_list:
    category = ask_chatgpt(f"Categorize this feedback: {feedback}")
    print(f"{feedback} -> {category}")
    time.sleep(3)
```

---

## 🚀 What's Next?

1. **Test it out** - Send some prompts and see responses
2. **Build something** - Create your first AI agent or automation
3. **Share feedback** - Open an issue if you find bugs
4. **Contribute** - Submit PRs to improve the project

---

## 📜 License

MIT License - Free to use for any purpose.

---

## 🙏 Acknowledgments

Built for indie developers, students, and builders who want to experiment with AI without breaking the bank.

If this saved you money or helped you build something cool, consider:
- ⭐ Starring the repo
- 🐛 Reporting bugs
- 💡 Suggesting improvements
- 📢 Sharing with others

---

**Made with ☕ for builders who can't afford API costs**
