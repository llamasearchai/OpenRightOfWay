import logging

try:
    from rich.logging import RichHandler
    _HAS_RICH = True
except Exception:  # pragma: no cover
    _HAS_RICH = False

_LOGGING_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging once.

    Uses RichHandler when available for better formatting.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    if _HAS_RICH:
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, markup=True)],
        )
    else:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    _LOGGING_CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name if name else "openrightofway")

