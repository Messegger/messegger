import tomllib
import logging
import datetime
import os

with open("configs/config.toml", "rb") as file:
    config = tomllib.load(file)

logging_level = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

for i in ['./data/logs', './data/database']:
    if not os.path.exists(i):
        os.makedirs(i, exist_ok=True)

logger = logging.getLogger()
logger.setLevel(logging_level[config["bot"]["logging_level"]])

log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
file_handler = logging.FileHandler(f'./data/logs/{current_time}.log', mode='w')
file_handler.setLevel(logging_level[config["bot"]["logging_level"]])
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging_level[config["bot"]["logging_level"]])
stream_handler.setFormatter(log_format)
logger.addHandler(stream_handler)
