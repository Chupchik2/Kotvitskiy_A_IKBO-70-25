"""Команды работы с датой и текстом: date и tac."""
from datetime import timezone

from shellemu.options import OptionError, parse_options
from shellemu.result import Result
from shellemu.vfs import FsError

RFC_2822 = "%a, %d %b %Y %H:%M:%S %z"
ISO_DATE = "%Y-%m-%d"
MAX_DATE_OPERANDS = 1
FORMAT_PREFIX = "+"
NEWLINE = b"\n"


def _default_format(stamp):
    """Формат вывода date по умолчанию (как в GNU date)."""
    zone = stamp.tzname() or ""
    return (f"{stamp:%a %b} {stamp.day:2d} {stamp:%H:%M:%S} "
            f"{zone} {stamp:%Y}")


def _date_text(stamp, flags, template):
    """Возвращает текст даты по выбранному режиму."""
    if template is not None:
        return stamp.strftime(template)
    if "R" in flags:
        return stamp.strftime(RFC_2822)
    if "I" in flags:
        return stamp.strftime(ISO_DATE)
    return _default_format(stamp)


def _date_template(operands):
    """Возвращает шаблон из операнда +ФОРМАТ или None; проверяет ошибки."""
    if not operands:
        return None
    if len(operands) > MAX_DATE_OPERANDS:
        raise OptionError(f"date: extra operand '{operands[1]}'")
    if not operands[0].startswith(FORMAT_PREFIX):
        raise OptionError(f"date: invalid date '{operands[0]}'")
    return operands[0][len(FORMAT_PREFIX):]


def cmd_date(shell, args):
    """date [-u] [-R] [-I] [+ФОРМАТ]: текущие дата и время."""
    try:
        flags, operands = parse_options("date", args, "uRI")
        template = _date_template(operands)
        stamp = shell.clock()
        if "u" in flags:
            stamp = stamp.astimezone(timezone.utc)
        return Result(out=_date_text(stamp, flags, template) + "\n")
    except OptionError as err:
        return Result(err=f"{err}\n")
    except ValueError:
        return Result(err="date: invalid format string\n")


def reverse_records(data):
    """Переставляет записи (строки) bytes в обратном порядке, как GNU tac.

    Если последняя строка не заканчивается переводом строки, она
    склеивается со следующей в выводе (так ведёт себя GNU tac).
    """
    parts = data.split(NEWLINE)
    tail = parts.pop()
    records = [part + NEWLINE for part in parts]
    if tail:
        records.append(tail)
    return b"".join(reversed(records))


def _tac_one(shell, name):
    """Возвращает текст tac для одного файла или бросает FsError."""
    node = shell.vfs.get(name, shell.cwd)
    if node.is_dir:
        raise FsError("Is a directory")
    return reverse_records(node.data).decode("utf-8", errors="replace")


def cmd_tac(shell, args):
    """tac ФАЙЛ...: выводит строки файлов в обратном порядке."""
    try:
        _, operands = parse_options("tac", args, "")
    except OptionError as err:
        return Result(err=f"{err}\n")
    if not operands:
        return Result(err="tac: missing file operand\n")
    out, err = [], []
    for name in operands:
        try:
            out.append(_tac_one(shell, name))
        except FsError as problem:
            if str(problem) == "Is a directory":
                err.append(f"tac: {name}: read error: {problem}\n")
            else:
                err.append(
                    f"tac: failed to open '{name}' for reading: {problem}\n")
    return Result(out="".join(out), err="".join(err))
