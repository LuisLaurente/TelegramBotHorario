from flask import Blueprint, request, jsonify, session
from models.user import db, User
from models.event import UserSettings
from telegram_bot import get_telegram_bot
import asyncio

telegram_bp = Blueprint('telegram', __name__)

def require_auth(f):
    """Decorador para requerir autenticación"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Autenticación requerida'}), 401
        return f(*args, **kwargs)
    return decorated_function

@telegram_bp.route('/telegram/link', methods=['POST'])
@require_auth
def link_telegram():
    """Vincular cuenta de Telegram del usuario"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data or 'telegram_chat_id' not in data:
            return jsonify({'error': 'ID de chat de Telegram requerido'}), 400
        
        telegram_chat_id = str(data['telegram_chat_id'])
        telegram_username = data.get('telegram_username', '')
        
        # Buscar o crear configuraciones del usuario
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if not settings:
            settings = UserSettings(
                user_id=user_id,
                timezone='UTC',
                default_reminder_minutes=30,
                notifications_enabled=True,
                daily_summary_enabled=False,
                daily_summary_time='08:00'
            )
            db.session.add(settings)
        
        # Verificar que el chat_id no esté ya vinculado a otra cuenta
        existing_settings = UserSettings.query.filter_by(telegram_chat_id=telegram_chat_id).first()
        if existing_settings and existing_settings.user_id != user_id:
            return jsonify({
                'error': 'Este ID de chat ya está vinculado a otra cuenta'
            }), 400
        
        # Actualizar configuraciones
        settings.telegram_chat_id = telegram_chat_id
        settings.telegram_username = telegram_username
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cuenta de Telegram vinculada exitosamente',
            'telegram_chat_id': telegram_chat_id,
            'telegram_username': telegram_username
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al vincular Telegram: {str(e)}'}), 500

@telegram_bp.route('/telegram/unlink', methods=['POST'])
@require_auth
def unlink_telegram():
    """Desvincular cuenta de Telegram del usuario"""
    try:
        user_id = session['user_id']
        
        # Buscar configuraciones del usuario
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if not settings or not settings.telegram_chat_id:
            return jsonify({'error': 'No hay cuenta de Telegram vinculada'}), 400
        
        # Limpiar datos de Telegram
        settings.telegram_chat_id = None
        settings.telegram_username = None
        settings.notifications_enabled = False
        settings.daily_summary_enabled = False
        
        db.session.commit()
        
        return jsonify({'message': 'Cuenta de Telegram desvinculada exitosamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al desvincular Telegram: {str(e)}'}), 500

@telegram_bp.route('/telegram/status', methods=['GET'])
@require_auth
def get_telegram_status():
    """Obtener estado de vinculación con Telegram"""
    try:
        user_id = session['user_id']
        
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if not settings:
            return jsonify({
                'linked': False,
                'telegram_chat_id': None,
                'telegram_username': None,
                'notifications_enabled': False,
                'daily_summary_enabled': False
            }), 200
        
        return jsonify({
            'linked': bool(settings.telegram_chat_id),
            'telegram_chat_id': settings.telegram_chat_id,
            'telegram_username': settings.telegram_username,
            'notifications_enabled': settings.notifications_enabled,
            'daily_summary_enabled': settings.daily_summary_enabled
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener estado: {str(e)}'}), 500

@telegram_bp.route('/telegram/test', methods=['POST'])
@require_auth
def test_telegram_notification():
    """Enviar notificación de prueba a Telegram"""
    try:
        user_id = session['user_id']
        
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if not settings or not settings.telegram_chat_id:
            return jsonify({'error': 'No hay cuenta de Telegram vinculada'}), 400
        
        if not settings.notifications_enabled:
            return jsonify({'error': 'Las notificaciones están desactivadas'}), 400
        
        # Obtener bot de Telegram
        bot = get_telegram_bot()
        if not bot:
            return jsonify({'error': 'Bot de Telegram no disponible'}), 500
        
        # Crear evento de prueba
        class TestEvent:
            def __init__(self):
                self.title = "Evento de prueba"
                self.description = "Esta es una notificación de prueba desde tu aplicación de horarios."
                self.start_time = datetime.now()
                self.category = None
        
        test_event = TestEvent()
        
        # Enviar notificación de prueba
        async def send_test():
            await bot.send_reminder(settings.telegram_chat_id, test_event)
        
        # Ejecutar la función asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_test())
        loop.close()
        
        return jsonify({'message': 'Notificación de prueba enviada exitosamente'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al enviar notificación de prueba: {str(e)}'}), 500

@telegram_bp.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook para recibir actualizaciones de Telegram"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        # Obtener bot de Telegram
        bot = get_telegram_bot()
        if not bot:
            return jsonify({'error': 'Bot not available'}), 500
        
        # Procesar la actualización
        # Nota: En un entorno de producción, esto debería manejarse de forma asíncrona
        # usando una cola de tareas como Celery
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Webhook error: {str(e)}'}), 500

