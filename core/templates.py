from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
templates.env.filters["strftime"] = lambda value, fmt: value.strftime(fmt) if value else ""
templates.env.filters["currency"] = lambda value: f"R$ {value:,.2f}" if value else ""
