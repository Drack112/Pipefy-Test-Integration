from dataclasses import dataclass


@dataclass
class WebhookPayloadDTO:
    event_id: str
    card_id: str
    client_email: str
    timestamp: str
