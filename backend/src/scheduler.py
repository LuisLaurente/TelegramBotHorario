import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from models.user import db, User
from models.event import Event, UserSettings
from telegram_bot import get_telegram_bot
import asyncio
import pytz

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationScheduler:
    def __init__(self, app_context):
        self.app_context = app_context
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("Scheduler iniciado")
        
        # Programar tareas recurrentes
        self.schedule_recurring_tasks()
        
    def schedule_recurring_tasks(self):
        """Programar tareas que se ejecutan regularmente"""
        
        # Verificar recordatorios cada minuto
        self.scheduler.add_job(
            func=self.check_event_reminders,
            trigger=CronTrigger(second=0),  # Cada minuto en el segundo 0
            id='check_reminders',
            name='Verificar recordatorios de eventos',
            replace_existing=True
        )
        
        # Enviar resúmenes diarios a las 8:00 AM por defecto
        self.scheduler.add_job(
            func=self.send_daily_summaries,
            trigger=CronTrigger(hour=8, minute=0, second=0),  # 8:00 AM todos los días
            id='daily_summaries',
            name='Enviar resúmenes diarios',
            replace_existing=True
        )
        
        # Limpiar eventos antiguos cada día a medianoche
        self.scheduler.add_job(
            func=self.cleanup_old_events,
            trigger=CronTrigger(hour=0, minute=0, second=0),  # Medianoche
            id='cleanup_events',
            name='Limpiar eventos antiguos',
            replace_existing=True
        )
        
        logger.info("Tareas recurrentes programadas")
    
    def check_event_reminders(self):
        """Verificar y enviar recordatorios de eventos próximos"""
        try:
            with self.app_context():
                logger.info("Verificando recordatorios de eventos...")
                
                # Obtener la hora actual
                now = datetime.utcnow()
                
                # Buscar eventos que necesitan recordatorio en los próximos 60 minutos
                upcoming_events = Event.query.filter(
                    Event.is_active == True,
                    Event.start_time > now,
                    Event.start_time <= now + timedelta(hours=1)
                ).all()
                
                for event in upcoming_events:
                    # Calcular cuándo enviar el recordatorio
                    reminder_time = event.start_time - timedelta(minutes=event.reminder_minutes)
                    
                    # Si es hora de enviar el recordatorio (con margen de 1 minuto)
                    if abs((reminder_time - now).total_seconds()) <= 60:
                        self.send_event_reminder(event)
                        
        except Exception as e:
            logger.error(f"Error verificando recordatorios: {e}")
    
    def send_event_reminder(self, event):
        """Enviar recordatorio de un evento específico"""
        try:
            with self.app_context():
                # Obtener configuraciones del usuario
                settings = UserSettings.query.filter_by(user_id=event.user_id).first()
                
                if not settings or not settings.telegram_chat_id or not settings.notifications_enabled:
                    logger.info(f"Usuario {event.user_id} no tiene Telegram configurado o notificaciones desactivadas")
                    return
                
                # Obtener bot de Telegram
                bot = get_telegram_bot()
                if not bot:
                    logger.error("Bot de Telegram no disponible")
                    return
                
                # Enviar recordatorio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        bot.send_reminder(settings.telegram_chat_id, event)
                    )
                    logger.info(f"Recordatorio enviado para evento {event.id}")
                finally:
                    loop.close()
                    
        except Exception as e:
            logger.error(f"Error enviando recordatorio para evento {event.id}: {e}")
    
    def send_daily_summaries(self):
        """Enviar resúmenes diarios a usuarios que lo tengan activado"""
        try:
            with self.app_context():
                logger.info("Enviando resúmenes diarios...")
                
                # Obtener usuarios con resumen diario activado
                users_with_summary = UserSettings.query.filter(
                    UserSettings.daily_summary_enabled == True,
                    UserSettings.telegram_chat_id.isnot(None)
                ).all()
                
                for settings in users_with_summary:
                    self.send_user_daily_summary(settings)
                    
        except Exception as e:
            logger.error(f"Error enviando resúmenes diarios: {e}")
    
    def send_user_daily_summary(self, settings):
        """Enviar resumen diario a un usuario específico"""
        try:
            with self.app_context():
                # Obtener eventos del día
                today = datetime.now().date()
                start_of_day = datetime.combine(today, datetime.min.time())
                end_of_day = datetime.combine(today, datetime.max.time())
                
                events = Event.query.filter(
                    Event.user_id == settings.user_id,
                    Event.is_active == True,
                    Event.start_time >= start_of_day,
                    Event.start_time <= end_of_day
                ).order_by(Event.start_time).all()
                
                # Obtener bot de Telegram
                bot = get_telegram_bot()
                if not bot:
                    logger.error("Bot de Telegram no disponible")
                    return
                
                # Enviar resumen
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        bot.send_daily_summary(settings.telegram_chat_id, events)
                    )
                    logger.info(f"Resumen diario enviado a usuario {settings.user_id}")
                finally:
                    loop.close()
                    
        except Exception as e:
            logger.error(f"Error enviando resumen diario a usuario {settings.user_id}: {e}")
    
    def cleanup_old_events(self):
        """Limpiar eventos antiguos (soft delete de eventos de más de 30 días)"""
        try:
            with self.app_context():
                logger.info("Limpiando eventos antiguos...")
                
                # Fecha límite (30 días atrás)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                # Marcar eventos antiguos como inactivos
                old_events = Event.query.filter(
                    Event.end_time < cutoff_date,
                    Event.is_active == True
                ).all()
                
                for event in old_events:
                    event.is_active = False
                
                if old_events:
                    db.session.commit()
                    logger.info(f"Marcados {len(old_events)} eventos como inactivos")
                else:
                    logger.info("No hay eventos antiguos para limpiar")
                    
        except Exception as e:
            logger.error(f"Error limpiando eventos antiguos: {e}")
            db.session.rollback()
    
    def schedule_event_reminder(self, event):
        """Programar recordatorio para un evento específico"""
        try:
            reminder_time = event.start_time - timedelta(minutes=event.reminder_minutes)
            
            # Solo programar si el recordatorio es en el futuro
            if reminder_time > datetime.utcnow():
                job_id = f"reminder_{event.id}"
                
                self.scheduler.add_job(
                    func=self.send_event_reminder,
                    trigger=DateTrigger(run_date=reminder_time),
                    args=[event],
                    id=job_id,
                    name=f'Recordatorio para evento {event.id}',
                    replace_existing=True
                )
                
                logger.info(f"Recordatorio programado para evento {event.id} a las {reminder_time}")
                
        except Exception as e:
            logger.error(f"Error programando recordatorio para evento {event.id}: {e}")
    
    def cancel_event_reminder(self, event_id):
        """Cancelar recordatorio de un evento"""
        try:
            job_id = f"reminder_{event_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Recordatorio cancelado para evento {event_id}")
        except Exception as e:
            logger.error(f"Error cancelando recordatorio para evento {event_id}: {e}")
    
    def reschedule_user_daily_summary(self, user_id, summary_time):
        """Reprogramar resumen diario para un usuario específico"""
        try:
            job_id = f"daily_summary_{user_id}"
            
            # Parsear hora (formato HH:MM)
            hour, minute = map(int, summary_time.split(':'))
            
            # Remover trabajo anterior si existe
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Programar nuevo trabajo
            self.scheduler.add_job(
                func=self.send_user_daily_summary_by_id,
                trigger=CronTrigger(hour=hour, minute=minute, second=0),
                args=[user_id],
                id=job_id,
                name=f'Resumen diario para usuario {user_id}',
                replace_existing=True
            )
            
            logger.info(f"Resumen diario reprogramado para usuario {user_id} a las {summary_time}")
            
        except Exception as e:
            logger.error(f"Error reprogramando resumen diario para usuario {user_id}: {e}")
    
    def send_user_daily_summary_by_id(self, user_id):
        """Enviar resumen diario por ID de usuario"""
        try:
            with self.app_context():
                settings = UserSettings.query.filter_by(user_id=user_id).first()
                if settings and settings.daily_summary_enabled:
                    self.send_user_daily_summary(settings)
        except Exception as e:
            logger.error(f"Error enviando resumen diario para usuario {user_id}: {e}")
    
    def get_scheduler_status(self):
        """Obtener estado del scheduler"""
        try:
            jobs = self.scheduler.get_jobs()
            return {
                'running': self.scheduler.running,
                'jobs_count': len(jobs),
                'jobs': [
                    {
                        'id': job.id,
                        'name': job.name,
                        'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    for job in jobs
                ]
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado del scheduler: {e}")
            return {'error': str(e)}
    
    def shutdown(self):
        """Detener el scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler detenido")
        except Exception as e:
            logger.error(f"Error deteniendo scheduler: {e}")

# Instancia global del scheduler
notification_scheduler = None

def init_scheduler(app_context):
    """Inicializar el scheduler de notificaciones"""
    global notification_scheduler
    notification_scheduler = NotificationScheduler(app_context)
    return notification_scheduler

def get_scheduler():
    """Obtener la instancia del scheduler"""
    return notification_scheduler