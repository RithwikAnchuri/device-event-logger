"""Simulated device that sends events to the AWS ingestion API.

Configuration comes from environment variables so no secrets live in the repo:
    API_URL  e.g. https://<api-id>.execute-api.<region>.amazonaws.com/dev/events
    API_KEY  the API Gateway key attached to the usage plan
"""
import os
import time
import uuid

import requests

URL = os.environ["API_URL"]
HEADERS = {"x-api-key": os.environ["API_KEY"]}


def send_event(device_id, event_type, event_id=None):
    payload = {
        "device_id": device_id,
        "event_id": event_id or str(uuid.uuid4()),
        "type": event_type,
    }
    r = requests.post(URL, json=payload, headers=HEADERS, timeout=5)
    print(r.status_code, r.json())
    return payload


if __name__ == "__main__":
    first = send_event("timer-01", "session_complete")  # new event -> 201
    time.sleep(1)
    # Simulate a network retry: same event_id sent again -> 409
    send_event("timer-01", "session_complete", event_id=first["event_id"])
    send_event("timer-01", "button_press")  # another new event -> 201
