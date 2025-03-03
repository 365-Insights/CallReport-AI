import logging
import json
from typing import Literal
from datetime import datetime
import os
from constants import SingletonMeta
# from opencensus.ext.azure.log_exporter import AzureLogHandler

from dotenv import load_dotenv

class CustomFormatter(logging.Formatter):
    def format(self, record):
        dtime = self.formatTime(record, self.datefmt)
        msg = record.getMessage()
        level = record.levelname
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # return json.dumps(log_record, ensure_ascii=True)
        return f"{level}|{dtime}|{msg}"

    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3]


class CustomLogger(metaclass=SingletonMeta):
    def __init__(self, severity_level: Literal["debug", "info", "warning", "error", "fatal"], instrumentation_key: str = None):
        self.__level_to_log_object = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "fatal": logging.CRITICAL,
        }
        self.__init__logger(self.__level_to_log_object.get(severity_level, logging.INFO), instrumentation_key)


    def __init__logger(self, level: int, instrumentation_key: str = None):
        self.__logger = logging.Logger('custom_logger', level)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        # console_handler.setFormatter(CustomFormatter())
        self.__logger.addHandler(console_handler)
        # if instrumentation_key:
        #     azure_handler = AzureLogHandler(connection_string=f'InstrumentationKey={instrumentation_key}')
        #     azure_handler.setLevel(level)
        #     self.__logger.addHandler(azure_handler)
        

    def debug(self, msg: str, extra: dict = None):
        self.__logger.debug(msg, extra=extra)

    def info(self, msg: str, extra: dict = None):
        self.__logger.info(msg, extra=extra)

    def warning(self, msg: str, extra: dict = None):
        self.__logger.warning(msg, extra=extra)

    def error(self, msg: str, extra: dict = None):
        self.__logger.error(msg, extra=extra)

    def fatal(self, msg: str, extra: dict = None):
        self.__logger.critical(msg, extra=extra)

instrument_key = load_dotenv()
instrument_key = os.getenv("INSTRUMENT_KEY", None)

logging.basicConfig(level=logging.CRITICAL)
LOGGER = CustomLogger("debug", instrument_key)
