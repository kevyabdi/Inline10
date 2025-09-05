from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running fine on Replit!"

def run():
    # Replit expects app to bind on port 5000
    app.run(host="0.0.0.0", port=5000)

def keep_alive():
    t = threading.Thread(target=run)
    t.daemon = True   # si uu u socdo background
    t.start()
