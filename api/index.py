from flask import Flask
from vercel_python_wsgi import make_handler

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello from Flask on Vercel!"

@app.route("/predict", methods=["POST"])
def predict():
    return {"result": "Your model result here"}

# Vercel needs `handler`
handler = make_handler(app)
