import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///edgehealth.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_NAME = 'edgehealth_session'
    SESSION_COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_HOURS = int(os.getenv('SESSION_HOURS', '8'))
    LOGIN_MAX_ATTEMPTS = 10
    LOGIN_WINDOW_SECONDS = 900
    MAX_CONTENT_LENGTH = 64 * 1024
    MONITOR_INTERVAL = int(os.getenv('MONITOR_INTERVAL', '30'))
    MONITOR_PACKETS = int(os.getenv('MONITOR_PACKETS', '4'))
    MONITOR_TIMEOUT = float(os.getenv('MONITOR_TIMEOUT', '1'))
    MONITOR_WORKERS = int(os.getenv('MONITOR_WORKERS', '4'))
    MONITOR_LEASE_SECONDS = int(os.getenv('MONITOR_LEASE_SECONDS', '120'))
    OFFLINE_AFTER = int(os.getenv('OFFLINE_AFTER', '3'))
    RECOVERY_AFTER = int(os.getenv('RECOVERY_AFTER', '2'))
    LATENCY_LIMIT_MS = float(os.getenv('LATENCY_LIMIT_MS', '150'))
    LOSS_LIMIT_PCT = float(os.getenv('LOSS_LIMIT_PCT', '5'))
    DIAGNOSTIC_WINDOW_SECONDS = int(os.getenv('DIAGNOSTIC_WINDOW_SECONDS', '300'))
    STALE_AFTER_SECONDS = int(os.getenv('STALE_AFTER_SECONDS', '180'))
    SEVERITY_MEDIUM_MINUTES = 5
    SEVERITY_HIGH_MINUTES = 15
    SEVERITY_CRITICAL_MINUTES = 60
    SEVERITY_GROUP_SIZE = 3
    SEVERITY_HIGH_USERS = 10
    SEVERITY_CRITICAL_USERS = 50
    FRONTEND_DIST = str(Path(__file__).resolve().parents[2] / 'frontend' / 'dist')
