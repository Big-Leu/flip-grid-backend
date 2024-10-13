import logging


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    :param name: the name of the logger.
    :return: the logger.
    """

    # Create a logger
    logger = logging.getLogger(name)

    # Set the log level
    logger.setLevel(logging.INFO)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create a formatter and add it to the console handler
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

    return logger
