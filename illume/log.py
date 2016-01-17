"""Illume logging."""


from illume import config
from logging import getLogger


log = getLogger(name=config.get("LOG_NAME"))
