from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>E-Sawsaw Test</h1>
    <p>Flask is running successfully on Render.</p>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
