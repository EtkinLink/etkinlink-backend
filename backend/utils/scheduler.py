"""
Event Status Scheduler
APScheduler kullanarak event status'larını otomatik günceller.
Her saat başında tarihi geçmiş event'leri COMPLETED'e çeker.
"""

import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import Engine, text
from flask import Flask

# Logger setup
logger = logging.getLogger(__name__)


def update_completed_events(engine: Engine) -> dict:
    """
    Tarihi geçmiş event'leri COMPLETED status'una günceller.
    
    Args:
        engine: SQLAlchemy database engine
        
    Returns:
        dict: Güncelleme sonuçları (updated_count, errors)
    """
    try:
        logger.info("Starting event status update job...")
        
        with engine.connect() as conn:
            # SQL query: Tarihi geçmiş FUTURE event'leri bul ve COMPLETED'e çek
            update_query = text("""
                UPDATE events
                SET status = 'COMPLETED', updated_at = NOW()
                WHERE status = 'FUTURE'
                  AND (
                      (ends_at IS NOT NULL AND ends_at < NOW())
                      OR
                      (ends_at IS NULL AND starts_at < NOW())
                  )
            """)
            
            result = conn.execute(update_query)
            updated_count = result.rowcount
            conn.commit()
            
            logger.info(f"Event status update completed. Updated {updated_count} events to COMPLETED.")
            
            return {
                "success": True,
                "updated_count": updated_count,
                "timestamp": datetime.now().isoformat(),
                "errors": None
            }
            
    except Exception as e:
        error_msg = f"Error updating event statuses: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "updated_count": 0,
            "timestamp": datetime.now().isoformat(),
            "errors": error_msg
        }


def manual_trigger_update(engine: Engine) -> dict:
    """
    Manuel olarak event status güncelleme işlemini tetikler.
    Admin endpoint'i tarafından kullanılır.
    
    Args:
        engine: SQLAlchemy database engine
        
    Returns:
        dict: Güncelleme sonuçları
    """
    logger.info("Manual event status update triggered by admin")
    return update_completed_events(engine)


def init_scheduler(app: Flask) -> Optional[BackgroundScheduler]:
    """
    APScheduler'ı başlatır ve event status güncelleme job'ını ekler.
    
    Args:
        app: Flask application instance
        
    Returns:
        BackgroundScheduler: Başlatılmış scheduler instance veya None
    """
    try:
        # SKIP_SCHEDULER env var kontrolü
        skip_scheduler = app.config.get('SKIP_SCHEDULER', 'false').lower() == 'true'
        if skip_scheduler:
            logger.info("Scheduler disabled via SKIP_SCHEDULER environment variable")
            return None
        
        # Scheduler'ı oluştur
        scheduler = BackgroundScheduler(
            timezone='Europe/Istanbul',
            daemon=True
        )
        
        # Job'ı ekle: Her saat başında çalış
        scheduler.add_job(
            func=update_completed_events,
            args=[app.engine],
            trigger=CronTrigger(
                minute=0,  # Her saat başında (00:00, 01:00, 02:00...)
                timezone='Europe/Istanbul'
            ),
            id='update_event_statuses',
            name='Update Event Statuses to COMPLETED (Hourly)',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=1800  # 30 dakika grace time
        )
        
        # Scheduler'ı başlat
        scheduler.start()
        
        logger.info("Event status scheduler started successfully")
        logger.info("Next run: Every hour at minute 0 (Europe/Istanbul)")
        
        return scheduler
        
    except Exception as e:
        error_msg = f"Failed to initialize scheduler: {str(e)}"
        logger.error(error_msg)
        return None


def get_scheduler_status(scheduler: Optional[BackgroundScheduler]) -> dict:
    """
    Scheduler durumunu döndürür.
    Admin endpoint'i tarafından kullanılır.
    
    Args:
        scheduler: BackgroundScheduler instance veya None
        
    Returns:
        dict: Scheduler durumu ve job bilgileri
    """
    if scheduler is None:
        return {
            "running": False,
            "reason": "Scheduler not initialized or disabled",
            "jobs": [],
            "next_run": None
        }
    
    try:
        jobs_info = []
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "running": scheduler.running,
            "state": scheduler.state,
            "jobs": jobs_info,
            "timezone": "Europe/Istanbul"
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        return {
            "running": False,
            "reason": f"Error: {str(e)}",
            "jobs": [],
            "next_run": None
        }
