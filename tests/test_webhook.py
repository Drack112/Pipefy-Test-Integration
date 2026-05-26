from unittest.mock import patch

import pytest


WEBHOOK_URL = "/webhooks/pipefy/card-updated"

CREATE_MUTATION = """
mutation {
  createClient(input: {
    clientName: "%s"
    clientEmail: "%s"
    requestType: "Account Opening"
    patrimonyValue: %s
  }) {
    id email status
  }
}
"""


@pytest.fixture(autouse=True)
def mock_pipefy():
    with patch(
        "app.integrations.pipefy.PipefyService.create_card",
        return_value="card_test_001",
    ):
        with patch("app.integrations.pipefy.PipefyService.update_card"):
            yield


def _create_client(client, name, email, patrimony_value):
    resp = client.post(
        "/graphql",
        json={"query": CREATE_MUTATION % (name, email, patrimony_value)},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["createClient"]["id"]


def _webhook(client, event_id, card_id, email):
    return client.post(
        WEBHOOK_URL,
        json={
            "event_id": event_id,
            "card_id": card_id,
            "client_email": email,
            "timestamp": "2026-05-26T12:00:00Z",
        },
    )


class TestWebhookPriority:
    def test_high_priority_when_patrimony_equal_to_threshold(self, client):
        _create_client(client, "Maria High", "high@test.com", 200000)

        resp = _webhook(client, "evt_001", "card_001", "high@test.com")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "processed"
        assert body["priority"] == "prioridade_alta"

    def test_high_priority_when_patrimony_above_threshold(self, client):
        _create_client(client, "Peter Rich", "rich@test.com", 500000)

        resp = _webhook(client, "evt_002", "card_002", "rich@test.com")

        assert resp.status_code == 200
        assert resp.json()["priority"] == "prioridade_alta"

    def test_normal_priority_when_patrimony_below_threshold(self, client):
        _create_client(client, "Ana Normal", "normal@test.com", 199999)

        resp = _webhook(client, "evt_003", "card_003", "normal@test.com")

        assert resp.status_code == 200
        assert resp.json()["priority"] == "prioridade_normal"

    def test_local_db_updated_to_processed(self, client, db_factory):
        from app.db.models.client import ClientModel

        _create_client(client, "Carlos DB", "db@test.com", 300000)
        _webhook(client, "evt_004", "card_004", "db@test.com")

        db = db_factory()
        try:
            record = db.query(ClientModel).filter_by(email="db@test.com").first()
            assert record.status == "Processado"
            assert record.priority == "prioridade_alta"
        finally:
            db.close()

    def test_pipefy_update_called_with_correct_args(self, client):
        _create_client(client, "Luiza P", "luiza@test.com", 250000)

        with patch("app.integrations.pipefy.PipefyService.update_card") as mock_update:
            _webhook(client, "evt_005", "card_005", "luiza@test.com")

            mock_update.assert_called_once_with(
                card_id="card_005",
                status="Processado",
                priority="prioridade_alta",
            )


class TestWebhookIdempotency:
    def test_duplicate_event_id_returns_duplicate_status(self, client):
        _create_client(client, "Lucas Idem", "idem@test.com", 100000)

        resp1 = _webhook(client, "evt_idem", "card_idem", "idem@test.com")
        resp2 = _webhook(client, "evt_idem", "card_idem", "idem@test.com")

        assert resp1.json()["status"] == "processed"
        assert resp2.json()["status"] == "duplicate"
        assert resp2.json()["event_id"] == "evt_idem"

    def test_duplicate_does_not_call_pipefy_again(self, client):
        _create_client(client, "Sofia Idem", "sofia@test.com", 250000)

        with patch("app.integrations.pipefy.PipefyService.update_card") as mock_update:
            _webhook(client, "evt_dedup", "card_dedup", "sofia@test.com")
            _webhook(client, "evt_dedup", "card_dedup", "sofia@test.com")

            assert mock_update.call_count == 1

    def test_duplicate_does_not_write_event_twice(self, client, db_factory):
        from app.db.models.webhook_event import WebhookEvent

        _create_client(client, "Bruno Multi", "multi@test.com", 100000)

        _webhook(client, "evt_once", "card_001", "multi@test.com")
        _webhook(client, "evt_once", "card_001", "multi@test.com")

        db = db_factory()
        try:
            count = db.query(WebhookEvent).filter_by(event_id="evt_once").count()
            assert count == 1
        finally:
            db.close()

    def test_different_event_ids_both_processed(self, client):
        _create_client(client, "Vera Two", "vera@test.com", 100000)

        resp1 = _webhook(client, "evt_a", "card_001", "vera@test.com")
        resp2 = _webhook(client, "evt_b", "card_001", "vera@test.com")

        assert resp1.json()["status"] == "processed"
        assert resp2.json()["status"] == "processed"


class TestWebhookErrors:
    def test_unknown_email_returns_404(self, client):
        resp = _webhook(client, "evt_404", "card_404", "unknown@test.com")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_pipefy_failure_does_not_fail_webhook(self, client):
        _create_client(client, "Jane Fail", "fail@test.com", 400000)

        with patch(
            "app.integrations.pipefy.PipefyService.update_card",
            side_effect=RuntimeError("pipefy timeout"),
        ):
            resp = _webhook(client, "evt_fail", "card_fail", "fail@test.com")

        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

    def test_pipefy_failure_still_persists_to_db(self, client, db_factory):
        from app.db.models.client import ClientModel

        _create_client(client, "Roy Fail", "roy@test.com", 300000)

        with patch(
            "app.integrations.pipefy.PipefyService.update_card",
            side_effect=RuntimeError("pipefy down"),
        ):
            _webhook(client, "evt_fail2", "card_fail2", "roy@test.com")

        db = db_factory()
        try:
            record = db.query(ClientModel).filter_by(email="roy@test.com").first()
            assert record.status == "Processado"
            assert record.priority == "prioridade_alta"
        finally:
            db.close()
