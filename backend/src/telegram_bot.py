import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from models.user import db, User
from models.event import UserSettings, Event
from datetime import datetime, timedelta
import asyncio
import dateparser  # ✅ AGREGADO PARA PROCESAMIENTO DE LENGUAJE NATURAL

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token, app_context):
        self.token = token
        self.app_context = app_context
        self.application = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Inicializar bot"""
        chat_id = update.effective_chat.id
        user_telegram = update.effective_user
        
        welcome_message = f"""
¡Hola {user_telegram.first_name}! 👋

Soy tu asistente de horarios. Para comenzar a recibir notificaciones de tus eventos, necesitas vincular tu cuenta.

Para vincular tu cuenta:
1. Ve a la configuración en la aplicación web
2. Ingresa tu ID de chat de Telegram: `{chat_id}`
3. Guarda los cambios

Una vez vinculada tu cuenta, podrás:
• Recibir recordatorios de eventos
• Obtener resúmenes diarios de tu horario
• Configurar notificaciones personalizadas
• Crear eventos usando lenguaje natural (ej: "mañana a las 3pm reunión")

Comandos disponibles:
/start - Mostrar este mensaje
/help - Ayuda
/status - Ver estado de vinculación
/today - Ver eventos de hoy
/tomorrow - Ver eventos de mañana
/settings - Configurar notificaciones
        """
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Mostrar ayuda"""
        help_message = """
📋 **Comandos disponibles:**

/start - Inicializar el bot
/help - Mostrar esta ayuda
/status - Ver estado de vinculación con tu cuenta
/today - Ver eventos programados para hoy
/tomorrow - Ver eventos programados para mañana
/settings - Configurar tus notificaciones

🎯 **Crear eventos con lenguaje natural:**
Puedes escribir mensajes como:
• "Mañana a las 3pm reunión con el equipo"
• "El viernes a las 10:30 clase de yoga"
• "Próximo lunes a las 9am dentista"

🔗 **Para vincular tu cuenta:**
1. Copia tu ID de chat: `{}`
2. Ve a la configuración en la web
3. Pega el ID y guarda

💡 **Tip:** Una vez vinculada tu cuenta, recibirás recordatorios automáticos de tus eventos.
        """.format(update.effective_chat.id)
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Ver estado de vinculación"""
        chat_id = str(update.effective_chat.id)
        
        with self.app_context():
            settings = UserSettings.query.filter_by(telegram_chat_id=chat_id).first()
            
            if settings:
                user = User.query.get(settings.user_id)
                status_message = f"""
✅ **Cuenta vinculada exitosamente**

👤 Usuario: {user.name}
📧 Email: {user.email}
🔔 Notificaciones: {'Activadas' if settings.notifications_enabled else 'Desactivadas'}
📅 Resumen diario: {'Activado' if settings.daily_summary_enabled else 'Desactivado'}
⏰ Recordatorio por defecto: {settings.default_reminder_minutes} minutos
🌍 Zona horaria: {settings.timezone}
                """
            else:
                status_message = f"""
❌ **Cuenta no vinculada**

Tu ID de chat: `{chat_id}`

