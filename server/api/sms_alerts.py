"""
Methane Shadow Hunter - Twilio SMS Alert Service.

Sends an SMS notification to the configured recipient for each new
methane super-emitter detection produced by the pipeline.

Configuration (server/.env):
    TWILIO_ACCOUNT_SID     – Twilio account SID
    TWILIO_AUTH_TOKEN      – Twilio auth token
    TWILIO_PHONE_NUMBER    – Twilio sender phone number (E.164 format)
    TWILIO_ALERT_RECIPIENT – Destination phone number (E.164 format)
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Priority label mapping
_PRIORITY_LABELS = {
    1: "CRITICAL",
    2: "HIGH",
    3: "MODERATE",
}

# Maximum individual detection SMS to send per pipeline run.
# Detections beyond this limit are batched into a single overflow summary
# to avoid sending hundreds of messages in one run.
MAX_INDIVIDUAL_ALERTS = 10


def _get_twilio_client():
    """
    Lazily import and initialise the Twilio REST client.
    Returns (client, from_number, to_number) or raises RuntimeError
    if Twilio credentials are not configured.
    """
    from django.conf import settings

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token  = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
    to_number   = getattr(settings, 'TWILIO_ALERT_RECIPIENT', '')

    missing = [k for k, v in {
        'TWILIO_ACCOUNT_SID':    account_sid,
        'TWILIO_AUTH_TOKEN':     auth_token,
        'TWILIO_PHONE_NUMBER':   from_number,
        'TWILIO_ALERT_RECIPIENT': to_number,
    }.items() if not v]

    if missing:
        raise RuntimeError(
            f"Twilio not configured. Missing settings: {', '.join(missing)}"
        )

    try:
        from twilio.rest import Client
    except ImportError as exc:
        raise RuntimeError(
            "twilio package is not installed. "
            "Run: pip install twilio>=9.0.0"
        ) from exc

    client = Client(account_sid, auth_token)
    return client, from_number, to_number


def _send_sms(body: str) -> bool:
    """
    Send a single SMS via Twilio.

    Args:
        body: Message text (keep under 160 chars for a single-segment SMS).

    Returns:
        True if sent successfully, False otherwise.
    """
    try:
        client, from_number, to_number = _get_twilio_client()
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number,
        )
        logger.info(
            "[SMS] Sent to %s | SID: %s | Status: %s",
            to_number, message.sid, message.status,
        )
        print(
            f"  [SMS] ✔ Alert sent → {to_number} | SID: {message.sid}"
        )
        return True
    except RuntimeError as exc:
        logger.warning("[SMS] Skipped – %s", exc)
        print(f"  [SMS] ⚠ Skipped – {exc}")
        return False
    except Exception as exc:
        logger.error("[SMS] Failed to send: %s", exc, exc_info=True)
        print(f"  [SMS] ✗ Failed – {exc}")
        return False


# ─── Public API ─────────────────────────────────────────────────────────────

def send_detection_alert(hotspot) -> bool:
    """
    Send an SMS alert for a single detected methane hotspot.

    Args:
        hotspot: DetectedHotspot-like object with attributes:
                 hotspot_id, latitude, longitude, severity,
                 anomaly_score, priority, ch4_count.

    Returns:
        True if the SMS was sent successfully.
    """
    priority_label = _PRIORITY_LABELS.get(getattr(hotspot, 'priority', 3), 'MODERATE')
    severity       = getattr(hotspot, 'severity', 'Unknown')
    lat            = float(getattr(hotspot, 'latitude', 0))
    lon            = float(getattr(hotspot, 'longitude', 0))
    score          = float(getattr(hotspot, 'anomaly_score', 0))
    ch4            = int(getattr(hotspot, 'ch4_count', 0))
    hid            = getattr(hotspot, 'hotspot_id', 'N/A')
    ts             = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

    body = (
        f"[MSH ALERT] {priority_label} Methane Detection\n"
        f"ID: {hid}\n"
        f"Severity: {severity} | Score: {score:.2f}σ\n"
        f"Location: {lat:.4f}°N, {lon:.4f}°E\n"
        f"CH4 Count: {ch4}\n"
        f"Time: {ts}"
    )
    return _send_sms(body)


def send_detections_batch(hotspots: list, run_pk=None) -> dict:
    """
    Send SMS alerts for a list of detected hotspots.

    Sends individual SMS messages for each detection up to
    MAX_INDIVIDUAL_ALERTS.  If there are more detections, a single
    overflow summary SMS is sent for the remainder.

    Args:
        hotspots: List of detected hotspot objects.
        run_pk:   Pipeline run ID (shown in overflow summary).

    Returns:
        dict with keys 'sent', 'failed', 'total'.
    """
    if not hotspots:
        return {'sent': 0, 'failed': 0, 'total': 0}

    sent   = 0
    failed = 0
    total  = len(hotspots)

    primary   = hotspots[:MAX_INDIVIDUAL_ALERTS]
    overflow  = hotspots[MAX_INDIVIDUAL_ALERTS:]

    # Individual alerts
    for hs in primary:
        ok = send_detection_alert(hs)
        if ok:
            sent += 1
        else:
            failed += 1

    # Overflow summary (one SMS for the rest)
    if overflow:
        critical = sum(1 for h in overflow if getattr(h, 'priority', 3) == 1)
        high     = sum(1 for h in overflow if getattr(h, 'priority', 3) == 2)
        mod      = sum(1 for h in overflow if getattr(h, 'priority', 3) >= 3)
        run_info = f" (Run #{run_pk})" if run_pk else ""
        body = (
            f"[MSH ALERT] +{len(overflow)} more detections{run_info}\n"
            f"Critical: {critical} | High: {high} | Moderate: {mod}\n"
            f"Check the dashboard for full details."
        )
        ok = _send_sms(body)
        if ok:
            sent += 1
        else:
            failed += 1

    return {'sent': sent, 'failed': failed, 'total': total}


def send_pipeline_summary(run, stats: dict) -> bool:
    """
    Send a single pipeline-completion summary SMS.

    Args:
        run:   PipelineRun model instance.
        stats: Dict with keys total_hotspots, detected, critical, high, moderate.

    Returns:
        True if sent successfully.
    """
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    body = (
        f"[MSH] Pipeline #{run.pk} Complete\n"
        f"Hotspots scanned : {stats.get('total_hotspots', 0)}\n"
        f"Detected         : {stats.get('detected', 0)} super-emitters\n"
        f"  Critical: {stats.get('critical', 0)} | High: {stats.get('high', 0)} "
        f"| Moderate: {stats.get('moderate', 0)}\n"
        f"Time: {ts}"
    )
    return _send_sms(body)
