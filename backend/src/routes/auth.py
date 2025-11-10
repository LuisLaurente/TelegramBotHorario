from flask import Blueprint, request, jsonify, session, redirect, url_for
from models.user import db, User
from models.event import UserSettings
from datetime import datetime
import os
import requests
import urllib.parse

auth_bp = Blueprint('auth', __name__)

# No usamos Authlib - lo hacemos manualmente

def init_oauth(app):
    """Función de compatibilidad - no hace nada ahora"""
    print("✅ OAuth inicializado en modo manual")
    return None

@auth_bp.route('/login')
def login():
    """Iniciar el proceso de autenticación con Google - MANUAL"""
    try:
        print("🔧 === INICIANDO LOGIN OAUTH MANUAL ===")
        
        # ✅ USAR VARIABLES DE ENTORNO (no hardcode)
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        
        print("🔍 Client ID desde env:", client_id)
        print("🔍 Client Secret length:", len(client_secret) if client_secret else 0)
        
        if not client_id or client_id == 'test':
            print("❌ Client ID todavía no está cargado correctamente")
            return jsonify({'error': 'Client ID no configurado'}), 500
        
        # Construir URL de autorización manualmente
        redirect_uri = url_for('auth.callback', _external=True)
        print("📍 Redirect URI:", redirect_uri)
        
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'select_account',
            'state': 'manual_oauth_state'  # Para seguridad básica
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        
        print("🌐 Auth URL generada:", auth_url)
        
        if 'accounts.google.com' not in auth_url:
            print("❌ URL no contiene dominio de Google")
            return jsonify({'error': 'URL de autorización inválida'}), 500
            
        print("✅ Redirigiendo a Google OAuth...")
        return redirect(auth_url)
        
    except Exception as e:
        print("💥 ERROR en login manual:")
        print(str(e))
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error en el proceso de login: {str(e)}'}), 500


@auth_bp.route('/callback')
def callback():
    """Callback después de la autenticación con Google - MANUAL"""
    try:
        print("🔄 Procesando callback OAuth manual")
        
        # Obtener el código de autorización
        auth_code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            print(f"❌ Error de Google: {error}")
            return jsonify({'error': f'Error de autenticación: {error}'}), 400
            
        if not auth_code:
            print("❌ No se recibió código de autorización")
            return jsonify({'error': 'No se recibió código de autorización'}), 400
        
        print("✅ Código de autorización recibido")
        
        # Intercambiar código por token
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        redirect_uri = url_for('auth.callback', _external=True)
        
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        print("🔄 Intercambiando código por token...")
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data=token_data
        )
        
        if token_response.status_code != 200:
            print(f"❌ Error obteniendo token: {token_response.text}")
            return jsonify({'error': 'Error obteniendo token de acceso'}), 400
        
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        if not access_token:
            print("❌ No se pudo obtener access token")
            return jsonify({'error': 'No se pudo obtener token de acceso'}), 400
        
        print("✅ Token de acceso obtenido")
        
        # Obtener información del usuario
        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if userinfo_response.status_code != 200:
            print(f"❌ Error obteniendo userinfo: {userinfo_response.text}")
            return jsonify({'error': 'Error obteniendo información del usuario'}), 400
        
        user_info = userinfo_response.json()
        print(f"✅ Usuario autenticado: {user_info.get('email')}")
        
        # Buscar o crear el usuario en la base de datos
        user = User.query.filter_by(google_id=user_info['sub']).first()
        
        if not user:
            # Crear nuevo usuario
            user = User(
                google_id=user_info['sub'],
                email=user_info['email'],
                name=user_info['name'],
                picture=user_info.get('picture', ''),
                is_active=True,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            db.session.add(user)
            db.session.commit()
            
            # Crear configuraciones por defecto para el usuario
            user_settings = UserSettings(
                user_id=user.id,
                timezone='UTC',
                default_reminder_minutes=30,
                notifications_enabled=True,
                daily_summary_enabled=False,
                daily_summary_time='08:00'
            )
            db.session.add(user_settings)
            db.session.commit()
            print(f"✅ Nuevo usuario creado: {user.email}")
        else:
            # Actualizar última conexión
            user.last_login = datetime.utcnow()
            db.session.commit()
            print(f"✅ Usuario existente: {user.email}")
        
        # Guardar información del usuario en la sesión
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        session['user_picture'] = user.picture
        
        # Redirigir al dashboard
        return redirect('/')
        
    except Exception as e:
        print("💥 Error en callback manual:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error en el callback: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Cerrar sesión del usuario"""
    try:
        session.clear()
        return jsonify({'message': 'Sesión cerrada exitosamente'}), 200
    except Exception as e:
        return jsonify({'error': f'Error al cerrar sesión: {str(e)}'}), 500

@auth_bp.route('/user')
def get_current_user():
    """Obtener información del usuario actual"""
    try:
        if 'user_id' not in session:
            return jsonify({'authenticated': False}), 401
            
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        if not user:
            session.clear()
            return jsonify({'authenticated': False}), 401
            
        return jsonify({
            'authenticated': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener usuario: {str(e)}'}), 500

@auth_bp.route('/check')
def check_auth():
    """Verificar si el usuario está autenticado"""
    try:
        if 'user_id' in session:
            return jsonify({'authenticated': True}), 200
        else:
            return jsonify({'authenticated': False}), 200
    except Exception as e:
        return jsonify({'error': f'Error al verificar autenticación: {str(e)}'}), 500