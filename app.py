from flask import Flask, render_template, request, redirect, url_for, flash, session
from extensions import db  # Importar desde extensions
import bcrypt
from werkzeug.utils import secure_filename
from models import User, Estacionamiento, Pagos
import os
import base64
import bcrypt
from flask import jsonify
from datetime import timezone, datetime, date, timedelta
import math
import qrcode
from io import BytesIO
import re, base64

# Precio por hora
PRECIO_POR_HORA = 15
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY1', 'dev-secret-key-123')
# Configurar la base de datos con SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/estacionamiento'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Carpeta donde guardarás las fotos
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Inicializar db con la aplicación
db.init_app(app)
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'pdf')

import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary import uploader


# Configuración con tus credenciales
cloudinary.config(
  cloud_name = "dcndmmy9m",
  api_key = "***oculto***",
  api_secret = "***oculto***"
)


# En tu aplicación Flask
from twilio.rest import Client



# Configura tus credenciales de Twilio
TWILIO_ACCOUNT_SID = '***oculto***'
TWILIO_AUTH_TOKEN = '***oculto***'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# Importar modelos después de inicializar db
from models import User

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Ruta de registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        codigo = request.form['codigo']
        username = request.form['nombre']
        email = request.form['correo']
        password = request.form['password'].encode('utf-8')
        confirm_password = request.form['confirm-password']

        if password.decode('utf-8') != confirm_password:
            flash('Las contraseñas no coinciden. Intenta nuevamente.', 'danger')
            return render_template('register.html')

        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        file = request.files['foto']
        if file and allowed_file(file.filename):
            foto_blob = file.read()  # Leer la imagen en binario
        else:
            foto_blob = None

        new_user = User(
            codigo=codigo,
            nombre=username,
            correo=email,
            password=hashed_password.decode('utf-8'),
            foto_blob=foto_blob
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registro exitoso! Por favor inicia sesión.', 'success')
         #   return redirect(url_for('user_data')) 
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar el usuario. Intenta nuevamente.', 'danger')
            print(e)

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['correo']
        password = request.form['password'].encode('utf-8')

        user = User.query.filter_by(correo=email).first()  # Buscar el usuario por correo
        if user and bcrypt.checkpw(password, user.password.encode('utf-8')):  # Verificar la contraseña
            session['usuario_id'] = user.id  # Aquí guardas el ID del usuario            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('parking', codigo=user.id))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
            return render_template('login.html')  # Volver a mostrar el formulario de login

    return render_template('login.html') 

@app.route('/parking', methods=['GET'])
def parking():
    codigo = session.get('usuario_id')
    parking_spots = Estacionamiento.query.filter_by(usuario_id=codigo).order_by(Estacionamiento.id).all()
    parking_spots = Estacionamiento.query.order_by(Estacionamiento.id).all()
    return render_template('parking.html', parking_spots=parking_spots)



# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/user')
def user_data():
    # Buscar el usuario en la base de datos usando SQLAlchemy
    usuario_id = session.get('usuario_id')

    if usuario_id:
        user = User.query.get(usuario_id)  # Obtener el objeto User con el ID de la sesión

        if user:
            # Convertir la imagen a base64 si existe
            foto_data = base64.b64encode(user.foto_blob).decode('utf-8') if user.foto_blob else None

            return render_template(
                'datos_usuario.html', 
                codigo=user.codigo,
                nombre=user.nombre,
                correo=user.correo,
                password=user.password,
                foto_data=foto_data
            )
        else:
            flash("Usuario no encontrado", "danger")
            return redirect(url_for('dashboard'))
    else:
        flash("Usuario no autenticado", "danger")
        return redirect(url_for('login'))


@app.route('/mostrar-sesion', methods=['GET'])
def mostrar_sesion():
    return jsonify({'usuario_id': session.get('usuario_id')})

@app.route('/info')
def info():
    # Supongamos que necesitas pasar un nombre o una fecha
    ubicacion = session.get('ubicacion', 'No seleccionada') 
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    return render_template('info.html', fecha=fecha, ubicacion=ubicacion)

@app.route('/calcular', methods=['POST'])
def calcular_total():
    # Obtener las horas de inicio y finalización del formulario
    hora_inicio = request.form['hora_inicio']
    hora_fin = request.form['hora_fin']
    
    # Convertir las horas a objetos de datetime para hacer la resta
    hora_inicio = datetime.strptime(hora_inicio, '%H:%M')
    hora_fin = datetime.strptime(hora_fin, '%H:%M')
    
    # Calcular la diferencia de horas en minutos
    diferencia = (hora_fin - hora_inicio).total_seconds() / 3600  # Resultado en horas
    
    # Redondear hacia arriba el número de horas
    horas_redondeadas = round(diferencia)
    
    # Calcular el total a pagar
    total = horas_redondeadas * PRECIO_POR_HORA
    
    # Pasar el total a la plantilla
    return render_template('info.html', total=total)

@app.route('/credito')
def credit():
    hora_inicio = request.args.get('hora_inicio')
    hora_fin = request.args.get('hora_fin')
    total = request.args.get('total', '0.00')
    
    # Validar parámetros
    if not all([hora_inicio, hora_fin, total]):
        flash('Datos incompletos', 'danger')
        return redirect(url_for('info'))
    
    return render_template('credit.html', 
                         hora_inicio=hora_inicio,
                         hora_fin=hora_fin,
                         total=total)

# Hacer lo mismo para las rutas debito y paypal

@app.route('/debito')
def debit():
    hora_inicio = request.args.get('hora_inicio')
    hora_fin = request.args.get('hora_fin')
    total = request.args.get('total', '0.00') 

        # Validar parámetros
    if not all([hora_inicio, hora_fin, total]):
        flash('Datos incompletos', 'danger')
        return redirect(url_for('info'))
    
    return render_template('debito.html', 
                         hora_inicio=hora_inicio,
                         hora_fin=hora_fin,
                         total=total)

@app.route('/paypal')
def paypal():
    hora_inicio = request.args.get('hora_inicio')
    hora_fin = request.args.get('hora_fin')
    total = request.args.get('total', '0.00') 
    return render_template('paypal.html', 
                         hora_inicio=hora_inicio,
                         hora_fin=hora_fin,
                         total=total)

@app.route('/procesar-pago', methods=['POST'])
def procesar_pago():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    estacionamiento_id = session.get('estacionamiento_id')
    if not estacionamiento_id:
        flash('No hay espacio reservado', 'danger')
        return redirect(url_for('info'))

    try:
        # Obtener datos del formulario
        metodo_pago = request.form.get('metodo_pago')
        nombre_titular = request.form.get('nombre_titular')
        numero_tarjeta = request.form.get('numero_tarjeta')
        fecha_exp = request.form.get('fecha_exp')
        codigo_seguridad = request.form.get('codigo_seguridad')
        hora_inicio = request.form.get('hora_inicio')
        hora_fin = request.form.get('hora_fin')
        total = float(request.form.get('total', 0))

        # Validar campos obligatorios
        if not all([metodo_pago, nombre_titular, numero_tarjeta, fecha_exp, codigo_seguridad]):
            flash('Faltan datos obligatorios', 'danger')
            return redirect(url_for('info'))

        # Obtener instancias
        estacionamiento = Estacionamiento.query.get(estacionamiento_id)
        usuario = User.query.get(session['usuario_id'])
        
        if not estacionamiento or not usuario:
            flash('Datos no encontrados', 'danger')
            return redirect(url_for('info'))

        # Convertir horas
        fecha_actual = date.today()
        hora_reserva = datetime.combine(fecha_actual, datetime.strptime(hora_inicio, '%H:%M').time())
        hora_liberacion = datetime.combine(fecha_actual, datetime.strptime(hora_fin, '%H:%M').time())

        # Crear registro de pago
        nuevo_pago = Pagos(
            usuario_id=session['usuario_id'],
            estacionamiento_id=estacionamiento_id,
            metodo_pago=metodo_pago,
            nombre_tarjeta=nombre_titular,
            numero_tarjeta=numero_tarjeta[-4:],
            cvv=codigo_seguridad,
            fecha_vencimiento=fecha_exp,
            monto_total=total,
            fecha_pago=datetime.now(),
            estado_pago='completado'
        )

        # Generar QR
        qr_data = f"""
        Comprobante de Pago - Estacionamiento
        Usuario: {usuario.nombre}
        Fecha: {nuevo_pago.fecha_pago.strftime('%d/%m/%Y %H:%M')}
        Lugar: {estacionamiento.ubicacion}
        Total: ${nuevo_pago.monto_total:.2f}
        """
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        nuevo_pago.qr_blob = buffered.getvalue()

        # Actualizar espacio
        estacionamiento.estado = 'occupied'
        estacionamiento.hora_reservacion = hora_reserva
        estacionamiento.hora_liberacion = hora_liberacion

        # Guardar cambios
        db.session.add(nuevo_pago)
        db.session.add(estacionamiento)
        db.session.commit()

        session.pop('estacionamiento_id', None)
        flash('Pago registrado exitosamente', 'success')
        return redirect(url_for('comprobante'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar el pago: {str(e)}', 'danger')
        print(f"Error: {str(e)}")
        return redirect(url_for('info'))

@app.route('/procesar-pago2', methods=['POST'])
def procesar_pago2():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    estacionamiento_id = session.get('estacionamiento_id')
    if not estacionamiento_id:
        flash('No hay espacio reservado', 'danger')
        return redirect(url_for('info'))

    try:
        # Obtener datos del formulario
        metodo_pago = request.form.get('metodo_pago')
        nombre_paypal = request.form.get('nombre_paypal')
        correo_paypal = request.form.get('correo_paypal')
        hora_inicio = request.form.get('hora_inicio')
        hora_fin = request.form.get('hora_fin')
        total = float(request.form.get('total', 0))

        # Validar campos
        if not all([metodo_pago, nombre_paypal, correo_paypal]):
            flash('Faltan datos obligatorios', 'danger')
            return redirect(url_for('info'))

        # Obtener instancias
        estacionamiento = Estacionamiento.query.get(estacionamiento_id)
        usuario = User.query.get(session['usuario_id'])
        
        if not estacionamiento or not usuario:
            flash('Datos no encontrados', 'danger')
            return redirect(url_for('info'))

        # Convertir horas
        fecha_actual = date.today()
        hora_reserva = datetime.combine(fecha_actual, datetime.strptime(hora_inicio, '%H:%M').time())
        hora_liberacion = datetime.combine(fecha_actual, datetime.strptime(hora_fin, '%H:%M').time())

        # Crear registro de pago
        nuevo_pago = Pagos(
            usuario_id=session['usuario_id'],
            estacionamiento_id=estacionamiento_id,
            metodo_pago=metodo_pago,
            nombre_paypal=nombre_paypal,
            correo_paypal=correo_paypal,
            monto_total=total,
            fecha_pago=datetime.now(),
            estado_pago='completado'
        )

        # Generar QR (mismo proceso que en el otro método)
        qr_data = f"""
        Comprobante de Pago - Estacionamiento
        Usuario: {usuario.nombre}
        Fecha: {nuevo_pago.fecha_pago.strftime('%d/%m/%Y %H:%M')}
        Lugar: {estacionamiento.ubicacion}
        Total: ${nuevo_pago.monto_total:.2f}
        """
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        nuevo_pago.qr_blob = buffered.getvalue()

        # Actualizar espacio
        estacionamiento.estado = 'occupied'
        estacionamiento.hora_reservacion = hora_reserva
        estacionamiento.hora_liberacion = hora_liberacion

        # Guardar cambios
        db.session.add(nuevo_pago)
        db.session.add(estacionamiento)
        db.session.commit()

        session.pop('estacionamiento_id', None)
        flash('Pago registrado exitosamente', 'success')
        return redirect(url_for('comprobante'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar el pago: {str(e)}', 'danger')
        print(f"Error: {str(e)}")
        return redirect(url_for('info'))

@app.route('/comprobante')
def comprobante():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Obtener el último pago del usuario
    ultimo_pago = Pagos.query.filter_by(usuario_id=session['usuario_id'])\
                            .order_by(Pagos.fecha_pago.desc())\
                            .first()
    
    if not ultimo_pago:
        flash('No se encontró ningún pago', 'danger')
        return redirect(url_for('parking'))
    
    # Obtener datos del usuario y estacionamiento
    usuario = User.query.get(session['usuario_id'])
    estacionamiento = Estacionamiento.query.get(ultimo_pago.estacionamiento_id)
    
    # Generar QR
    qr_data = f"""
    Comprobante de Pago - Estacionamiento
    Usuario: {usuario.nombre}
    Fecha: {ultimo_pago.fecha_pago.strftime('%d/%m/%Y %H:%M')}
    Lugar: {estacionamiento.ubicacion}
    Total: ${ultimo_pago.monto_total:.2f}
    """
    if ultimo_pago.qr_blob:
        img_str = base64.b64encode(ultimo_pago.qr_blob).decode()
    else:
        img_str = None
    
    return render_template('comprobante.html',
                         usuario=usuario,
                         pago=ultimo_pago,
                         estacionamiento=estacionamiento,
                         qr_code=img_str)

@app.route('/actualizar-estado', methods=['POST'])
def actualizar_estado():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'success': False, 'error': 'Usuario no autenticado'}), 401

    data = request.get_json()
    spot = Estacionamiento.query.get(data['id'])
    
    if not spot:
        return jsonify({'success': False, 'error': 'Espacio no encontrado'}), 404
    
    # Estados que no permiten modificación por usuarios
    if spot.estado in ['disabled', 'temporarily-closed', 'executive']:
        return jsonify({'success': False, 'error': 'Estado no modificable'}), 400
    
    # Validar permisos para modificar reservas existentes
    if spot.estado == 'reserved' and spot.usuario_id != usuario_id:
        return jsonify({'success': False, 'error': 'Acceso no autorizado'}), 403

    nuevo_estado = data['nuevoEstado']
    
    with db.session.begin_nested():
        try:
            # Si el nuevo estado es "reserved"
            if nuevo_estado == 'reserved':
                session['estacionamiento_id'] = spot.id
                session['ubicacion'] = spot.ubicacion 
                # Liberar todas las reservas previas del usuario
                reservas_previas = Estacionamiento.query.filter_by(
                    usuario_id=usuario_id, 
                    estado='reserved'
                ).all()
                
                for reserva in reservas_previas:
                    reserva.estado = 'available'
                    reserva.usuario_id = None  # Limpiar usuario
                    db.session.add(reserva)
                    reserva.hora_reservacion = None 
                
                # Asignar nuevo espacio
                spot.usuario_id = usuario_id
                spot.hora_reservacion = datetime.now(timezone.utc) 
            else:
                # Cualquier otro estado debe limpiar el usuario_id
                spot.usuario_id = None  # <--- Aquí se fuerza el NULL

            spot.estado = nuevo_estado
            db.session.add(spot)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({
        'success': True,
        'nuevoEstado': spot.estado,
        'usuario_id': spot.usuario_id  # Será null si no es reserved
    })

from datetime import datetime, timedelta
import pytz

@app.route('/get-reservation-time')
def get_reservation_time():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    reserva = Estacionamiento.query.filter_by(
        usuario_id=session['usuario_id'],
        estado='occupied'  # Asegurar que solo busca reservas activas
    ).first()

    if reserva and reserva.hora_reservacion:
        # Convertir a UTC si no está en esa zona horaria
        reserva_time = reserva.hora_reservacion.astimezone(timezone.utc)
        ahora_utc = datetime.now(timezone.utc)
        
        tiempo_transcurrido = (ahora_utc - reserva_time).total_seconds()
        print("ahora:"+str(ahora_utc))
        print("Reserva"+str(reserva_time))
        print("transcurrido"+str(tiempo_transcurrido))


        if tiempo_transcurrido > 900:
            reserva.estado = 'available'
            reserva.usuario_id = None
            reserva.hora_reservacion = None
            db.session.commit()
            return jsonify({'reservation_end': None})

        hora_fin = reserva_time + timedelta(seconds=900)
        return jsonify({
            'reservation_end': hora_fin.strftime('%Y-%m-%dT%H:%M:%SZ')
        })

    return jsonify({'reservation_end': None})

@app.route('/confirm-arrival', methods=['POST'])
def confirm_arrival():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    reserva = Estacionamiento.query.filter_by(
        usuario_id=session['usuario_id'],
        estado='occupied'
    ).first()
    
    if reserva:
        try:
            # Convertir a UTC
            hora_liberacion = reserva.hora_liberacion.astimezone(timezone.utc)
            ahora_utc = datetime.now(timezone.utc)
            
            usuario = User.query.get(session['usuario_id'])
            
            reserva.estado = 'occupied'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'nombre': usuario.nombre,
                'hora_liberacion': hora_liberacion.strftime('%Y-%m-%dT%H:%M:%SZ'),
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Reserva no encontrada'}), 404

@app.route('/release-spot', methods=['POST'])
def release_spot():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    reserva = Estacionamiento.query.filter_by(
        usuario_id=session['usuario_id'],
        estado='occupied'
    ).first()
    
    if reserva:
        reserva.estado = 'available'
        reserva.usuario_id = None
        reserva.hora_reservacion = None  # Limpiar hora de reservación
        db.session.commit()
    
    return jsonify({'success': True})

@app.route('/cancel-reservation', methods=['POST'])
def cancel_reservation():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    reserva = Estacionamiento.query.filter_by(
        usuario_id=session['usuario_id'],
        estado='occupied'
    ).first()
    
    if reserva:
        reserva.estado = 'available'
        reserva.usuario_id = None
        reserva.hora_reservacion = None  # Agregar esto
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Reserva no encontrada'}), 404

@app.route('/time')
def time():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    print(usuario_id)  # Ahora sí está definido

    return render_template('time.html')

@app.route('/get-reservation-time2')
def get_reservation_time2():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'error': 'No autenticado'}), 401

    reserva = Estacionamiento.query.filter_by(
        usuario_id=usuario_id,
        estado='occupied'
    ).first()

    if reserva and reserva.hora_liberacion:
        hora_liberacion_utc = reserva.hora_liberacion.astimezone(timezone.utc)
        
        return jsonify({
            'reservation_end': hora_liberacion_utc.isoformat()
        })

    return jsonify({'reservation_end': None})

@app.route('/reserva')
def reserva():
    return render_template('reservaActiva.html')  # O el HTML que estás usando

@app.route('/liberar-reserva', methods=['POST'])
def liberar_reserva():
    usuario_id = session.get('usuario_id')
    
    if not usuario_id:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    try:
        # Buscar reserva ACTIVA del usuario
        reserva = Estacionamiento.query.filter_by(
            usuario_id=usuario_id,
            estado='occupied'  # ¡Filtro clave que faltaba!
        ).first()
        
        if not reserva:
            return jsonify({'error': 'No hay reserva activa'}), 404

        # Actualizar campos relevantes
        reserva.estado = "available"
        reserva.usuario_id = None
        reserva.hora_reservacion = None
        reserva.hora_liberacion = None

        db.session.commit()
        return jsonify({'mensaje': 'Reserva liberada con éxito'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error al liberar reserva: {str(e)}")
        return jsonify({'error': 'Error interno al liberar reserva'}), 500


@app.route('/recuperar_password', methods=['POST'])
def recuperar_password():
    nombre = request.form.get('nombre')
    correo = request.form.get('correo')
    nueva_password = request.form.get('nueva_password')

    # Validar campos obligatorios
    if not all([nombre, correo]):
        flash('Todos los campos son obligatorios', 'danger')
        return redirect(url_for('recuperar_password'))

    # Buscar usuario
    user = User.query.filter_by(nombre=nombre, correo=correo).first()

    if user:
        if nueva_password:
            # Hashear nueva contraseña
            hashed_pw = bcrypt.hashpw(nueva_password.encode('utf-8'), bcrypt.gensalt())
            user.password = hashed_pw.decode('utf-8')
            db.session.commit()
            flash('Contraseña actualizada exitosamente', 'success')
            return redirect(url_for('login'))
        else:
            flash('Ingrese una nueva contraseña', 'danger')
            return redirect(url_for('recuperar_password'))
    else:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('recuperar_password'))

# Ruta para mostrar el formulario
@app.route('/recuperar_password')
def show_recuperar_password():
    return render_template('recuperar.html')

@app.route('/verificar_usuario', methods=['POST'])
def verificar_usuario():
    data = request.get_json()
    user = User.query.filter_by(
        nombre=data.get('nombre'),
        correo=data.get('correo')
    ).first()
    
    return jsonify({'valido': user is not None})


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    try:
        if 'pdf' not in request.files:
            return jsonify({'success': False, 'error': 'No se ha proporcionado ningún archivo PDF'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400

        filename = 'ticket.pdf'  # O utiliza el nombre del archivo original

        upload_result = cloudinary.uploader.upload(
        file,
        resource_type="auto",  # <--- CAMBIO CLAVE
        folder="tickets-pdf/",
        public_id=f"ticket_{filename}",
        use_filename=True,
        unique_filename=False,
        overwrite=True,
        invalidate=True
        )



        return jsonify({
            'success': True, 
            'url': upload_result['secure_url']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/enviar-whatsapp', methods=['POST'])
def enviar_whatsapp():
    try:
        data = request.json
        phone_number = data.get('phone')
        message_body = data.get('message')
        media_url = data.get('media_url')  # Espera la URL del PDF subido
        
        # Depuración
        print("Número de teléfono:", phone_number)
        print("Mensaje:", message_body)
        print("Media URL:", media_url)
        
        # Validación del número de teléfono con formato internacional
        if not re.match(r'^\+\d{1,15}$', phone_number):
            return jsonify({'success': False, 'error': 'Formato de número inválido'}), 400
        
        message_data = {
            'from_': TWILIO_WHATSAPP_NUMBER,
            'to': f'whatsapp:{phone_number}',
            'body': message_body
        }
        
        
        
        # Enviar el mensaje a través de Twilio
        message = client.messages.create(**message_data)
        print("Mensaje enviado. SID:", message.sid)
        return jsonify({'success': True, 'message_id': message.sid})
        
    except Exception as e:
        print("Error al enviar:", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False) 