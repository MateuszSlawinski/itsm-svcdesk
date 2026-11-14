"""Relay ticket events to the webhook URL a customer registered."""
import requests


def relay_event(callback_url: str, event: dict) -> int:
    """POST the event to the customer's callback URL and return the status code."""
    response = requests.post(callback_url, json=event, timeout=5)
    return response.status_code
