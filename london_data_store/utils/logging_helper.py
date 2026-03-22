"""Lightweight logging helpers.

Provides a BasicLogger class that wraps stdlib logging.getLogger()
with a consistent format and sensible defaults.
"""

import logging


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get or create a named logger with a console handler."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


class BasicLogger:
    """Convenience wrapper matching the original BasicLogger signature.

    Args:
        logger_name: Name for the underlying logger.
        verbose: Ignored (kept for backward compatibility).
        log_directory: Ignored (kept for backward compatibility).
        **kwargs: Ignored (kept for backward compatibility).
    """

    def __init__(self, logger_name: str = "app", verbose: bool = False, log_directory: str = None, **kwargs):
        self.logger = get_logger(logger_name)

    def debug(self, msg, *a, **kw):
        self.logger.debug(msg, *a, **kw)

    def info(self, msg, *a, **kw):
        self.logger.info(msg, *a, **kw)

    def warning(self, msg, *a, **kw):
        self.logger.warning(msg, *a, **kw)

    def error(self, msg, *a, **kw):
        self.logger.error(msg, *a, **kw)

    def critical(self, msg, *a, **kw):
        self.logger.critical(msg, *a, **kw)
