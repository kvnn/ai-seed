import logging


LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"


def configure_logging() -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    return logging.getLogger("oahuai")


logger = configure_logging()
