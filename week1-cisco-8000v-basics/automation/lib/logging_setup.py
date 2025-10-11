import os
import sys
import logging
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


def setup_logging(log_dir: str = "logs", console_level: str = "INFO"):
    """
    Configure Loguru with dual-sink logging:
    1. File sink: captures ALL logs at DEBUG level
    2. Console sink: shows only explicit console.info/success/warning/error calls

    Returns:
        tuple: (debug_logger, console_logger)
            - debug_logger: For internal/debug messages (goes to file only)
            - console_logger: For user-facing messages (goes to both file + console)

    Usage:
        logger, console = setup_logging()
        logger.debug("Internal detail")  # File only
        console.info("User message")     # File + Console
    """
    os.makedirs(log_dir, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Intercept stdlib logging (Nornir, Netmiko, Paramiko, etc.)
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG, force=True)

    # Set levels for noisy libraries
    for name in ("nornir", "nornir.core", "paramiko", "netmiko", "urllib3"):
        logging.getLogger(name).setLevel(logging.DEBUG)

    # 1) FILE SINK: Everything at DEBUG level
    logger.add(
        os.path.join(log_dir, "nornir_debug.log"),
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    # 2) CONSOLE SINK: Only messages tagged with console=True
    def console_filter(record):
        """Only allow messages explicitly marked for console output."""
        return record["extra"].get("console", False)

    logger.add(
        sys.stdout,
        level=console_level,
        filter=console_filter,
        colorize=True,
        format="<level>{message}</level>"
    )

    # Create two bound loggers
    debug_logger = logger  # Goes to file only (no console=True tag)
    console_logger = logger.bind(console=True)  # Goes to file + console

    return debug_logger, console_logger