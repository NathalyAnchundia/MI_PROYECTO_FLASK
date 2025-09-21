from flask import Flask, render_template, redirect, url_for, flash, request
from datetime import datetime
from modelos import db, Producto, Cliente
from formularios import ProductoForm, ClienteForm
from inventario import Inventario
from persistencia import (
    guardar_productos_txt, leer_productos_txt,
    guardar_productos_json, leer_productos_json,
    guardar_productos_csv, leer_productos_csv
)
from sqlalchemy.exc import IntegrityError
import os

app = Flask(__name__)

# Configuración para usar carpeta 'instance' donde está inventario.db
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'inventario.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key'  # Cambiar en producción

db.init_app(app)

# Context processor para tener la fecha/hora actual disponible en templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

with app.app_context():
    db.create_all()
    inventario = Inventario.cargar_desde_bd()


# --- Rutas principales ---

@app.route('/')
def index():
    return render_template('index.html', title='Inicio')


@app.route('/leer-datos')
def leer_datos():
    # Página con opciones para guardar y cargar productos en diferentes formatos
    return render_template('leer_datos.html', title='Leer datos')


@app.route('/usuario/<nombre>')
def usuario(nombre):
    return f'Bienvenido, {nombre}!'


@app.route('/about/')
def about():
    return render_template('about.html', title='Acerca de')


# --- Productos ---

@app.route('/productos')
def listar_productos():
    q = request.args.get('q', '').strip()
    productos = inventario.buscar_por_nombre(q) if q else inventario.listar_todos()
    return render_template('productos/lista.html', title='Productos', productos=productos, q=q)


@app.route('/productos/nuevo', methods=['GET', 'POST'])
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        try:
            inventario.agregar(
                nombre=form.nombre.data.strip(),
                cantidad=form.cantidad.data,
                precio=form.precio.data
            )
            flash('Producto agregado correctamente.', 'success')
            return redirect(url_for('listar_productos'))
        except ValueError as e:
            form.nombre.errors.append(str(e))
    return render_template('productos/formulario.html', title='Nuevo producto', form=form, modo='crear')


@app.route('/productos/<int:pid>/editar', methods=['GET', 'POST'])
def editar_producto(pid):
    producto = Producto.query.get_or_404(pid)
    form = ProductoForm(obj=producto)
    if form.validate_on_submit():
        try:
            inventario.actualizar(
                id=pid,
                nombre=form.nombre.data.strip(),
                cantidad=form.cantidad.data,
                precio=form.precio.data
            )
            flash('Producto actualizado.', 'success')
            return redirect(url_for('listar_productos'))
        except ValueError as e:
            form.nombre.errors.append(str(e))
    return render_template('productos/formulario.html', title='Editar producto', form=form, modo='editar')


@app.route('/productos/<int:pid>/eliminar', methods=['POST'])
def eliminar_producto(pid):
    ok = inventario.eliminar(pid)
    flash('Producto eliminado.' if ok else 'Producto no encontrado.', 'info' if ok else 'warning')
    return redirect(url_for('listar_productos'))


# --- Clientes ---

@app.route('/clientes')
def listar_clientes():
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template('clientes/lista.html', title='Clientes', clientes=clientes)


