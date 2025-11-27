
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
from dotenv import load_dotenv

load_dotenv()

class PrintToAzureHandler(logging.Handler):
    def __init__(self, connection_string):
        super().__init__()
        self.azure_handler = AzureLogHandler(connection_string=connection_string)

    def emit(self, record):
        log_entry = self.format(record)
        self.azure_handler.emit(record)


# Load Application Insights connection string from Azure Key Vault
from utils.config import get_config
config = get_config()
connection_string = config.get_app_insights_connection_string()
azure_handler = PrintToAzureHandler(connection_string)


import sys

class LoggerWriter:
    def __init__(self, level):
        self.level = level

    def write(self, message):
        if message != '\n':  # Ignore empty messages
            self.level(message)

    def flush(self):
        pass

logger = logging.getLogger('azure')
logger.setLevel(logging.INFO)
logger.addHandler(azure_handler)

# Add a StreamHandler to output to the console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

sys.stdout = LoggerWriter(logger.info)
sys.stderr = LoggerWriter(logger.error)
