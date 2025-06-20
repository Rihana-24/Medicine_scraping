import requests
import os
from dotenv import load_dotenv
import http.server
import socketserver
import urllib.parse
import webbrowser
import secrets

# Load environment variables
load_dotenv()

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:8000/callback")

if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET:
    print("Error: TIKTOK_CLIENT_KEY or TIKTOK_CLIENT_SECRET not found in .env file.")
    exit(1)

# Global variable to store the authorization code
auth_code = None

# HTTP server to capture the authorization code
class AuthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Error: No authorization code received.")

def get_access_token():
    """Obtain an Access Token using Client Key and Client Secret."""
    global auth_code
    state = secrets.token_urlsafe(16)
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/?client_key={TIKTOK_CLIENT_KEY}"
        f"&response_type=code&scope=video.list,comment.list&redirect_uri={TIKTOK_REDIRECT_URI}"
        f"&state={state}"
    )

    print("Opening browser for TikTok authorization...")
    webbrowser.open(auth_url)

    with socketserver.TCPServer(("", 8000), AuthHandler) as httpd:
        print("Waiting for authorization code on http://localhost:8000/callback...")
        httpd.handle_request()

    if not auth_code:
        print("Error: Failed to obtain authorization code.")
        exit(1)

    token_url = "https://open-api.tiktok.com/oauth/access_token/"
    data = {
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": TIKTOK_REDIRECT_URI
    }
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            print(f"Error: Failed to obtain Access Token. Response: {token_data}")
            exit(1)
        print(f"Success: Access Token obtained: {access_token}")
        return access_token
    except requests.RequestException as e:
        print(f"Error exchanging code for Access Token: {e}")
        exit(1)

if __name__ == "__main__":
    access_token = get_access_token()