def alert(request, message: str, level: str = "info"):
    """Adiciona uma mensagem de alerta na sessão."""
    if "alerts" not in request.session:
        request.session["alerts"] = []

    request.session["alerts"].append({"level": level, "message": message})


def alert_info(request, message: str):
    """Adiciona uma mensagem de alerta do tipo info na sessão."""
    alert(request, message, "info")


def alert_success(request, message: str):
    """Adiciona uma mensagem de alerta do tipo sucesso na sessão."""
    alert(request, message, "success")


def alert_error(request, message: str):
    """Adiciona uma mensagem de alerta do tipo erro na sessão."""
    alert(request, message, "error")


def get_alerts(request) -> list:
    """Retorna as mensagens de alerta da sessão."""
    return request.session.pop("alerts", None)
