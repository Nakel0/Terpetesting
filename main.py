# main.py
from flask import Flask, request, jsonify
import requests
import time
import json
import os
from urllib.parse import unquote

app = Flask(__name__)

# Your 1NCE credentials (use environment variables for security)
ONCEAPI_USERNAME = os.getenv("ONCEAPI_USERNAME", "okunleyenakky@gmail.com")
ONCEAPI_PASSWORD = os.getenv("ONCEAPI_PASSWORD", "")  # Set this in Railway dashboard

# Token storage
access_token = None
token_expires_at = 0

# not valid will re move

def get_access_token():
    """Get or refresh the 1NCE access token"""
    global access_token, token_expires_at
    
    # Check if token is still valid (with 5 minute buffer)
    if access_token and time.time() < (token_expires_at - 300):
        print("Using existing valid token")
        return access_token
    
    print(f"Getting new token for username: {ONCEAPI_USERNAME}")
    print(f"Password is {'set' if ONCEAPI_PASSWORD else 'NOT SET'}")
    
    # Use Basic Auth header with client_credentials grant type
    import base64
    credentials = base64.b64encode(f"{ONCEAPI_USERNAME}:{ONCEAPI_PASSWORD}".encode()).decode()
    
    token_url = "https://api.1nce.com/management-api/oauth/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}"
    }
    data = {
        "grant_type": "client_credentials"
    }
    
    try:
        print(f"Making request to: {token_url}")
        print(f"Using Basic Auth with username: {ONCEAPI_USERNAME}")
        print(f"Grant type: client_credentials")
        response = requests.post(token_url, headers=headers, data=data)
        print(f"1NCE Token Response Status: {response.status_code}")
        print(f"1NCE Token Response: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            token_expires_at = time.time() + expires_in
            
            print(f"✅ New token obtained, expires in {expires_in} seconds")
            return access_token
        else:
            print(f"❌ Failed to get token: {response.status_code} - {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting access token: {e}")
        return None

@app.route('/sms', methods=['POST', 'GET'])
def send_sms():
    """Middleware endpoint that accepts requests from your platform"""
    
    # Get access token
    token = get_access_token()
    if not token:
        return jsonify({"error": "Failed to authenticate with 1NCE"}), 401
    
    # Extract parameters from query string
    phone_number = request.args.get('to', '')
    message = request.args.get('message', '')
    
    if not phone_number or not message:
        return jsonify({"error": "Missing phone number or message"}), 400
    
    # Decode URL-encoded message
    message = unquote(message)
    phone_number = unquote(phone_number)
    
    # Your SIM ICCID
    iccid = "8958822866614198736"
    
    # 1NCE SMS API endpoint
    sms_url = f"https://api.1nce.com/management-api/v1/sims/{iccid}/sms"
    
    # Prepare the request to 1NCE
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # 1NCE payload format
    payload = {
        "sourceAddress": "",
        "payload": message,
        "submitSm": {
            "destAddrNpi": 1,
            "destAddrTon": 1
        }
    }
    
    try:
        # Send SMS via 1NCE API
        response = requests.post(sms_url, headers=headers, json=payload)
        
        print(f"1NCE Response: {response.status_code} - {response.text}")
        
        if response.status_code in [200, 201, 202]:
            return jsonify({
                "status": "success", 
                "message": "SMS sent successfully",
                "to": phone_number,
                "text": message
            })
        else:
            return jsonify({
                "error": f"1NCE API error: {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"Error sending SMS: {e}")
        return jsonify({"error": "Failed to send SMS"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    token_valid = access_token is not None and time.time() < token_expires_at
    return jsonify({
        "status": "healthy", 
        "token_valid": token_valid,
        "username": ONCEAPI_USERNAME
    })

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        "service": "1NCE SMS Middleware",
        "endpoints": {
            "sms": "/sms?to=PHONE_NUMBER&message=MESSAGE",
            "health": "/health"
        }
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# requirements.txt content:
"""
flask==2.3.3
requests==2.31.0
gunicorn==21.2.0
"""
