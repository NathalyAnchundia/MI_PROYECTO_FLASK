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


# --- Ejecutar la app ---

if __name__ == '__main__':
    app.run(debug=True)
