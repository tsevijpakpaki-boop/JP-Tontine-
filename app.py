
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "jp_tontine_secret_key"

# Données en mémoire - on passera sur DB plus tard
members = []
transactions = []
piggy_banks = []

@app.route('/')
def index():
    return render_template('index.html',
                           members=members,
                           transactions=transactions,
                           piggy_banks=piggy_banks)

@app.route('/add_member', methods=['POST'])
def add_member():
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    if name and amount > 0:
        members.append({'name': name, 'amount': amount})
        flash("Membre ajouté avec succès", "success")
    return redirect(url_for('index'))
@app.route('/add_to_piggy', methods=['POST'])
def add_to_piggy():
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    
    # Trouve la tirelire avec ce nom
    piggy = next((p for p in piggy_banks if p['name'] == name), None)
    
    if piggy and amount > 0:
        piggy['current'] += amount
        flash("Montant ajouté à la tirelire", "success")
    else:
        flash("Tirelire introuvable", "error")
    
    return redirect(url_for('index'))
@app.route( methods=['POST'])
def withdraw():
    name = request.form.get('name')
    amount = float(request.form.get('amount', 0))
    network = request.form.get('network') # tmoney ou flooz

    member = next((m for m in members if m['name'] == name), None)

    if not member:
        flash("Membre introuvable", "error")
        return redirect(url_for('index'))

    if amount <= 0 or amount > member['amount']:
        flash("Montant invalide", "error")
        return redirect(url_for('index'))

    commission = amount * 0.03
    net_amount = amount - commission

    # MAJ solde membre
    member['amount'] -= amount

    # Enregistrer transaction
    transactions.append({
        'type': 'retrait',
        'name': name,
        'amount': amount,
        'commission': commission,
        'net_amount': net_amount,
        'network': network,
        'date': datetime.now().strftime('%d/%m/%Y %H:%M')
    })

    network_num = "91 54 48 32" if network == "tmoney" else "96 24 05 38"
    flash(f"Retrait validé. Commission 3% envoyée sur {network.upper()} {network_num}", "success")
    return redirect(url_for('index'))

@app.route('/add_piggy_bank', methods=['POST'])
def add_piggy_bank():
    name = request.form.get('piggy_name')
    goal = float(request.form.get('goal', 0))
    if name and goal > 0:
        piggy_banks.append({'name': name, 'goal': goal, 'current': 0})
        flash("Tirelire créée", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
