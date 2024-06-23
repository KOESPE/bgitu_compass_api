import configparser

from config import LOCALE_FILE


def loc(section: str, key: str, *args) -> str:
    config = configparser.ConfigParser()

    with open(LOCALE_FILE, 'r', encoding='UTF-8') as f:
        config.read_file(f)
    try:
        if len(args) > 0:
            value = config.get(section, key).format(*args)
        else:
            value = config.get(section, key)
        return value
    except configparser.NoSectionError:
        return f"Key '{key}' не найден в файле локализации."
    except configparser.NoOptionError:
        return f"Section '{section}' не найден в файле конфигурации."



