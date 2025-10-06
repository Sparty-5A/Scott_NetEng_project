import os, sys, logging
from loguru import logger

class InterceptHandler(logging.Handler):
    """Bridge stdlib logging -> Loguru, preserving level and caller site."""
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logging(log_dir: str = "logs", console_user_only: bool = True):
    """Configure Loguru with (1) file DEBUG sink and (2) optional console sink for user-output.
    Returns (logger, console) where `console` is a bound logger that prints to stdout when used.
    """
    os.makedirs(log_dir, exist_ok=True)
    logger.remove()

    # Send all stdlib logging (Nornir/Netmiko/etc.) to Loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG)
    for name in ("nornir", "nornir.core", "nornir.plugins", "paramiko", "netmiko"):
        logging.getLogger(name).setLevel(logging.DEBUG)

    # File sink: capture everything
    logger.add(
        os.path.join(log_dir, "nornir_debug.log"),
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    # Console: only show messages explicitly bound with channel="stdout"
    if console_user_only:
        def _stdout_filter(record):
            return record["extra"].get("channel") == "stdout"
        logger.add(sys.stdout, level="INFO", filter=_stdout_filter, colorize=True, format="<level>{message}</level>")
        console = logger.bind(channel="stdout")
    else:
        logger.add(sys.stdout, level="INFO", colorize=True, format="<level>{message}</level>")
        console = logger

    return logger, console
