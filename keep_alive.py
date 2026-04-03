import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Alexandria Cinema Bot is running!"

def run():
    # Use the PORT environment variable provided by the platform (default to 8000)
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True # Ensure the thread dies when the main program exists
    t.start()