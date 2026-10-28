"""Команды навигации: ls и cd."""
from shellemu.options import OptionError, parse_options
from shellemu.result import Result
from shellemu.vfs import FsError, join_path, normalize

DIR_MODE = "drwxr-xr-x"
FILE_MODE = "-rw-r--r--"
LINKS = 1
OLD_DIR_DAYS = 180
HOME = "/"
MANY_OPERANDS = 2
MAX_CD_OPERANDS = 1


def _mtime_text(node, now):
    """Форматирует время изменения как ls -l."""
    stamp = node.mtime
    day = f"{stamp:%b} {stamp.day:2d}"
    age = now.replace(tzinfo=None) - stamp.replace(tzinfo=None)
    if abs(age.days) > OLD_DIR_DAYS:
        return f"{day}  {stamp.year}"
    return f"{day} {stamp:%H:%M}"


def _long_rows(entries, now):
    """Строит выровненные строки формата ls -l."""
    sizes = [str(node.size) for _, node in entries]
    owner_w = max(len(node.owner) for _, node in entries)
    group_w = max(len(node.group) for _, node in entries)
    size_w = max(len(size) for size in sizes)
    rows = []
    for (name, node), size in zip(entries, sizes):
        mode = DIR_MODE if node.is_dir else FILE_MODE
        rows.append(
            f"{mode} {LINKS} {node.owner:<{owner_w}} "
            f"{node.group:<{group_w}} {size:>{size_w}} "
            f"{_mtime_text(node, now)} {name}"
        )
    return rows


def _format(entries, long_format, now):
    """Форматирует список записей (имя, узел) в текст."""
    if not entries:
        return []
    if long_format:
        return _long_rows(entries, now)
    return ["  ".join(name for name, _ in entries)]


def _dir_entries(shell, path, node, show_all):
    """Возвращает отсортированные записи каталога."""
    items = [(name, child) for name, child in node.children.items()
             if show_all or not name.startswith(".")]
    items.sort(key=lambda item: item[0].casefold())
    if show_all:
        parent = shell.vfs.get(path + "/..", shell.cwd)
        items = [(".", node), ("..", parent)] + items
    return items


def _collect(shell, operands):
    """Разбирает операнды ls на файлы, каталоги и сообщения об ошибках."""
    files, dirs, errors = [], [], []
    for operand in operands:
        try:
            node = shell.vfs.get(operand, shell.cwd)
        except FsError as err:
            errors.append(f"ls: cannot access '{operand}': {err}")
            continue
        (dirs if node.is_dir else files).append((operand, node))
    return files, dirs, errors


def cmd_ls(shell, args):
    """ls [-l] [-a] [путь...]: список файлов и каталогов."""
    try:
        flags, operands = parse_options("ls", args, "la")
    except OptionError as err:
        return Result(err=f"{err}\n")
    operands = operands or ["."]
    files, dirs, errors = _collect(shell, operands)
    now = shell.clock()
    blocks = []
    if files:
        files.sort(key=lambda item: item[0].casefold())
        blocks.append("\n".join(_format(files, "l" in flags, now)))
    for path, node in sorted(dirs, key=lambda item: item[0].casefold()):
        entries = _dir_entries(shell, path, node, "a" in flags)
        body = "\n".join(_format(entries, "l" in flags, now))
        titled = len(operands) >= MANY_OPERANDS
        blocks.append(f"{path}:\n{body}" if titled else body)
    blocks = [block for block in blocks if block]
    out = "\n\n".join(blocks) + "\n" if blocks else ""
    err = "".join(f"{line}\n" for line in errors)
    return Result(out=out, err=err)


def _target(shell, operands):
    """Возвращает путь назначения для cd или бросает FsError."""
    if not operands:
        return HOME
    if operands[0] == "-":
        if not shell.oldpwd:
            raise FsError("OLDPWD not set")
        return shell.oldpwd
    return operands[0]


def _check_dir(shell, target):
    """Проверяет, что target существует и является каталогом."""
    if not shell.vfs.get(target, shell.cwd).is_dir:
        raise FsError("Not a directory")


def cmd_cd(shell, args):
    """cd [путь|-]: смена текущего каталога."""
    try:
        _, operands = parse_options("cd", args, "")
    except OptionError as err:
        return Result(err=f"{err}\n")
    if len(operands) > MAX_CD_OPERANDS:
        return Result(err="cd: too many arguments\n")
    try:
        target = _target(shell, operands)
    except FsError as err:
        return Result(err=f"cd: {err}\n")
    try:
        _check_dir(shell, target)
    except FsError as err:
        return Result(err=f"cd: {target}: {err}\n")
    shell.oldpwd = shell.cwd
    shell.cwd = join_path(normalize(target, shell.cwd))
    printed = bool(operands) and operands[0] == "-"
    return Result(out=shell.cwd + "\n" if printed else "")
