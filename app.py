
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

membres = []

@app.route("/")
def home():
    return render_template("index.html", membres=membres)

@app.route("/ajouter", methods=["POST"])
def ajouter():
    nom = request.form.get("nom")
    montant = request.form.get("montant")
    if nom and montant:
        membres.append({"nom": nom, "montant": montant})
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True) 
