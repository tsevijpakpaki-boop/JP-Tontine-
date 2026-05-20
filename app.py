from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Mon app Flask fonctionne sur Render !"

if __name__ == "__main__":
    app.run(debug=True)
