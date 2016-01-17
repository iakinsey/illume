"""
Configuration management.

Environment must be set before use.

Call .get() to obtain configuration variable. If the variable does not exist
in the set environment, then
"""


CONFIG_KEY = "config_class"
ENV = {}


class EMPTY:
    """
    Signifies that a default value was not set. Should trigger an error if
    default is set to EMPTY and an attribute does not exist.
    """

    pass


class Config:
    no_config_err = "No such config variable {}"

    def __init__(self, name, fallback):
        from importlib import import_module
        from os import listdir
        from os.path import dirname

        self.config_path = dirname(__file__)
        self.name = name
        self.fallback = fallback

        # List of config modules available
        self.config_modules = set([
            i.strip(".py")
            for i in listdir(self.config_path)
            if ".py" in i and i != "__init__.py"
        ])

        if name not in self.config_modules:
            err = "Config environment {} does not exist".format(name)

            raise AttributeError(err)

        if self.fallback:
            # Fallback configuration module.
            self.base = import_module("illume.config.base")

        # Desired configuration module.
        self.module = import_module("illume.config.{}".format(self.name))

    def get(self, name, default):
        value = getattr(self.module, name, default)

        if value != EMPTY:
            return value
        elif value == EMPTY and not self.fallback:
            raise AttributeError(self.no_config_err.format(name))
        elif value == EMPTY and self.fallback:
            value = getattr(self.base, name, default)

            if value == EMPTY:
                raise AttributeError(self.no_config_err.format(name))

            return value


def setenv(name, fallback=True):
    """
    Set configuration environment.
    """

    if CONFIG_KEY in ENV:
        raise AttributeError("Config environment already set.")

    config_class = Config(name, fallback)

    ENV[CONFIG_KEY] = config_class


def get(name, default=EMPTY):
    """
    Get configuration variable.
    """

    config_class = ENV.get(CONFIG_KEY, None)

    if config_class is None:
        raise AttributeError("Config environment not set.")

    return config_class.get(name, default)
