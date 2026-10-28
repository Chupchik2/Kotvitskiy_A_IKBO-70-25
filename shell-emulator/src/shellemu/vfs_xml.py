"""Загрузка VFS из XML-файла (всё хранится только в памяти).

Формат::

    <vfs owner="root" group="root">
      <dir name="home" owner="user" mtime="2026-01-31T12:00:00">
        <file name="a.txt">текст</file>
        <file name="b.bin" encoding="base64">AAEC</file>
      </dir>
    </vfs>

Двоичные данные записываются в base64 (``encoding="base64"``).
"""
import base64
import xml.etree.ElementTree as ET
from datetime import datetime

from shellemu.vfs import DEFAULT_OWNER, Directory, File, Vfs


class VfsError(Exception):
    """Ошибка загрузки VFS (файл не найден, неверный формат)."""


def _parse_xml(path):
    """Читает XML-файл и возвращает корневой элемент."""
    try:
        return ET.parse(path).getroot()
    except FileNotFoundError as err:
        raise VfsError(f"файл не найден: {path}") from err
    except ET.ParseError as err:
        raise VfsError(f"неверный формат XML: {err}") from err
    except OSError as err:
        raise VfsError(f"не удалось прочитать {path}: {err}") from err


def _attributes(element):
    """Возвращает общие атрибуты узла: owner, group, mtime."""
    attrs = {
        "owner": element.get("owner", DEFAULT_OWNER),
        "group": element.get("group", DEFAULT_OWNER),
    }
    stamp = element.get("mtime")
    if stamp is not None:
        try:
            attrs["mtime"] = datetime.fromisoformat(stamp)
        except ValueError as err:
            raise VfsError(f"неверная дата mtime: '{stamp}'") from err
    return attrs


def _check_name(name):
    """Проверяет имя узла."""
    if not name:
        raise VfsError("у элемента нет атрибута name")
    if "/" in name or name in (".", ".."):
        raise VfsError(f"недопустимое имя '{name}'")


def _file_data(element):
    """Возвращает содержимое файла в байтах."""
    if len(element):
        raise VfsError("внутри <file> не должно быть элементов")
    text = element.text or ""
    encoding = element.get("encoding", "text")
    if encoding == "text":
        return text.encode("utf-8")
    if encoding != "base64":
        raise VfsError(f"неизвестная кодировка '{encoding}'")
    try:
        return base64.b64decode("".join(text.split()), validate=True)
    except ValueError as err:
        raise VfsError(f"неверные данные base64: {err}") from err


def _make_node(element):
    """Создаёт узел VFS по элементу XML."""
    if element.tag not in ("dir", "file"):
        raise VfsError(f"неизвестный элемент <{element.tag}>")
    name = element.get("name", "")
    _check_name(name)
    attrs = _attributes(element)
    if element.tag == "dir":
        return Directory(name, **attrs)
    return File(name, data=_file_data(element), **attrs)


def build_vfs(root_element, source=""):
    """Строит Vfs из корневого элемента <vfs> (обход без рекурсии)."""
    if root_element.tag != "vfs":
        raise VfsError(f"корневой элемент должен быть <vfs>, а не "
                       f"<{root_element.tag}>")
    root = Directory("", **_attributes(root_element))
    stack = [(root, root_element)]
    while stack:
        directory, element = stack.pop()
        for child in element:
            node = _make_node(child)
            if node.name in directory.children:
                raise VfsError(f"дубликат имени '{node.name}'")
            directory.children[node.name] = node
            if node.is_dir:
                stack.append((node, child))
    return Vfs(root, source)


def load_vfs(path):
    """Загружает VFS из XML-файла path."""
    return build_vfs(_parse_xml(path), str(path))
