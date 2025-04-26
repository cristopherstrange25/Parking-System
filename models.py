from extensions import db
from flask_login import UserMixin

# Clase User
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    foto_blob = db.Column(db.LargeBinary, nullable=True)  # Guardar la imagen como BLOB

    # Relación con Estacionamiento (un usuario puede tener múltiples estacionamientos)
    # Cambié 'usuario' a 'estacionamientos_usuario' para evitar el conflicto de nombre
    estacionamientos = db.relationship('Estacionamiento', backref='estacionamientos_usuario', lazy=True)

# Clase Estacionamiento
class Estacionamiento(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ubicacion = db.Column(db.String(255), nullable=False)  # Dirección o coordenadas
    estado = db.Column(db.String(20), nullable=False, default="available")  # "available", "reserved", "occupied"
    hora_reservacion = db.Column(db.DateTime, nullable=True)  # Puede ser null si no está reservado
    hora_liberacion = db.Column(db.DateTime, nullable=True) 
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    # Definición correcta de la clave foránea
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Usuario que reserva

    def __repr__(self):
        return f'<Estacionamiento {self.id}, {self.ubicacion}, {self.estado}>'

# En models.py
class Pagos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    estacionamiento_id = db.Column(db.Integer, db.ForeignKey('estacionamiento.id'), nullable=False)
    metodo_pago = db.Column(db.String(20), nullable=False)
    nombre_tarjeta = db.Column(db.String(100))  # Nuevo campo
    numero_tarjeta = db.Column(db.String(16))   # Nuevo campo
    nombre_paypal = db.Column(db.String(100))
    correo_paypal = db.Column(db.String(100))
    cvv = db.Column(db.String(3))               # Cambiado de codigo_seguridad
    fecha_vencimiento = db.Column(db.String(5)) # Cambiado de fecha_exp
    monto_total = db.Column(db.Float, nullable=False)
    fecha_pago = db.Column(db.DateTime, nullable=False)
    estado_pago = db.Column(db.String(20), nullable=False)
    qr_blob = db.Column(db.LargeBinary, nullable=True)
