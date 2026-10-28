"""Виртуальная файловая система в памяти."""
from dataclasses import dataclass, field
from datetime import datetime

DEFAULT_OWNER = "root"
SEPARATOR = "/"
CURRENT = "."
PARENT = ".."


class FsError(Exception):
    """Ошибка операции с файловой системой (сообщение в стиле UNIX)."""


@dataclass
class Node:
    """Общие свойства файла и каталога."""

    name: str
    owner: str = DEFAULT_OWNER
    group: str = DEFAULT_OWNER
    mtime: datetime = field(default_factory=datetime.now)

    is_dir = False


@dataclass
class File(Node):
    """Файл с двоичным содержимым."""

    data: bytes = b""

    @property
    def size(self):
        """Размер файла в байтах."""
        return len(self.data)


@dataclass
class Directory(Node):
    """Каталог: словарь имя -> узел."""

    children: dict = field(default_factory=dict)

    is_dir = True

    @property
    def size(self):
        """Условный размер каталога (как у ls -l в UNIX)."""
        return 0


def normalize(path, cwd):
    """Возвращает список компонентов абсолютного пути.

    Обрабатывает абсолютные и относительные пути, '.', '..' и лишние '/'.
    Выше корня подняться нельзя.
    """
    parts = [] if path.startswith(SEPARATOR) else split_path(cwd)
    for item in path.split(SEPARATOR):
        if item in ("", CURRENT):
            continue
        if item == PARENT:
            if parts:
                parts.pop()
        else:
            parts.append(item)
    return parts


def split_path(path):
    """Делит абсолютный путь на компоненты."""
    return [item for item in path.split(SEPARATOR) if item]


def join_path(parts):
    """Собирает абсолютный путь из компонентов."""
    return SEPARATOR + SEPARATOR.join(parts)


class Vfs:
    """Дерево каталогов и файлов, целиком хранящееся в памяти."""

    def __init__(self, root=None, source=""):
        """Создаёт VFS; без корня — пустая файловая система."""
        self.root = root if root is not None else Directory("")
        self.source = source

    def lookup(self, parts):
        """Находит узел по компонентам абсолютного пути."""
        node = self.root
        for part in parts:
            if not node.is_dir:
                raise FsError("Not a directory")
            node = node.children.get(part)
            if node is None:
                raise FsError("No such file or directory")
        return node

    def get(self, path, cwd):
        """Находит узел по пути (абсолютному или относительно cwd)."""
        return self.lookup(normalize(path, cwd))

    def touch(self, path, cwd, owner, now, create=True):
        """Обновляет время изменения узла; при необходимости создаёт файл.

        Новый файл пустой и принадлежит owner. Если родительского каталога
        нет, бросает FsError. С create=False несуществующий файл не создаётся.
        """
        parts = normalize(path, cwd)
        if not parts:
            self.root.mtime = now
            return
        parent = self.lookup(parts[:-1])
        if not parent.is_dir:
            raise FsError("Not a directory")
        node = parent.children.get(parts[-1])
        if node is not None:
            node.mtime = now
        elif create:
            name = parts[-1]
            parent.children[name] = File(name, owner, owner, now)

    def count(self):
        """Возвращает пару (каталогов без корня, файлов)."""
        dirs = files = 0
        stack = [self.root]
        while stack:
            for child in stack.pop().children.values():
                if child.is_dir:
                    dirs += 1
                    stack.append(child)
                else:
                    files += 1
        return dirs, files

    @staticmethod
    def _entries(directory, prefix):
        """Возвращает потомков каталога как (узел, префикс, последний)."""
        names = sorted(directory.children)
        return [
            (directory.children[name], prefix, index == len(names) - 1)
            for index, name in enumerate(names)
        ]

    def tree_lines(self):
        """Возвращает строки дерева для печати (ASCII)."""
        lines = [SEPARATOR]
        stack = list(reversed(self._entries(self.root, "")))
        while stack:
            node, prefix, last = stack.pop()
            mark = "`-- " if last else "|-- "
            suffix = SEPARATOR if node.is_dir else ""
            lines.append(f"{prefix}{mark}{node.name}{suffix}")
            if node.is_dir:
                deeper = prefix + ("    " if last else "|   ")
                stack.extend(reversed(self._entries(node, deeper)))
        return lines
