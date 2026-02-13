#!/usr/bin/env python3
"""
Test client for ChatGPT API Server
Usage: python3 test_client.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5001"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        print(f"✓ Health check: {data}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_chat(prompt):
    """Test chat endpoint"""
    print(f"\nSending prompt: '{prompt}'")
    print("Waiting for response...\n")

    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"prompt": prompt},
            timeout=180  # 3 minute timeout
        )

        data = response.json()

        if data.get("success"):
            print("="*60)
            print("CHATGPT RESPONSE:")
            print("="*60)
            print(data["response"])
            print("="*60)
            return True
        else:
            print(f"✗ Error: {data.get('error')}")
            return False

    except requests.exceptions.Timeout:
        print("✗ Request timed out")
        return False
    except Exception as e:
        print(f"✗ Request failed: {e}")
        return False

def test_new_chat():
    """Test new chat endpoint"""
    print("\nStarting new chat...")
    try:
        response = requests.post(f"{BASE_URL}/new-chat")
        data = response.json()

        if data.get("success"):
            print("✓ New chat started")
            return True
        else:
            print(f"✗ Error: {data.get('error')}")
            return False
    except Exception as e:
        print(f"✗ Failed to start new chat: {e}")
        return False

def interactive_mode():
    """Interactive chat mode"""
    print("\n" + "="*60)
    print("INTERACTIVE MODE - Type 'quit' to exit, 'new' for new chat")
    print("="*60 + "\n")

    while True:
        try:
            prompt = input("You: ").strip()

            if not prompt:
                continue

            if prompt.lower() == 'quit':
                print("Goodbye!")
                break

            if prompt.lower() == 'new':
                test_new_chat()
                continue

            print()
            test_chat(prompt)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("ChatGPT API Server - Test Client")
    print("="*60)

    # Check if server is running
    if not test_health():
        print("\n⚠️  Server is not running!")
        print("Start it with: python3 chatgpt_api_server.py")
        sys.exit(1)

    # Check for command line arguments
    if len(sys.argv) > 1:
        # Use command line prompt
        prompt = " ".join(sys.argv[1:])
        test_chat(prompt)
    else:
        # Run quick test
        print("\nRunning quick test...")
        if test_chat("Say 'Hello!' and nothing else."):
            print("\n✓ Test passed!")

        # Enter interactive mode
        try:
            response = input("\nEnter interactive mode? (y/n): ").strip().lower()
            if response == 'y':
                interactive_mode()
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
