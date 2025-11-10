from flask import Blueprint, request, jsonify, session

from models.user import db, User
from models.event import Event, Category, UserSettings
from datetime import datetime, timedelta
import pytz

events_bp = Blueprint('events', __name__)

def require_auth(f):
    """Decorador para requerir autenticación"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Autenticación requerida'}), 401
        return f(*args, **kwargs)
    return decorated_function

@events_bp.route('/events', methods=['GET'])
@require_auth
def get_events():
    """Obtener todos los eventos del usuario"""
    try:
        user_id = session['user_id']
        
        # Parámetros de consulta opcionales
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Event.query.filter_by(user_id=user_id, is_active=True)
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Event.start_time >= start_dt)
            
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Event.end_time <= end_dt)
        
        events = query.order_by(Event.start_time).all()
        
        return jsonify({
            'events': [event.to_dict() for event in events]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener eventos: {str(e)}'}), 500

@events_bp.route('/events', methods=['POST'])
@require_auth
def create_event():
    """Crear un nuevo evento"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
            
        # Validar campos requeridos
        required_fields = ['title', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        # Convertir fechas
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        
        # Validar que la fecha de fin sea posterior a la de inicio
        if end_time <= start_time:
            return jsonify({'error': 'La fecha de fin debe ser posterior a la de inicio'}), 400
        
        # Crear el evento
        event = Event(
            user_id=user_id,
            title=data['title'],
            description=data.get('description', ''),
            start_time=start_time,
            end_time=end_time,
            category_id=data.get('category_id'),
            reminder_minutes=data.get('reminder_minutes', 30),
            is_active=True
        )
        
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            'message': 'Evento creado exitosamente',
            'event': event.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al crear evento: {str(e)}'}), 500

@events_bp.route('/events/<int:event_id>', methods=['PUT'])
@require_auth
def update_event(event_id):
    """Actualizar un evento existente"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        # Buscar el evento
        event = Event.query.filter_by(id=event_id, user_id=user_id, is_active=True).first()
        
        if not event:
            return jsonify({'error': 'Evento no encontrado'}), 404
        
        # Actualizar campos
        if 'title' in data:
            event.title = data['title']
        if 'description' in data:
            event.description = data['description']
        if 'start_time' in data:
            event.start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        if 'end_time' in data:
            event.end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        if 'category_id' in data:
            event.category_id = data['category_id']
        if 'reminder_minutes' in data:
            event.reminder_minutes = data['reminder_minutes']
        
        # Validar fechas si se actualizaron
        if event.end_time <= event.start_time:
            return jsonify({'error': 'La fecha de fin debe ser posterior a la de inicio'}), 400
        
        event.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Evento actualizado exitosamente',
            'event': event.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar evento: {str(e)}'}), 500

@events_bp.route('/events/<int:event_id>', methods=['DELETE'])
@require_auth
def delete_event(event_id):
    """Eliminar un evento (soft delete)"""
    try:
        user_id = session['user_id']
        
        # Buscar el evento
        event = Event.query.filter_by(id=event_id, user_id=user_id, is_active=True).first()
        
        if not event:
            return jsonify({'error': 'Evento no encontrado'}), 404
        
        # Soft delete
        event.is_active = False
        event.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Evento eliminado exitosamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar evento: {str(e)}'}), 500

@events_bp.route('/categories', methods=['GET'])
@require_auth
def get_categories():
    """Obtener todas las categorías del usuario"""
    try:
        user_id = session['user_id']
        categories = Category.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'categories': [category.to_dict() for category in categories]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener categorías: {str(e)}'}), 500

@events_bp.route('/categories', methods=['POST'])
@require_auth
def create_category():
    """Crear una nueva categoría"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'Nombre de categoría requerido'}), 400
        
        # Verificar que no exista una categoría con el mismo nombre
        existing_category = Category.query.filter_by(
            user_id=user_id, 
            name=data['name']
        ).first()
        
        if existing_category:
            return jsonify({'error': 'Ya existe una categoría con ese nombre'}), 400
        
        # Crear la categoría
        category = Category(
            user_id=user_id,
            name=data['name'],
            color=data.get('color', '#3498db')
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Categoría creada exitosamente',
            'category': category.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al crear categoría: {str(e)}'}), 500

@events_bp.route('/categories/<int:category_id>', methods=['PUT'])
@require_auth
def update_category(category_id):
    """Actualizar una categoría existente"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        # Buscar la categoría
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        
        if not category:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Actualizar campos
        if 'name' in data:
            # Verificar que no exista otra categoría con el mismo nombre
            existing_category = Category.query.filter_by(
                user_id=user_id, 
                name=data['name']
            ).filter(Category.id != category_id).first()
            
            if existing_category:
                return jsonify({'error': 'Ya existe una categoría con ese nombre'}), 400
                
            category.name = data['name']
            
        if 'color' in data:
            category.color = data['color']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Categoría actualizada exitosamente',
            'category': category.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar categoría: {str(e)}'}), 500

@events_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@require_auth
def delete_category(category_id):
    """Eliminar una categoría"""
    try:
        user_id = session['user_id']
        
        # Buscar la categoría
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        
        if not category:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Verificar si hay eventos usando esta categoría
        events_count = Event.query.filter_by(category_id=category_id, is_active=True).count()
        
        if events_count > 0:
            return jsonify({
                'error': f'No se puede eliminar la categoría porque tiene {events_count} eventos asociados'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({'message': 'Categoría eliminada exitosamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar categoría: {str(e)}'}), 500

@events_bp.route('/settings', methods=['GET'])
@require_auth
def get_user_settings():
    """Obtener configuraciones del usuario"""
    try:
        user_id = session['user_id']
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if not settings:
            # Crear configuraciones por defecto si no existen
            settings = UserSettings(
                user_id=user_id,
                timezone='UTC',
                default_reminder_minutes=30,
                notifications_enabled=True,
                daily_summary_enabled=False,
                daily_summary_time='08:00'
            )
            db.session.add(settings)
            db.session.commit()
        
        return jsonify({
            'settings': settings.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener configuraciones: {str(e)}'}), 500
@events_bp.route('/settings', methods=['PUT'])
@require_auth
def update_user_settings():
    """Actualizar configuraciones del usuario"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if not settings:
            settings = UserSettings(user_id=user_id)
            db.session.add(settings)
        
        # Actualizar campos
        if 'timezone' in data:
            settings.timezone = data['timezone']
        if 'default_reminder_minutes' in data:
            settings.default_reminder_minutes = data['default_reminder_minutes']
        if 'notifications_enabled' in data:
            settings.notifications_enabled = data['notifications_enabled']
        if 'daily_summary_enabled' in data:
            settings.daily_summary_enabled = data['daily_summary_enabled']
        if 'daily_summary_time' in data:
            settings.daily_summary_time = data['daily_summary_time']
        if 'telegram_chat_id' in data:
            settings.telegram_chat_id = data['telegram_chat_id']
        if 'telegram_username' in data:
            settings.telegram_username = data['telegram_username']
        
        settings.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Configuraciones actualizadas exitosamente',
            'settings': settings.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar configuraciones: {str(e)}'}), 500