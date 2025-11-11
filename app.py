from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_session import Session
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import func
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones con los modelos de detalle (añadimos cascade)
    explorador = db.relationship('Explorador', backref='user', uselist=False, cascade='all, delete-orphan')
    emprendedor = db.relationship('Emprendedor', backref='user', uselist=False, cascade='all, delete-orphan')

    # Métodos de seguridad
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Explorador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    primer_nombre = db.Column(db.String(50))
    segundo_nombre = db.Column(db.String(50))
    primer_apellido = db.Column(db.String(50))
    segundo_apellido = db.Column(db.String(50))
    fecha_nacimiento = db.Column(db.Date)
    telefono = db.Column(db.String(20))
    preferencias = db.Column(db.String(200))

class Emprendedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Datos personales
    primer_nombre = db.Column(db.String(50))
    segundo_nombre = db.Column(db.String(50))
    primer_apellido = db.Column(db.String(50))
    segundo_apellido = db.Column(db.String(50))
    fecha_nacimiento = db.Column(db.Date)
    telefono = db.Column(db.String(20))

    # Datos de la empresa
    nombre_emprendimiento = db.Column(db.String(100), nullable=False)
    nit = db.Column(db.String(30), unique=True, nullable=False)
    clasificacion = db.Column(db.String(50))  # Ej: "Comida", "Ocio", "Hospedaje"
    zona = db.Column(db.String(100))
    ubicacion = db.Column(db.String(100))
    plan = db.Column(db.String(50), default='Sin Plan')

class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    clasificacion = db.Column(db.String(50))
    zona = db.Column(db.String(100))
    ubicacion = db.Column(db.String(100))
    descripcion = db.Column(db.Text)
    url = db.Column(db.String(200))
    emprendedor_id = db.Column(db.Integer, db.ForeignKey('emprendedor.id'))
    visitas = db.relationship('Visita', backref='empresa', lazy=True)

class Favorito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    explorador_id = db.Column(db.Integer, db.ForeignKey('explorador.id'), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow)

class Visita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'))
    explorador_id = db.Column(db.Integer, db.ForeignKey('explorador.id'), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(50), default='clic')  # clic, guardado, etc.

