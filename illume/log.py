"""Illume logging."""


from illume import config
from logging import getLogger, DEBUG


log = getLogger(name=config.get("LOG_NAME"))
