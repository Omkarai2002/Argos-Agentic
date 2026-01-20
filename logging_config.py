import logging
import logging.config
import os

class LoggerFeature:
    @staticmethod
    def setup_logging():
        env = os.getenv("APP_ENV", "dev")

        if env == "prod":
            config_path = "config/logging_prod.conf"
        else:
            config_path = "config/logging_dev.conf"

        logging.config.fileConfig(config_path, disable_existing_loggers=False)
