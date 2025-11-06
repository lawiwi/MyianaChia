from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder='Templates')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Session en filesystem (útil para debug y Deploy básicos)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

db = SQLAlchemy(app)
# Modelo de usuario
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Explorador')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Rutas
@app.route('/BotonLog')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'Administrador':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'Emprendedor':
            return redirect(url_for('emprendedor_dashboard'))
        else:
            return redirect(url_for('explorador_dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        role = "Emprendedor" if 'is_emprendedor' in request.form else "Explorador"

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Usuario o correo ya registrado', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registro exitoso. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('Base/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier'].strip()
        password = request.form['password']

        # Buscamos usuario por nombre o email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Bienvenido {user.username}!', 'success')

            if user.role == 'Administrador':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'Emprendedor':
                return redirect(url_for('emprendedor_dashboard'))
            else:
                return redirect(url_for('explorador_dashboard'))

        else:
            flash('Credenciales incorrectas', 'danger')

    return render_template('Base/login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('login'))

# Helper: crear base de datos si no existe
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Base de datos creada (site.db)')


if __name__ == '__main__':
    # Crear DB si no existe (útil para desarrollo local)
    if not os.path.exists('site.db'):
        db.create_all()
    app.run(debug=True) 

@app.route("/")
def chiaentre():
    return render_template('Base/Home.html')

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/admin_dashboard')
def admin_dashboard():
    user = User.query.get(session['user_id'])
    return render_template('Base/dashboard_admin.html', user=user)

@app.route('/emprendedor_dashboard')
def emprendedor_dashboard():
    user = User.query.get(session['user_id'])
    return render_template('Emprededores/dashboard_emprededor.html', user=user)

@app.route('/explorador_dashboard')
def explorador_dashboard():
    user = User.query.get(session['user_id'])
    return render_template('Explorador/dashboard_explorador.html', user=user)

@app.route("/Restaurantes")
def chiacomida():
    return render_template('Usuarios/Restaurantes.html')

@app.route("/Arte")
def chiaarte():
    return render_template('Usuarios/Arte.html')

@app.route("/Deportes")
def chiadeportes():
    return render_template('Usuarios/Deportes.html')

@app.route("/Ocio")
def chiaocio():
    return render_template('Usuarios/Ocio.html')

@app.route("/Shopping")
def chiashopping():
    return render_template('Usuarios/Shopping.html')

@app.route("/Naturaleza")
def chianatu():
    return render_template('Usuarios/Recreacion.html')