Para vincular tu cuenta:
1. Copia el ID de arriba
2. Ve a la configuración en la aplicación web
3. Pega el ID en el campo correspondiente
4. Guarda los cambios
                """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /today - Ver eventos de hoy"""
        chat_id = str(update.effective_chat.id)
        
        with self.app_context():
            settings = UserSettings.query.filter_by(telegram_chat_id=chat_id).first()
            
            if not settings:
                await update.message.reply_text(
                    "❌ Tu cuenta no está vinculada. Usa /status para más información."
                )
                return
            
            # Obtener eventos de hoy
            today = datetime.now().date()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())
            
            events = Event.query.filter(
                Event.user_id == settings.user_id,
                Event.is_active == True,
                Event.start_time >= start_of_day,
                Event.start_time <= end_of_day
            ).order_by(Event.start_time).all()
            
            if not events:
                await update.message.reply_text("📅 No tienes eventos programados para hoy.")
                return
            
            message = "📅 **Eventos de hoy:**\n\n"
            for event in events:
                start_time = event.start_time.strftime("%H:%M")
                end_time = event.end_time.strftime("%H:%M")
                category_name = event.category.name if event.category else "Sin categoría"
                
                message += f"🕐 {start_time} - {end_time}\n"
                message += f"📋 {event.title}\n"
                message += f"🏷️ {category_name}\n"
                if event.description:
                    message += f"📝 {event.description}\n"
                message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def tomorrow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /tomorrow - Ver eventos de mañana"""
        chat_id = str(update.effective_chat.id)
        
        with self.app_context():
            settings = UserSettings.query.filter_by(telegram_chat_id=chat_id).first()
            
            if not settings:
                await update.message.reply_text(
                    "❌ Tu cuenta no está vinculada. Usa /status para más información."
                )
                return
            
            # Obtener eventos de mañana
            tomorrow = datetime.now().date() + timedelta(days=1)
            start_of_day = datetime.combine(tomorrow, datetime.min.time())
            end_of_day = datetime.combine(tomorrow, datetime.max.time())
            
            events = Event.query.filter(
                Event.user_id == settings.user_id,
                Event.is_active == True,
                Event.start_time >= start_of_day,
                Event.start_time <= end_of_day
            ).order_by(Event.start_time).all()
            
            if not events:
                await update.message.reply_text("📅 No tienes eventos programados para mañana.")
                return
            
            message = "📅 **Eventos de mañana:**\n\n"
            for event in events:
                start_time = event.start_time.strftime("%H:%M")
                end_time = event.end_time.strftime("%H:%M")
                category_name = event.category.name if event.category else "Sin categoría"
                
                message += f"🕐 {start_time} - {end_time}\n"
                message += f"📋 {event.title}\n"
                message += f"🏷️ {category_name}\n"
                if event.description:
                    message += f"📝 {event.description}\n"
                message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /settings - Configurar notificaciones"""
        chat_id = str(update.effective_chat.id)
        
        with self.app_context():
            settings = UserSettings.query.filter_by(telegram_chat_id=chat_id).first()
            
            if not settings:
                await update.message.reply_text(
                    "❌ Tu cuenta no está vinculada. Usa /status para más información."
                )
                return
            
            # Crear teclado inline para configuraciones
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"🔔 Notificaciones: {'ON' if settings.notifications_enabled else 'OFF'}", 
                        callback_data="toggle_notifications"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"📅 Resumen diario: {'ON' if settings.daily_summary_enabled else 'OFF'}", 
                        callback_data="toggle_daily_summary"
                    )
                ],
                [
                    InlineKeyboardButton("⏰ Cambiar tiempo de recordatorio", callback_data="change_reminder_time")
                ],
                [
                    InlineKeyboardButton("🌍 Cambiar zona horaria", callback_data="change_timezone")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"""
            ⚙️ **Configuración de notificaciones**

            🔔 Notificaciones: {'Activadas' if settings.notifications_enabled else 'Desactivadas'}
            📅 Resumen diario: {'Activado' if settings.daily_summary_enabled else 'Desactivado'}
            ⏰ Recordatorio por defecto: {settings.default_reminder_minutes} minutos
            🌍 Zona horaria: {settings.timezone}

            Usa los botones de abajo para cambiar la configuración:
                        """
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes de texto que no son comandos para crear eventos."""
        chat_id = str(update.effective_chat.id)
        text = update.message.text
        
        with self.app_context():
            settings = UserSettings.query.filter_by(telegram_chat_id=chat_id).first()
            
            if not settings:
                await update.message.reply_text(
                    "❌ Tu cuenta no está vinculada. Usa /status para más información."
                )
                return
            
            # Usar dateparser para el procesamiento de lenguaje natural en español
            from dateparser import parse
            import pytz  # ✅ AGREGADO PARA CONVERSIÓN DE ZONAS HORARIAS
            
            # Usar la zona horaria del usuario para el parseo y preferir fechas futuras
            settings_timezone = settings.timezone or 'UTC'
            
            try:
                # 1. Intentar parsear fecha/hora
                parsed_datetime_utc = parse(
                    text,
                    settings={
                        'TIMEZONE': 'UTC', 
                        'TO_TIMEZONE': 'UTC',
                        'RETURN_AS_TIMEZONE_AWARE': True,
                        'PREFER_DATES_FROM': 'future',
                        'RELATIVE_BASE': datetime.now(),
                    },
                    languages=['es'] # Especificar español
                )
                
                if not parsed_datetime_utc:
                    await update.message.reply_text(
                        "❌ No pude entender una fecha u hora válida en tu mensaje. Por favor, sé más específico (ej: 'mañana a las 3pm reunión')."
                    )
                    return
                
                # 2. Asignar el título (usamos todo el texto como título por simplicidad)
                title = text.strip() 
                
                # 3. Determinar el tiempo inicial y final
                start_time_utc = parsed_datetime_utc.replace(tzinfo=None) # Almacenar como naive UTC
                # Asignar una duración por defecto de 60 minutos si no se especifica
                default_duration_minutes = 60 
                end_time_utc = start_time_utc + timedelta(minutes=default_duration_minutes)

                # 4. Crear y guardar evento
                new_event = Event(
                    user_id=settings.user_id,
                    title=title,
                    description=f"Agregado desde Telegram - Chat ID: {chat_id}",
                    start_time=start_time_utc,
                    end_time=end_time_utc,
                    reminder_minutes=settings.default_reminder_minutes,
                    is_active=True
                )
                
                db.session.add(new_event)
                db.session.commit()
                
                # 5. Usar pytz para mostrar la hora en la zona horaria del usuario
                try:
                    tz = pytz.timezone(settings.timezone)
                    start_time_local = pytz.utc.localize(new_event.start_time).astimezone(tz)
                    end_time_local = pytz.utc.localize(new_event.end_time).astimezone(tz)

                    start_time_display = start_time_local.strftime("%Y-%m-%d %H:%M %Z")
                    end_time_display = end_time_local.strftime("%Y-%m-%d %H:%M %Z")
                except pytz.UnknownTimeZoneError:
                    # Si hay un error con la zona horaria, volvemos a mostrar UTC
                    start_time_display = new_event.start_time.strftime("%Y-%m-%d %H:%M UTC")
                    end_time_display = new_event.end_time.strftime("%Y-%m-%d %H:%M UTC")
                
                # 6. Enviar confirmación con la hora en la zona horaria del usuario
                message = f"""
✅ **Evento creado exitosamente**

📋 **Título:** {new_event.title}
🕐 **Inicio:** {start_time_display}
⏰ **Fin:** {end_time_display}
🔔 **Recordatorio:** {new_event.reminder_minutes} minutos antes
🌍 **Zona Horaria:** {settings.timezone}
                """
                await update.message.reply_text(message, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}")
                await update.message.reply_text(
                    "❌ Ocurrió un error al intentar crear el evento. Verifica el formato del mensaje."
                )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar callbacks de botones inline"""
        query = update.callback_query
        await query.answer()
        
        chat_id = str(query.from_user.id)
        
        with self.app_context():
            settings = UserSettings.query.filter_by(telegram_chat_id=chat_id).first()
            
            if not settings:
                await query.edit_message_text("❌ Tu cuenta no está vinculada.")
                return
            
            if query.data == "toggle_notifications":
                settings.notifications_enabled = not settings.notifications_enabled
                db.session.commit()
                
                status = "activadas" if settings.notifications_enabled else "desactivadas"
                await query.edit_message_text(f"✅ Notificaciones {status}")
                
            elif query.data == "toggle_daily_summary":
                settings.daily_summary_enabled = not settings.daily_summary_enabled
                db.session.commit()
                
                status = "activado" if settings.daily_summary_enabled else "desactivado"
                await query.edit_message_text(f"✅ Resumen diario {status}")
                
            elif query.data == "change_reminder_time":
                await query.edit_message_text(
                    "⏰ Para cambiar el tiempo de recordatorio, ve a la configuración en la aplicación web."
                )
                
            elif query.data == "change_timezone":
                await query.edit_message_text(
                    "🌍 Para cambiar la zona horaria, ve a la configuración en la aplicación web."
                )
    
    async def send_reminder(self, chat_id, event):
        """Enviar recordatorio de evento"""
        try:
            start_time = event.start_time.strftime("%H:%M")
            category_name = event.category.name if event.category else "Sin categoría"
            
            message = f"""
🔔 **Recordatorio de evento**

📋 {event.title}
🕐 Hora: {start_time}
🏷️ Categoría: {category_name}
            """
            
            if event.description:
                message += f"\n📝 {event.description}"
            
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error enviando recordatorio: {e}")
    
    async def send_daily_summary(self, chat_id, events):
        """Enviar resumen diario"""
        try:
            if not events:
                message = "📅 **Resumen del día**\n\nNo tienes eventos programados para hoy."
            else:
                message = "📅 **Resumen del día**\n\n"
                for event in events:
                    start_time = event.start_time.strftime("%H:%M")
                    end_time = event.end_time.strftime("%H:%M")
                    category_name = event.category.name if event.category else "Sin categoría"
                    
                    message += f"🕐 {start_time} - {end_time}\n"
                    message += f"📋 {event.title}\n"
                    message += f"🏷️ {category_name}\n\n"
            
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error enviando resumen diario: {e}")
    
    def setup_handlers(self):
        """Configurar manejadores de comandos"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("today", self.today_command))
        self.application.add_handler(CommandHandler("tomorrow", self.tomorrow_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # ✅ NUEVO MANEJADOR PARA TEXTO LIBRE
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_text_message
            )
        )
    
    async def start_bot(self):
        """Iniciar el bot con POLLING"""
        try:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
            
            print("🔄 Iniciando bot de Telegram con polling...")
            
            # 1. Inicializar la aplicación
            await self.application.initialize()
            
            # 2. Iniciar el bot y el polling. Esto es suficiente.
            await self.application.start()
            
            # 3. MANTENER EL BUCLE DE EVENTOS CORRIENDO
            # Nota: La función que envuelve este método (start_polling) 
            # ya llama a loop.run_forever(), por lo que solo necesitamos 
            # asegurarnos de que la aplicación esté arrancada.
            
            print("✅ Bot de Telegram iniciado correctamente con polling")
            
        except Exception as e:
            print(f"❌ Error iniciando bot: {e}")
            raise
    
    async def stop_bot(self):
        """Detener el bot"""
        try:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Bot de Telegram detenido")
        except Exception as e:
            logger.error(f"Error deteniendo bot: {e}")

# Instancia global del bot
telegram_bot = None

def init_telegram_bot(token, app_context):
    """Inicializar el bot de Telegram con POLLING"""
    global telegram_bot
    
    if not token or token == 'test':
        logger.warning("Token de Telegram no configurado")
        return None
    
    try:
        print("🤖 Iniciando bot de Telegram con polling...")
        telegram_bot = TelegramBot(token, app_context)
        
        # ✅ INICIAR POLLING EN SEGUNDO PLANO
        def start_polling():
            try:
                import asyncio
                
                # Crear nuevo event loop para el bot
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Iniciar el bot
                loop.run_until_complete(telegram_bot.start_bot())
                
                # Mantener el bot corriendo
                print("✅ Bot de Telegram iniciado - Escuchando mensajes...")
                loop.run_forever()
                
            except Exception as e:
                logger.error(f"Error en polling: {e}")
        
        # Ejecutar en un hilo separado
        import threading
        bot_thread = threading.Thread(target=start_polling, daemon=True)
        bot_thread.start()
        
        return telegram_bot
        
    except Exception as e:
        logger.error(f"Error iniciando bot de Telegram: {e}")
        return None

def get_telegram_bot():
    """Obtener la instancia del bot"""
    return telegram_bot