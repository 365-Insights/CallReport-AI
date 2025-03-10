
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
import os
from dotenv import load_dotenv

load_dotenv()

class PrintToAzureHandler(logging.Handler):
    def __init__(self, connection_string):
        super().__init__()
        self.azure_handler = AzureLogHandler(connection_string=connection_string)

    def emit(self, record):
        log_entry = self.format(record)
        self.azure_handler.emit(record)


# Replace 'your_connection_string' with your actual Azure Application Insights connection string
instrumentation_key = os.getenv("AZURE_APP_INSIGHTS")
connection_string=f'{instrumentation_key}'
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
