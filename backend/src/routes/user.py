from flask import Blueprint, jsonify, session
from models.user import User

user_bp = Blueprint('user', __name__)

@user_bp.route('/user/profile', methods=['GET'])
def get_user_profile():
    """Obtener perfil del usuario actual"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuario no autenticado'}), 401
            
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404
            
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener perfil: {str(e)}'}), 500