@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def crear_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        nuevo_cliente = Cliente(
            nombre=form.nombre.data.strip(),
            direccion=form.direccion.data.strip(),
            correo_electronico=form.correo_electronico.data.strip()
        )
        db.session.add(nuevo_cliente)
        try:
            db.session.commit()
            flash('Cliente agregado correctamente.', 'success')
            return redirect(url_for('listar_clientes'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: el correo electrónico ya existe.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error inesperado: {str(e)}', 'danger')
    return render_template('clientes/formulario.html', title='Nuevo cliente', form=form, modo='crear')


@app.route('/clientes/<int:cid>/editar', methods=['GET', 'POST'])
def editar_cliente(cid):
    cliente = Cliente.query.get_or_404(cid)
    form = ClienteForm(obj=cliente)
    if form.validate_on_submit():
        cliente.nombre = form.nombre.data.strip()
        cliente.direccion = form.direccion.data.strip()
        cliente.correo_electronico = form.correo_electronico.data.strip()
        try:
            db.session.commit()
            flash('Cliente actualizado correctamente.', 'success')
            return redirect(url_for('listar_clientes'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: el correo electrónico ya existe.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error inesperado: {str(e)}', 'danger')
    return render_template('clientes/formulario.html', title='Editar cliente', form=form, modo='editar')


# --- Guardar productos en archivos ---

@app.route('/productos/txt/guardar', methods=['POST'])
def guardar_txt():
    productos = [{'id': p.id, 'nombre': p.nombre, 'cantidad': p.cantidad, 'precio': p.precio} for p in Producto.query.all()]
    guardar_productos_txt(productos)
    flash('Productos guardados en TXT', 'success')
    return redirect(url_for('listar_productos'))


@app.route('/productos/json/guardar', methods=['POST'])
def guardar_json():
    productos = [{'id': p.id, 'nombre': p.nombre, 'cantidad': p.cantidad, 'precio': p.precio} for p in Producto.query.all()]
    guardar_productos_json(productos)
    flash('Productos guardados en JSON', 'success')
    return redirect(url_for('listar_productos'))


@app.route('/productos/csv/guardar', methods=['POST'])
def guardar_csv():
    productos = [{'id': p.id, 'nombre': p.nombre, 'cantidad': p.cantidad, 'precio': p.precio} for p in Producto.query.all()]
    guardar_productos_csv(productos)
    flash('Productos guardados en CSV', 'success')
    return redirect(url_for('listar_productos'))


# --- Cargar y mostrar contenido crudo de archivos ---

@app.route('/productos/txt/cargar')
def cargar_txt():
    """Leer contenido crudo del archivo TXT y mostrarlo en pantalla sin formatear"""
    archivo = os.path.join(basedir, 'instance', 'productos.txt')
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
    except FileNotFoundError:
        contenido = "⚠️ Archivo productos.txt no encontrado."
    
    # Respuesta HTML con contenido crudo en etiqueta <pre>
    return f"""
    <html>
        <head>
            <title>Contenido TXT</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>📄 Contenido crudo desde archivo TXT</h1>
            <pre style="background:#f9f9f9; padding:1em; border:1px solid #ccc;">{contenido}</pre>
            <p><a href="{url_for('leer_datos')}">⬅️ Volver</a></p>
        </body>
    </html>
    """


@app.route('/productos/json/cargar')
def cargar_json():
    """Leer contenido crudo del archivo JSON y mostrarlo en pantalla sin formatear"""
    archivo = os.path.join(basedir, 'instance', 'productos.json')
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
    except FileNotFoundError:
        contenido = "⚠️ Archivo productos.json no encontrado."

    return f"""
    <html>
        <head>
            <title>Contenido JSON</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>📄 Contenido crudo desde archivo JSON</h1>
            <pre style="background:#f9f9f9; padding:1em; border:1px solid #ccc;">{contenido}</pre>
            <p><a href="{url_for('leer_datos')}">⬅️ Volver</a></p>
        </body>
    </html>
    """


@app.route('/productos/csv/cargar')
def cargar_csv():
    """Leer contenido crudo del archivo CSV y mostrarlo en pantalla sin formatear"""
    archivo = os.path.join(basedir, 'instance', 'productos.csv')
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
    except FileNotFoundError:
        contenido = "⚠️ Archivo productos.csv no encontrado."

    return f"""
    <html>
        <head>
            <title>Contenido CSV</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>📄 Contenido crudo desde archivo CSV</h1>
            <pre style="background:#f9f9f9; padding:1em; border:1px solid #ccc;">{contenido}</pre>
            <p><a href="{url_for('leer_datos')}">⬅️ Volver</a></p>
        </body>
    </html>
    """

# -------------------- FUNCIONES DE COMPRA --------------------

@app.route('/productos/<int:pid>/comprar', methods=['POST'])
@login_required
def comprar_producto(pid):
    if current_user.es_admin():
        flash('Los administradores no pueden comprar productos.', 'warning')
        return redirect(url_for('listar_productos'))

    try:
        cantidad = int(request.form.get('cantidad', 1))
        if cantidad < 1:
            raise ValueError
    except ValueError:
        flash('Cantidad inválida.', 'danger')
        return redirect(url_for('listar_productos'))

    conn = conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, cantidad AS disponible FROM productos WHERE id = %s", (pid,))
    producto = cursor.fetchone()

    if not producto:
        cerrar_conexion(conn)
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('listar_productos'))

    if producto['disponible'] < cantidad:
        cerrar_conexion(conn)
        flash(f'Solo quedan {producto["disponible"]} unidades.', 'warning')
        return redirect(url_for('listar_productos'))

    try:
        cursor.execute(
            "INSERT INTO compras (usuario_id, producto_id, cantidad) VALUES (%s, %s, %s)",
            (current_user.id, pid, cantidad)
        )
        cursor.execute(
            "UPDATE productos SET cantidad = cantidad - %s WHERE id = %s",
            (cantidad, pid)
        )
        conn.commit()
        flash(f'Compra realizada: {cantidad} unidad(es) de "{producto["nombre"]}".', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al registrar la compra: {str(e)}', 'danger')
    finally:
        cerrar_conexion(conn)

    return redirect(url_for('listar_productos'))

@app.route('/mis-compras')
@login_required
def mis_compras():
    conn = conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id, p.nombre AS producto, c.cantidad, c.fecha
        FROM compras c
        JOIN productos p ON c.producto_id = p.id
        WHERE c.usuario_id = %s
        ORDER BY c.fecha DESC
    """, (current_user.id,))
    compras = cursor.fetchall()
    cerrar_conexion(conn)
    return render_template('compras/mis_compras.html', compras=compras)

# -------------------- DASHBOARD --------------------

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.es_admin():
        conn = conexion()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM productos")
        total_productos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM compras")
        total_compras = cursor.fetchone()[0]

        cerrar_conexion(conn)

        return render_template('dashboard.html',
                               nombre=current_user.nombre,
                               es_admin=True,
                               total_productos=total_productos,
                               total_usuarios=total_usuarios,
                               total_compras=total_compras)

    # Usuario normal
    return render_template('dashboard.html',
                           nombre=current_user.nombre,
                           es_admin=False)

# -------------------- AUTENTICACIÓN --------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, email, password, rol FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        cerrar_conexion(conn)

        if usuario and check_password_hash(usuario[3], password):
            user = Usuario(*usuario)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO usuarios (nombre, email, password, rol) VALUES (%s, %s, %s, %s)",
                           (nombre, email, password, 'user'))
            conn.commit()
            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'danger')
        finally:
            cerrar_conexion(conn)

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

#carrito de compras
# Añadir producto al carrito
@app.route('/agregar_al_carrito/<int:pid>', methods=['POST'])
@login_required
def agregar_al_carrito(pid):
    try:
        cantidad = int(request.form.get('cantidad', 1))
        if cantidad < 1:
            raise ValueError
    except ValueError:
        flash('Cantidad inválida.', 'danger')
        return redirect(url_for('listar_productos'))

    conn = conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, precio, cantidad FROM productos WHERE id = %s", (pid,))
    producto = cursor.fetchone()
    cerrar_conexion(conn)

    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('listar_productos'))

    if producto['cantidad'] < cantidad:
        flash(f'Solo quedan {producto["cantidad"]} unidades disponibles.', 'warning')
        return redirect(url_for('listar_productos'))

    carrito = session.get('carrito', {})

    if str(pid) in carrito:
        carrito[str(pid)]['cantidad'] += cantidad
    else:
        carrito[str(pid)] = {
            'id': producto['id'],
            'nombre': producto['nombre'],
            'precio': float(producto['precio']),
            'cantidad': cantidad
        }

    session['carrito'] = carrito
    flash(f'Se agregaron {cantidad} unidad(es) de "{producto["nombre"]}" al carrito.', 'success')
    return redirect(url_for('listar_productos'))


# Mostrar carrito
@app.route('/carrito')
@login_required
def carrito():
    carrito = session.get('carrito', {})
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())
    return render_template('carrito.html', carrito=carrito, total=total)


# Eliminar producto del carrito
@app.route('/carrito/eliminar/<int:producto_id>')
@login_required
def eliminar(producto_id):
    carrito = session.get('carrito', {})
    pid = str(producto_id)
    if pid in carrito:
        carrito.pop(pid)
        session['carrito'] = carrito
        flash('Producto eliminado del carrito.', 'success')
    else:
        flash('Producto no encontrado en el carrito.', 'warning')
    return redirect(url_for('carrito'))


# Vaciar carrito
@app.route('/carrito/vaciar')
@login_required
def vaciar():
    session['carrito'] = {}
    flash('Carrito vaciado.', 'success')
    return redirect(url_for('carrito'))

@app.route('/carrito/comprar', methods=['POST'])
@login_required
def comprar_carrito():
    if current_user.es_admin():
        flash('Los administradores no pueden comprar productos.', 'warning')
        return redirect(url_for('listar_productos'))

    carrito = session.get('carrito', {})
    if not carrito:
        flash('El carrito está vacío.', 'warning')
        return redirect(url_for('carrito'))

    conn = conexion()
    cursor = conn.cursor(dictionary=True)

    # Validar disponibilidad de cada producto antes de comprar
    for pid_str, item in carrito.items():
        pid = int(pid_str)
        cursor.execute("SELECT cantidad FROM productos WHERE id = %s", (pid,))
        producto_db = cursor.fetchone()
        if not producto_db:
            cerrar_conexion(conn)
            flash(f'El producto "{item["nombre"]}" no existe.', 'danger')
            return redirect(url_for('carrito'))
        if producto_db['cantidad'] < item['cantidad']:
            cerrar_conexion(conn)
            flash(f'Solo quedan {producto_db["cantidad"]} unidades disponibles de "{item["nombre"]}".', 'warning')
            return redirect(url_for('carrito'))

    # Si todo está ok, insertar compras y actualizar inventario
    try:
        for pid_str, item in carrito.items():
            pid = int(pid_str)
            cantidad = item['cantidad']

            cursor.execute(
                "INSERT INTO compras (usuario_id, producto_id, cantidad) VALUES (%s, %s, %s)",
                (current_user.id, pid, cantidad)
            )
            cursor.execute(
                "UPDATE productos SET cantidad = cantidad - %s WHERE id = %s",
                (cantidad, pid)
            )
        conn.commit()
        session['carrito'] = {}  # Vaciar carrito al completar compra
        flash('Compra realizada con éxito.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al realizar la compra: {str(e)}', 'danger')
    finally:
        cerrar_conexion(conn)

    return redirect(url_for('listar_productos'))

# --- Ejecutar la app ---

if __name__ == '__main__':
    app.run(debug=True)
