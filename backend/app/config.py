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
    # Remote collectors (HTTPS ingestion).
    COLLECTOR_STALE_SECONDS = int(os.getenv('COLLECTOR_STALE_SECONDS', '180'))
    COLLECTOR_MAX_BATCH = int(os.getenv('COLLECTOR_MAX_BATCH', '200'))
    COLLECTOR_MAX_REQUESTS_PER_MINUTE = int(os.getenv('COLLECTOR_MAX_REQUESTS_PER_MINUTE', '120'))
    COLLECTOR_MAX_SAMPLE_AGE_HOURS = int(os.getenv('COLLECTOR_MAX_SAMPLE_AGE_HOURS', '24'))
    COLLECTOR_MAX_CLOCK_SKEW_SECONDS = int(os.getenv('COLLECTOR_MAX_CLOCK_SKEW_SECONDS', '120'))
    COLLECTOR_MAX_CONTENT_LENGTH = 512 * 1024
    # Privacy and operations.
    TERMS_VERSION = os.getenv('TERMS_VERSION', '2026-10')
    # Optional generative AI (Gemini): plain-language explanation of an incident. No key = disabled.
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash').strip()
    GEMINI_TIMEOUT_SECONDS = float(os.getenv('GEMINI_TIMEOUT_SECONDS', '20'))
    IA_EXPLICACOES_POR_HORA = int(os.getenv('IA_EXPLICACOES_POR_HORA', '10'))
    METRIC_RETENTION_DAYS = int(os.getenv('METRIC_RETENTION_DAYS', '180'))
    TRUST_PROXY = int(os.getenv('TRUST_PROXY', '0'))
    FRONTEND_DIST =str(Path(__file__).resolve().parents[2] / 'frontend' / 'dist')