class LogAccion(db.Model):
    __tablename__ = 'log_accion'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    tipo_entidad = db.Column(db.String(100))  # Ej: "Usuario", "Emprendimiento"
    entidad_id = db.Column(db.Integer, nullable=True)  # ID del registro afectado
    accion = db.Column(db.String(200))  # Ej: "Creación", "Eliminación", "Modificación"
    detalles = db.Column(db.Text)  # Texto libre con información adicional
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='acciones_log')

    def __repr__(self):
        return f"<LogAccion {self.id} - {self.accion} - {self.tipo_entidad}>"

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
        role = request.form.get('role', 'Explorador')

        # Evitar duplicados
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Usuario o correo ya registrado', 'danger')
            return redirect(url_for('register'))

        # Crear el usuario base
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # -------------------------------
        # Conversión segura de fecha
        # -------------------------------
        from datetime import datetime
        fecha_nacimiento_str = request.form.get('fecha_nacimiento', '').strip()
        fecha_nacimiento = None
        if fecha_nacimiento_str:
            try:
                fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Formato de fecha inválido. Usa AAAA-MM-DD.", "danger")
                return redirect(url_for('register'))

        # -------------------------------
        # Registro según el rol
        # -------------------------------
        if role == 'Explorador':
            nuevo_explorador = Explorador(
                user_id=new_user.id,
                primer_nombre=request.form.get('primer_nombre', '').strip(),
                segundo_nombre=request.form.get('segundo_nombre', '').strip(),
                primer_apellido=request.form.get('primer_apellido', '').strip(),
                segundo_apellido=request.form.get('segundo_apellido', '').strip(),
                fecha_nacimiento=fecha_nacimiento,
                telefono=request.form.get('telefono', '').strip(),
                preferencias=request.form.get('preferencias', '').strip()
            )
            db.session.add(nuevo_explorador)

        elif role == 'Emprendedor':
            nuevo_emprendedor = Emprendedor(
                user_id=new_user.id,
                primer_nombre=request.form.get('primer_nombre_emp', '').strip(),
                segundo_nombre=request.form.get('segundo_nombre_emp', '').strip(),
                primer_apellido=request.form.get('primer_apellido_emp', '').strip(),
                segundo_apellido=request.form.get('segundo_apellido_emp', '').strip(),
                fecha_nacimiento=fecha_nacimiento,
                telefono=request.form.get('telefono_emp', '').strip(),
                nombre_emprendimiento=request.form.get('nombre_emprendimiento', '').strip(),
                nit=request.form.get('nit', '').strip(),
                clasificacion=request.form.get('clasificacion', '').strip(),
                ubicacion=request.form.get('ubicacion', '').strip(),
                zona=request.form.get('zona', '').strip()
            )
            db.session.add(nuevo_emprendedor)

        # Guardar todo
        db.session.commit()

        # -------------------------------
        # 📘 REGISTRO EN AUDITORÍA
        # -------------------------------
        log = LogAccion(
            entidad_id=new_user.id,
            accion="Creación",
            detalles=f"Se creó el usuario '{new_user.username}' con rol '{new_user.role}'."
        )
        db.session.add(log)
        db.session.commit()

        flash('Registro exitoso. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    # Si GET → mostrar el formulario
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

@app.route('/crear_admin')
def crear_admin():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        return "El administrador ya existe"

    admin = User(
        username='admin',
        email='admin@myiana.com',
        role='Administrador'
    )
    admin.set_password('admin')
    db.session.add(admin)
    db.session.commit()
    return "Usuario administrador creado correctamente: admin / admin123"


if __name__ == '__main__':
    # Crear DB si no existe (útil para desarrollo local)
    if not os.path.exists('site.db'):
        db.create_all()
    app.run(debug=True) 


@app.route("/")
def chiaentre():
    return render_template('Base/Home.html')

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
from collections import Counter

@app.route('/admin_dashboard')
def admin_dashboard():
    # Totales generales
    total_usuarios = User.query.count()
    total_exploradores = User.query.filter(func.lower(User.role) == 'explorador').count()
    total_emprendedores = User.query.filter(func.lower(User.role) == 'emprendedor').count()

    # Datos para la gráfica de roles
    roles_data = {
        'Exploradores': total_exploradores,
        'Emprendedores': total_emprendedores
    }
    
    # --- Datos para exploradores ---
    exploradores = Explorador.query.all()

    # --- Datos para emprendedores ---
    emprendedores = Emprendedor.query.all()
    planes_posibles = ['Sin Plan','Valvanera', 'Castillo Marroquin', 'Diosa chia']

    logs = LogAccion.query.order_by(LogAccion.fecha.desc()).all()

    # Contar cuántos emprendedores hay por plan
    planes = [e.plan if e.plan in planes_posibles else 'Sin plan' for e in emprendedores]
    plan_counts = Counter(planes)

    labels_plan = planes_posibles
    values_plan = [plan_counts.get(p, 0) for p in labels_plan]

    # --- Gráfica de preferencias (Exploradores) ---
    preferencias_posibles = ['Comida', 'Hospedaje', 'Ocio', 'Arte y Cultura', 'Naturaleza', 'Compras']
    preferencias = [exp.preferencias for exp in exploradores if exp.preferencias in preferencias_posibles]
    preferencias_count = Counter(preferencias)

    labels_pref = preferencias_posibles
    values_pref = [preferencias_count.get(p, 0) for p in labels_pref]

    acciones_labels = ['Creación', 'Edición', 'Eliminación']

    conteo_acciones = {
        'Creación': db.session.query(func.count(LogAccion.id)).filter(LogAccion.accion.like('%Creación%')).scalar(),
        'Edición': db.session.query(func.count(LogAccion.id)).filter(LogAccion.accion.like('%Edición%')).scalar(),
        'Eliminación': db.session.query(func.count(LogAccion.id)).filter(LogAccion.accion.like('%Eliminación%')).scalar()
    }

    acciones_values = [conteo_acciones[label] for label in acciones_labels]

    return render_template(
        'Base/dashboard_admin.html',
        total_usuarios=total_usuarios,
        total_exploradores=total_exploradores,
        total_emprendedores=total_emprendedores,
        roles_data=roles_data,
        emprendedores=emprendedores,
        exploradores=exploradores,
        labels_plan=labels_plan,
        values_plan=values_plan,
        labels_pref=labels_pref,
        values_pref=values_pref,
        logs=logs,
        acciones_labels=acciones_labels,
        acciones_values=acciones_values 
    )

# --- Ver detalles de un emprendimiento ---
@app.route('/emprendimiento/<int:id>')
def ver_emprendimiento(id):
    e = Emprendedor.query.get_or_404(id)
    return render_template('Emprededores/ver_emprendimiento.html', e=e)

# --- Ver detalles de un explorador ---
@app.route('/explorador/<int:id>')
def ver_explorador(id):
    explorador = Explorador.query.get_or_404(id)
    return render_template('Explorador/ver_explorador.html', explorador=explorador)


# --- Eliminar emprendimiento ---
@app.route('/eliminar_emprendimiento/<int:id>', methods=['POST'])
def eliminar_emprendimiento(id):
    emprendimiento = Emprendedor.query.get_or_404(id)
    user = emprendimiento.user  # Obtiene el usuario asociado

    # Registrar en auditoría antes de eliminar
    log = LogAccion(
        accion='Eliminación',
        entidad_id=user.id,
        detalles=f'Se eliminó el usuario "{user.username}" asociado al emprendimiento "{emprendimiento.nombre_emprendimiento}".'
    )
    db.session.add(log)

    db.session.delete(user)  # Borra también el usuario
    db.session.commit()

    flash('Emprendimiento eliminado completamente.', 'success')
    return redirect(url_for('admin_dashboard'))


# --- Editar emprendimiento ---
@app.route('/editar_emprendimiento/<int:id>', methods=['POST'])
def editar_emprendimiento(id):
    e = Emprendedor.query.get_or_404(id)

    # Guardar datos anteriores para comparar
    datos_antes = {
        "nombre_emprendimiento": e.nombre_emprendimiento,
        "nit": e.nit,
        "zona": e.zona,
        "ubicacion": e.ubicacion,
        "plan": e.plan,
        "clasificacion": e.clasificacion
    }

    # Actualizar datos
    e.nombre_emprendimiento = request.form.get('nombre_emprendimiento', e.nombre_emprendimiento)
    e.nit = request.form.get('nit', e.nit)
    e.zona = request.form.get('zona', e.zona)
    e.ubicacion = request.form.get('ubicacion', e.ubicacion)
    e.plan = request.form.get('plan', e.plan)
    e.clasificacion = request.form.get('clasificacion', e.clasificacion)

    # Guardar cambios
    db.session.commit()

    # Comparar y generar detalle de los cambios
    cambios = []
    for campo, valor_anterior in datos_antes.items():
        nuevo_valor = getattr(e, campo)
        if valor_anterior != nuevo_valor:
            cambios.append(f"{campo}: '{valor_anterior}' → '{nuevo_valor}'")

    detalles = ", ".join(cambios) if cambios else "Sin cambios detectados"

    # 🔹 Registrar auditoría
    log = LogAccion(
        accion="Edición de Emprendedor",
        entidad_id=e.id,
        detalles=f"Se editaron los datos del emprendimiento '{e.nombre_emprendimiento}'. Cambios: {detalles}"
    )
    db.session.add(log)
    db.session.commit()

    flash('Información actualizada correctamente.', 'success')
    return redirect(url_for('admin_dashboard'))

# --- Eliminar explorador ---
@app.route('/eliminar_explorador/<int:id>', methods=['POST'])
def eliminar_explorador(id):
    explorador = Explorador.query.get_or_404(id)
    user = explorador.user  # Obtiene el usuario asociado

    # Registrar en auditoría antes de eliminar
    log = LogAccion(
        accion='Eliminación',
        entidad_id=user.id,
        detalles=f'Se eliminó el usuario "{user.username}" asociado al explorador "{explorador.primer_nombre,explorador.primer_apellido}".'
    )
    db.session.add(log)

    db.session.delete(user)  # Esto elimina al usuario y en cascada su registro de explorador
    db.session.commit()

    flash('Explorador eliminado completamente.', 'success')
    return redirect(url_for('admin_dashboard'))


# EDITAR EXPLORADOR
@app.route('/editar_explorador/<int:id>', methods=['POST'])
def editar_explorador(id):
    explorador = Explorador.query.get_or_404(id)

    # Guardar datos previos
    datos_antes = {
        "primer_nombre": explorador.primer_nombre,
        "segundo_nombre": explorador.segundo_nombre,
        "primer_apellido": explorador.primer_apellido,
        "segundo_apellido": explorador.segundo_apellido,
        "telefono": explorador.telefono,
        "fecha_nacimiento": explorador.fecha_nacimiento
    }

    # Actualizar campos
    explorador.primer_nombre = request.form.get('primer_nombre', explorador.primer_nombre)
    explorador.segundo_nombre = request.form.get('segundo_nombre', explorador.segundo_nombre)
    explorador.primer_apellido = request.form.get('primer_apellido', explorador.primer_apellido)
    explorador.segundo_apellido = request.form.get('segundo_apellido', explorador.segundo_apellido)
    explorador.telefono = request.form.get('telefono', explorador.telefono)

    fecha_str = request.form.get('fecha_nacimiento')
    if fecha_str:
        try:
            if isinstance(fecha_str, str):
                explorador.fecha_nacimiento = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            else:
                explorador.fecha_nacimiento = fecha_str
        except Exception as e:
            flash(f'Error en la fecha ({e}). Usa el formato AAAA-MM-DD.', 'danger')
            return redirect(url_for('admin_dashboard'))

    try:
        db.session.commit()

        # Comparar cambios
        cambios = []
        for campo, valor_anterior in datos_antes.items():
            nuevo_valor = getattr(explorador, campo)
            if valor_anterior != nuevo_valor:
                cambios.append(f"{campo}: '{valor_anterior}' → '{nuevo_valor}'")

        detalles = ", ".join(cambios) if cambios else "Sin cambios detectados"

        # 🔹 Registrar auditoría
        log = LogAccion(
            accion="Edición de Explorador",
            entidad_id=explorador.id,
            detalles=f"Se editaron los datos del explorador '{explorador.primer_nombre} {explorador.primer_apellido}'. Cambios: {detalles}"
        )
        db.session.add(log)
        db.session.commit()

        flash('Explorador actualizado correctamente.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar: {e}', 'danger')

    return redirect(url_for('admin_dashboard'))


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