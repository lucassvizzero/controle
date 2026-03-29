"""Testes unitários para core/utils.py."""
from core.utils import alert, alert_error, alert_info, alert_success, get_alerts


def _mock_request(initial_alerts=None):
    """Cria um request fake com sessão em dicionário."""
    class FakeRequest:
        session = {}
    req = FakeRequest()
    if initial_alerts is not None:
        req.session["alerts"] = initial_alerts
    return req


class TestAlert:
    def test_alert_info_adds_to_session(self):
        req = _mock_request()
        alert_info(req, "Mensagem informativa")
        assert req.session["alerts"] == [{"level": "info", "message": "Mensagem informativa"}]

    def test_alert_success_adds_to_session(self):
        req = _mock_request()
        alert_success(req, "Operação realizada")
        assert req.session["alerts"][0]["level"] == "success"
        assert req.session["alerts"][0]["message"] == "Operação realizada"

    def test_alert_error_adds_to_session(self):
        req = _mock_request()
        alert_error(req, "Algo deu errado")
        assert req.session["alerts"][0]["level"] == "error"

    def test_multiple_alerts_accumulate(self):
        req = _mock_request()
        alert_success(req, "Primeiro")
        alert_error(req, "Segundo")
        assert len(req.session["alerts"]) == 2

    def test_alert_creates_list_when_absent(self):
        req = _mock_request()
        assert "alerts" not in req.session
        alert(req, "Teste", level="info")
        assert "alerts" in req.session

    def test_alert_default_level_is_info(self):
        req = _mock_request()
        alert(req, "Sem nível")
        assert req.session["alerts"][0]["level"] == "info"


class TestGetAlerts:
    def test_returns_alerts_list(self):
        req = _mock_request(initial_alerts=[{"level": "success", "message": "OK"}])
        alerts = get_alerts(req)
        assert alerts == [{"level": "success", "message": "OK"}]

    def test_clears_alerts_from_session(self):
        req = _mock_request(initial_alerts=[{"level": "error", "message": "Erro"}])
        get_alerts(req)
        assert "alerts" not in req.session

    def test_returns_none_when_no_alerts(self):
        req = _mock_request()
        result = get_alerts(req)
        assert result is None

    def test_does_not_raise_when_session_empty(self):
        req = _mock_request()
        result = get_alerts(req)
        assert result is None
