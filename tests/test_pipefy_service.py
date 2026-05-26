from unittest.mock import MagicMock, patch

import pytest

from app.integrations.pipefy import PipefyService


def _mock_http_response(body: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


def _patch_post(body: dict):
    mock_resp = _mock_http_response(body)
    return patch("httpx.Client.post", return_value=mock_resp)


class TestPipefyServiceCreateCard:
    def test_returns_card_id_on_success(self):
        body = {
            "data": {
                "createCard": {
                    "card": {
                        "id": "99999",
                        "title": "Test",
                        "current_phase": {"name": "Inbox"},
                    }
                }
            }
        }
        with _patch_post(body):
            service = PipefyService()
            card_id = service.create_card("Test User", "test@test.com", 50000)

        assert card_id == "99999"

    def test_raises_on_graphql_errors(self):
        body = {"errors": [{"message": "Unauthorized"}]}

        with _patch_post(body):
            service = PipefyService()
            with pytest.raises(RuntimeError, match="pipefy returned errors"):
                service.create_card("Test User", "test@test.com", 50000)

    def test_returns_none_when_token_not_set(self):
        with patch("app.integrations.pipefy.settings") as mock_settings:
            mock_settings.pipefy_token = ""
            service = PipefyService()
            result = service.create_card("Test", "test@test.com", 1000)

        assert result is None

    def test_sends_correct_field_ids(self):
        body = {
            "data": {
                "createCard": {
                    "card": {
                        "id": "111",
                        "title": "Lucas",
                        "current_phase": {"name": "Inbox"},
                    }
                }
            }
        }
        with _patch_post(body) as mock_post:
            service = PipefyService()
            service.create_card("Lucas", "lucas@test.com", 200000)

        _, kwargs = mock_post.call_args
        variables = kwargs["json"]["variables"]
        field_ids = [f["field_id"] for f in variables["fields_attributes"]]
        assert "nome_do_cliente" in field_ids
        assert "email" in field_ids
        assert "valor_patrim_nio" in field_ids


class TestPipefyServiceUpdateCard:
    def test_updates_status_and_priority_fields(self):
        body = {"data": {"updateCardField": {"card": {"id": "123"}, "success": True}}}

        with _patch_post(body) as mock_post:
            service = PipefyService()
            service.update_card("123", "Processado", "prioridade_alta")

        assert mock_post.call_count == 2
        calls_json = [c.kwargs["json"]["variables"] for c in mock_post.call_args_list]
        field_ids = [v["field_id"] for v in calls_json]
        assert "status" in field_ids
        assert "prioridade" in field_ids

    def test_raises_on_graphql_errors(self):
        body = {"errors": [{"message": "Card not found"}]}

        with _patch_post(body):
            service = PipefyService()
            with pytest.raises(RuntimeError, match="pipefy returned errors"):
                service.update_card("bad_id", "Processado", "prioridade_alta")

    def test_skips_when_token_not_set(self):
        with patch("app.integrations.pipefy.settings") as mock_settings:
            mock_settings.pipefy_token = ""
            service = PipefyService()
            service.update_card("123", "Processado", "prioridade_alta")
