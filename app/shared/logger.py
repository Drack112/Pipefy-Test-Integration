import logging
import sys

_DEV_FMT = (
    "%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(funcName)s — %(message)s"
)
_PROD_FMT = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'


def setup_logging(debug: bool = False, env: str = "development") -> None:
    if debug:
        level = logging.DEBUG
    elif env == "production":
        level = logging.WARNING
    else:
        level = logging.INFO

    fmt = _DEV_FMT if env != "production" else _PROD_FMT
    logging.basicConfig(level=level, format=fmt, stream=sys.stdout, force=True)

    logging.getLogger("strawberry.execution").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
