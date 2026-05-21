from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

app = Flask(_name_)
app.config['SECRET_KEY'] = '40543a13d7c2fd34f3ffbb622b33edf25'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tontine.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

FEE_RATE = 0.05
ADMIN_NUMBERS = {'tmoney': '91 54 48 32', 'flooz': '96 24 05 38'}
ADMIN_USERNAME = 'jp'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    piggybanks = db.relationship('Piggybank', backref='owner', lazy=True)

class Piggybank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target = db.Column(db.Integer, nullable=False)
    balance = db.Column(db.Integer, default=0)
    desc = db.Column(db.String(200))
    color = db.Column(db.String(7), default='#667eea')
    total_fees = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='piggybank', lazy=True, cascade='all, delete-orphan')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    fee = db.Column(db.Integer, default=0)
    network = db.Column(db.String(20))
    number = db.Column(db.String(20))
    note = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    piggybank_id = db.Column(db.Integer, db.ForeignKey('piggybank.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def dashboard():
    piggies = Piggybank.query.filter_by(user_id=current_user.id).all()
    total_saved = sum(p.balance for p in piggies)
    total_fees = sum(p.total_fees for p in piggies)
    ready = sum(1 for p in piggies if p.balance == p.target and p.target > 0)
    return render_template('dashboard.html', piggies=piggies, total_saved=total_saved,
                         total_fees=total_fees, ready=ready)

@app.route('/create_piggy', methods=['POST'])
@login_required
def create_piggy():
    name = request.form['name']
    target = int(request.form['target'])
    desc = request.form['desc']
    color = request.form['color']

    piggy = Piggybank(name=name, target=target, desc=desc, color=color, user_id=current_user.id)
    db.session.add(piggy)
    db.session.commit()
    flash('Tirelire créée')
    return redirect(url_for('dashboard'))

@app.route('/deposit/<int:id>', methods=['POST'])
@login_required
def deposit(id):
    piggy = Piggybank.query.get_or_404(id)
    if piggy.user_id!= current_user.id:
        return 'Unauthorized', 403

    amount = int(request.form['amount'])
    note = request.form.get('note', 'Dépôt manuel')

    piggy.balance += amount
    tx = Transaction(type='depot', amount=amount, note=note, piggybank_id=id)
    db.session.add(tx)
    db.session.commit()
    flash('Dépôt effectué')
    return redirect(url_for('dashboard'))

@app.route('/withdraw/<int:id>', methods=['POST'])
@login_required
def withdraw(id):
    piggy = Piggybank.query.get_or_404(id)
    if piggy.user_id!= current_user.id:
        return 'Unauthorized', 403

    if piggy.balance!= piggy.target:
        flash('Retrait bloqué: solde ≠ cible')
        return redirect(url_for('dashboard'))

    network = request.form['network']
    number = request.form['number']
    fee = int(piggy.balance * FEE_RATE)
    admin_number = ADMIN_NUMBERS[network]

    tx = Transaction(
        type='retrait', amount=piggy.balance, fee=fee, network=network,
        number=number, note=f'Commission 5% versée sur {network} {admin_number}',
        piggybank_id=id
    )
    db.session.add(tx)
    piggy.total_fees += fee
    piggy.balance = 0
    db.session.commit()

    pdf_path = generate_receipt(tx, piggy)
    flash('Retrait confirmé. Télécharge ton reçu.')
    return send_file(pdf_path, as_attachment=True)

def generate_receipt(tx, piggy):
    filename = f'recu_{tx.id}.pdf'
    filepath = os.path.join('static', filename)
    c = canvas.Canvas(filepath, pagesize=A4)

    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, 800, "JP-Tontine Pro - Reçu de Retrait")
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, f"Date: {tx.date.strftime('%d/%m/%Y %H:%M')}")
    c.drawString(100, 730, f"Tirelire: {piggy.name}")
  c.drawString(100, 710, f"Montant: {tx.amount} FCFA".replace(',', '))
    c.drawString(100, 690, f"Réseau: {tx.network.upper()}")
    c.drawString(100, 670, f"Numéro bénéficiaire: {tx.number}")
    c.drawString(100, 650, f"Commission 5%: {tx.fee:,} FCFA".replace(',', '))
    c.drawString(100, 630, f"Note: {tx.note}")
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(100, 580, "Conservez ce reçu pour vos justificatifs.")
    c.save()
    return filepath

@app.route('/admin')
@login_required
def admin():
    if current_user.username!= ADMIN_USERNAME:
        return 'Unauthorized', 403

    users = User.query.all()
    txs = Transaction.query.filter_by(type='retrait').order_by(Transaction.date.desc()).all()
    total_fees_tmoney = sum(t.fee for t in txs if t.network == 'tmoney')
    total_fees_flooz = sum(t.fee for t in txs if t.network == 'flooz')

    return render_template('admin.html', users=users, txs=txs,
                         tmoney_total=total_fees_tmoney, flooz_total=total_fees_flooz)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Identifiants invalides')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed = generate_password_hash(request.form['password'])
        user = User(username=request.form['username'], password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        flash('Compte créé, connecte-toi')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if _name_ == '_main_':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
