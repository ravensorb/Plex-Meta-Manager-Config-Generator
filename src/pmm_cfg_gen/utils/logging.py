#!/usr/bin/env python3
###################################################################################################

import logging
import logging.config
import logging.handlers
import os

import coloredlogs
import yaml


class RollingFileHanderEx(logging.handlers.RotatingFileHandler):
    def __init__(
        self,
        filename,
        mode: str = "a",
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: str | None = None,
        delay: bool = False,
        errors: str | None = None,
    ) -> None:
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay, errors)


def setup_logging(
    default_path="logging.yaml", default_level=logging.INFO, env_key="LOG_CFG"
):
    """
    | **@author:** Prathyush SP
    | Logging Setup
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, "rt") as f:
            try:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)
            except Exception as e:
                print(e)
                print("Error in Logging Configuration. Using default configs")
                logging.basicConfig(level=default_level)
                coloredlogs.install(level=default_level)
    else:
        logging.basicConfig(level=default_level)
        coloredlogs.install(level=default_level)
        print("Failed to load configuration file. Using default configs")
