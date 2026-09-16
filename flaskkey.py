from flask import Flask
import secrets
app = Flask(__name__)
# Generate a secure random key
app.config['SECRET_KEY'] = secrets.token_hex(16)
# Example usage
@app.route('/')
def home():
   return "Secret Key Configured!"

import secrets
print(secrets.token_hex(16)) 