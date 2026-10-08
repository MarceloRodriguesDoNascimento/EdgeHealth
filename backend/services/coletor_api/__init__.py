"""Collector protocol (HTTPS): authentication, configuration, heartbeat and idempotent ingestion.

The collector only measures (packets sent/received and latency). Status, incidents, severity and
diagnosis are always derived here, by the same RegistrarMedicaoService used by the local worker.
"""
