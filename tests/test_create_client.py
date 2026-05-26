from unittest.mock import patch

import pytest


CREATE_MUTATION = """
mutation {
  createClient(input: {
    clientName: "%s"
    clientEmail: "%s"
    requestType: "%s"
    patrimonyValue: %s
  }) {
    id name email requestType patrimonyValue status priority
  }
}
"""


@pytest.fixture(autouse=True)
def mock_pipefy_create():
    with patch(
        "app.integrations.pipefy.PipefyService.create_card",
        return_value="card_test_001",
    ):
        yield


def _create(
    client,
    name="John Silva",
    email="john@test.com",
    request_type="Account Opening",
    patrimony_value=100000,
):
    resp = client.post(
        "/graphql",
        json={"query": CREATE_MUTATION % (name, email, request_type, patrimony_value)},
    )
    assert resp.status_code == 200
    return resp.json()


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.post("/graphql", json={"query": "{ health }"})

        assert resp.status_code == 200
        assert resp.json()["data"]["health"] == "ok"

    def test_health_has_no_errors(self, client):
        resp = client.post("/graphql", json={"query": "{ health }"})

        assert "errors" not in resp.json()


class TestCreateClient:
    def test_valid_payload_returns_client(self, client):
        body = _create(client)

        data = body["data"]["createClient"]
        assert data["id"] is not None
        assert data["name"] == "John Silva"
        assert data["email"] == "john@test.com"
        assert data["requestType"] == "Account Opening"
        assert data["patrimonyValue"] == 100000.0
        assert data["status"] == "Aguardando Análise"
        assert data["priority"] is None

    def test_client_persisted_in_database(self, client, db_factory):
        from app.db.models.client import ClientModel

        _create(client, email="persist@test.com")

        db = db_factory()
        try:
            record = db.query(ClientModel).filter_by(email="persist@test.com").first()
            assert record is not None
            assert record.name == "John Silva"
            assert record.status == "Aguardando Análise"
            assert record.pipefy_card_id == "card_test_001"
        finally:
            db.close()

    def test_duplicate_email_rejected(self, client):
        _create(client, email="dup@test.com")
        body = _create(client, email="dup@test.com")

        assert body["data"] is None
        assert "already registered" in body["errors"][0]["message"]

    def test_invalid_email_rejected(self, client):
        body = _create(client, email="not-an-email")

        assert body["data"] is None
        assert "invalid email" in body["errors"][0]["message"]

    def test_empty_name_rejected(self, client):
        body = _create(client, name="   ")

        assert body["data"] is None
        assert "name is required" in body["errors"][0]["message"]

    def test_negative_patrimony_value_rejected(self, client):
        body = _create(client, patrimony_value=-1)

        assert body["data"] is None
        assert "patrimony_value" in body["errors"][0]["message"]
