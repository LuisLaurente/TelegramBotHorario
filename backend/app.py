# backend/app.py
import os
import sys
from flask import Flask, send_from_directory, jsonify
from dotenv import load_dotenv  # <- AGREGAR ESTE IMPORT

# ✅ FORZAR RECARGA COMPLETA DEL .env
print("=== FORZANDO RECARGA DE .env ===")
load_dotenv(override=True)  # override=True fuerza la recarga

# Verificar que se cargaron correctamente
print("GOOGLE_CLIENT_ID después de recarga:", os.environ.get('GOOGLE_CLIENT_ID'))
print("GOOGLE_CLIENT_SECRET length:", len(os.environ.get('GOOGLE_CLIENT_SECRET', '')))
print("=================================")

# Configurar el path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from models.user import db
from models.event import Event, Category, UserSettings
from routes.auth import auth_bp, init_oauth
from routes.events import events_bp
from routes.telegram import telegram_bp
from telegram_bot import init_telegram_bot
from scheduler import init_scheduler

app = Flask(__name__, static_folder=os.path.join(src_dir, 'static'))
app.config['SECRET_KEY'] = 'clave-temporal-para-pruebas-123456'

# Configurar CORS
from flask_cors import CORS
CORS(app, origins="*")

# Configurar OAuth
google = init_oauth(app)

# Configurar bot de Telegram
telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', 'test')
if telegram_token and telegram_token != 'test':
    telegram_bot = init_telegram_bot(telegram_token, app.app_context)
else:
    telegram_bot = None
    print("⚠️  Telegram bot token no configurado")

# Configurar scheduler
scheduler = init_scheduler(app.app_context)

# Configurar base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(src_dir, 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Crear tablas
with app.app_context():
    db.create_all()

# Registrar blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(events_bp, url_prefix='/api')
app.register_blueprint(telegram_bp, url_prefix='/api')

@app.route('/api/debug/oauth-setup')
def debug_oauth_setup():
    """Debug completo de la configuración OAuth"""
    from routes.auth import oauth
    
    debug_info = {
        'has_google_attr': hasattr(oauth, 'google'),
        'client_id': None,
        'authorize_url': None,
        'client_kwargs': None
    }
    
    if hasattr(oauth, 'google'):
        debug_info.update({
            'client_id': oauth.google.client_id,
            'authorize_url': oauth.google.authorize_url,
            'client_kwargs': oauth.google.client_kwargs
        })
    
    return jsonify(debug_info)

# Endpoint de debug para variables de entorno
@app.route('/api/debug/full-env')
def debug_full_env():
    """Debug completo de todas las variables de entorno"""
    import os
    env_vars = {}
    for key, value in os.environ.items():
        if 'GOOGLE' in key or 'SECRET' in key or 'TOKEN' in key:
            if 'SECRET' in key or 'TOKEN' in key:
                env_vars[key] = f"***{len(value)}***" if value else "None"
            else:
                env_vars[key] = value
    
    # Verificar archivo .env
    env_file_path = os.path.join(os.path.dirname(__file__), '.env')
    env_file_exists = os.path.exists(env_file_path)
    
    return jsonify({
        'env_vars': env_vars,
        'env_file_exists': env_file_exists,
        'env_file_path': env_file_path,
        'current_working_dir': os.getcwd()
    })
# Rutas temporales para OAuth - ELIMINAR en producción
@app.route('/privacy')
def privacy():
    return "Política de privacidad - Desarrollo"

@app.route('/terms')  
def terms():
    return "Términos de servicio - Desarrollo"

# Endpoint para obtener estado del scheduler
@app.route('/api/scheduler/status')
def scheduler_status():
    from scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler:
        return scheduler.get_scheduler_status()
    else:
        return {'error': 'Scheduler not initialized'}, 500

# Ruta que captura todo - DEBE SER LA ÚLTIMA
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        if scheduler:
            scheduler.shutdown()
        if telegram_bot:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(telegram_bot.stop_bot())
            loop.close()