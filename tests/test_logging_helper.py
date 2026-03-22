"""Tests for london_data_store.utils.logging_helper module."""

import logging

from london_data_store.utils.logging_helper import BasicLogger, get_logger


class TestGetLogger:
    def test_returns_logger(self):
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_has_handler(self):
        logger = get_logger("test_handler_logger")
        assert len(logger.handlers) >= 1

    def test_no_propagation(self):
        logger = get_logger("test_no_prop")
        assert logger.propagate is False


class TestBasicLogger:
    def test_instantiation(self):
        bl = BasicLogger(logger_name="test_bl", verbose=False, log_directory=None)
        assert bl.logger.name == "test_bl"

    def test_info_method(self, capsys):
        bl = BasicLogger(logger_name="test_info_bl")
        bl.info("test message")
        # No exception means it works

    def test_backward_compat_kwargs(self):
        """verbose and log_directory are accepted but ignored."""
        bl = BasicLogger(verbose=True, log_directory="/tmp/logs", logger_name="compat_test")
        assert bl.logger is not None
