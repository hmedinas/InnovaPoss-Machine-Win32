import functools
import uuid
from configparser import ConfigParser

import pika


def log_prefix(logger, label, prefix=list()):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            prefix.append(label)
            logger.extra['prefix'] = ':'.join(prefix)
            result = func(*args, **kwargs)
            prefix.pop()
            logger.extra['prefix'] = ':'.join(prefix)
            return result

        return wrapper

    return decorator


def get_with_default(config: ConfigParser, section: str, name: str, default):
    """
    Tries to extract the value from the configuration file. If such option does not exist, uses the default value. 
    """
    if config.has_option(section, name):
        return config.get(section, name)
    elif default is None:
        raise ValueError(f"Config value '{section}.{name}' has no default and has to be set.")
    else:
        return default


def Singleton(cls):
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]

    return getinstance


class PikaHelper:
    @staticmethod
    def get_reply_props_from_request(props: pika.BasicProperties):
        replyprops = pika.BasicProperties()
        replyprops.message_id = uuid.uuid4()

