"""Команды, изменяющие состояние VFS в памяти: chown, touch, vfs-load."""
import re

from shellemu.options import OptionError, parse_options
from shellemu.result import Result
from shellemu.vfs import FsError, SEPARATOR
from shellemu.vfs_xml import VfsError

NAME_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*|[0-9]+)$")
OWNER_SEPARATOR = ":"
MIN_CHOWN_OPERANDS = 2
SINGLE = 1


class SpecError(Exception):
    """Неверная спецификация владельца."""


def parse_owner_spec(spec):
    """Разбирает ВЛАДЕЛЕЦ[:ГРУППА] в пару (владелец, группа).

    Отсутствующая часть возвращается как None (не меняется).
    """
    if not spec:
        raise SpecError("invalid user: ''")
    owner, _, group = spec.partition(OWNER_SEPARATOR)
    if owner and not NAME_RE.match(owner):
        raise SpecError(f"invalid user: '{owner}'")
    if group and not NAME_RE.match(group):
        raise SpecError(f"invalid group: '{group}'")
    return owner or None, group or None


def _owner_text(node, with_group):
    """Возвращает 'владелец' или 'владелец:группа' для сообщений."""
    if with_group:
        return f"{node.owner}:{node.group}"
    return node.owner


def _change_one(node, path, owner, group, verbose):
    """Меняет владельца узла; возвращает строку для -v или пустую."""
    with_group = group is not None
    before = _owner_text(node, with_group)
    node.owner = owner or node.owner
    node.group = group or node.group
    after = _owner_text(node, with_group)
    if not verbose:
        return ""
    if before == after:
        return f"ownership of '{path}' retained as {after}\n"
    return f"changed ownership of '{path}' from {before} to {after}\n"


def _child_path(path, name):
    """Склеивает путь каталога и имя потомка."""
    return path.rstrip(SEPARATOR) + SEPARATOR + name


def _apply_chown(node, path, change, flags):
    """Применяет chown к узлу и (с -R) ко всем потомкам."""
    owner, group = change
    lines = []
    stack = [(path, node)]
    while stack:
        current_path, current = stack.pop()
        lines.append(_change_one(current, current_path, owner, group,
                                 "v" in flags))
        if "R" in flags and current.is_dir:
            for name in sorted(current.children, reverse=True):
                stack.append((_child_path(current_path, name),
                              current.children[name]))
    return "".join(lines)


def cmd_chown(shell, args):
    """chown [-R] [-v] ВЛАДЕЛЕЦ[:ГРУППА] ФАЙЛ...: смена владельца."""
    try:
        flags, operands = parse_options("chown", args, "Rv")
    except OptionError as err:
        return Result(err=f"{err}\n")
    if not operands:
        return Result(err="chown: missing operand\n")
    if len(operands) < MIN_CHOWN_OPERANDS:
        return Result(err=f"chown: missing operand after '{operands[0]}'\n")
    try:
        change = parse_owner_spec(operands[0])
    except SpecError as err:
        return Result(err=f"chown: {err}\n")
    out, err = [], []
    for path in operands[1:]:
        try:
            node = shell.vfs.get(path, shell.cwd)
        except FsError as problem:
            err.append(f"chown: cannot access '{path}': {problem}\n")
            continue
        out.append(_apply_chown(node, path, change, flags))
    return Result(out="".join(out), err="".join(err))


def cmd_touch(shell, args):
    """touch [-c] ФАЙЛ...: создаёт пустой файл или обновляет время."""
    try:
        flags, operands = parse_options("touch", args, "c")
    except OptionError as err:
        return Result(err=f"{err}\n")
    if not operands:
        return Result(err="touch: missing file operand\n")
    now = shell.clock().replace(tzinfo=None)
    err = []
    for path in operands:
        try:
            shell.vfs.touch(path, shell.cwd, shell.user, now, "c" not in flags)
        except FsError as problem:
            err.append(f"touch: cannot touch '{path}': {problem}\n")
    return Result(err="".join(err))


def cmd_vfs_load(shell, args):
    """vfs-load ПУТЬ: загружает новую VFS с диска вместо текущей."""
    if not args:
        return Result(err="vfs-load: missing file operand\n")
    if len(args) > SINGLE:
        return Result(err="vfs-load: too many arguments\n")
    try:
        return Result(out=shell.load_vfs(args[0]))
    except VfsError as err:
        return Result(err=f"vfs-load: {err}\n")
