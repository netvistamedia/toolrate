from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.tool import Tool  # noqa: E402, F401
from app.models.report import ExecutionReport  # noqa: E402, F401
from app.models.score_cache import ScoreSnapshot  # noqa: E402, F401
from app.models.api_key import ApiKey  # noqa: E402, F401
from app.models.alternative import Alternative  # noqa: E402, F401
from app.models.webhook import Webhook  # noqa: E402, F401
from app.models.audit_log import AuditLog  # noqa: E402, F401
from app.models.tool_pricing_history import ToolPricingHistory  # noqa: E402, F401
from app.models.payg_meter_event import PaygMeterEvent  # noqa: E402, F401
