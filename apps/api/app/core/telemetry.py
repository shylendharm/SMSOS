from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_business_id: ContextVar[str | None] = ContextVar("business_id", default=None)


def set_request_id(value: str):
    _request_id.set(value)


def get_request_id() -> str | None:
    return _request_id.get()


def set_correlation_id(value: str):
    _correlation_id.set(value)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_business_id(value: str):
    _business_id.set(value)


def get_business_id() -> str | None:
    return _business_id.get()


def clear_telemetry_context():
    _request_id.set(None)
    _correlation_id.set(None)
    _business_id.set(None)