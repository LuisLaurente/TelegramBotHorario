import os
import sys

# ✅ AGREGAR ESTO AL PRINCIPIO del archivo (después de los imports estándar)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from flask import Flask, send_from_directory
from flask_cors import CORS
from models.user import db
from models.event import Event, Category, UserSettings
from routes.auth import auth_bp, init_oauth
from routes.events import events_bp
from routes.telegram import telegram_bp
from routes.user import user_bp  # Si existe
from telegram_bot import init_telegram_bot
from scheduler import init_scheduler

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# ✅ Usar configuración desde config.py
app.config.from_object(config['production'])  # Cambiar a 'development' para desarrollo

# Configurar CORS
CORS(app, origins="*")

# Configurar OAuth
google = init_oauth(app)

# Configurar bot de Telegram (solo si hay token)
telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
if telegram_token and telegram_token != 'your-telegram-bot-token':
    telegram_bot = init_telegram_bot(telegram_token, app.app_context)
else:
    telegram_bot = None
    print("⚠️  Telegram bot token no configurado")

# Configurar scheduler
scheduler = init_scheduler(app.app_context)

# Configurar base de datos
db.init_app(app)

# Crear tablas
with app.app_context():
    db.create_all()

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

@app.route('/api/scheduler/status')
def scheduler_status():
    from scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler:
        return scheduler.get_scheduler_status()
    else:
        return {'error': 'Scheduler not initialized'}, 500

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)  # ✅ debug=False en producción
    except KeyboardInterrupt:
        if scheduler:
            scheduler.shutdown()
        if telegram_bot:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(telegram_bot.stop_bot())
            loop.close()