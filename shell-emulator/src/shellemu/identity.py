"""Данные о реальной ОС: имя пользователя и имя компьютера."""
import getpass
import socket

DEFAULT_USER = "user"
DEFAULT_HOST = "localhost"


def current_user():
    """Возвращает имя текущего пользователя ОС."""
    try:
        return getpass.getuser() or DEFAULT_USER
    except (KeyError, OSError, ImportError):
        return DEFAULT_USER


def hostname():
    """Возвращает имя компьютера."""
    try:
        return socket.gethostname() or DEFAULT_HOST
    except OSError:
        return DEFAULT_HOST


def window_title(user, host):
    """Формирует заголовок окна: Эмулятор - [user@host]."""
    return f"Эмулятор - [{user}@{host}]"
