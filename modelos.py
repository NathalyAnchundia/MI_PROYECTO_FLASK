from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=0)
    precio = db.Column(db.Float, nullable=False, default=0.0)  # para demo

    def __repr__(self):
        return f'<Producto {self.id} {self.nombre}>'

    def to_tuple(self):
        # ejemplo de tupla: (id, nombre, cantidad, precio)
        return (self.id, self.nombre, self.cantidad, self.precio)
    
# modelos para clientes.
class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    correo_electronico = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<Cliente {self.id} {self.nombre}>'

    def to_tuple(self):
        # ejemplo de tupla: (id, nombre, direccion, correo_electronico)
        return (self.id, self.nombre, self.direccion, self.correo_electronico) 