"""Запуск эмулятора из командной строки."""
import argparse
import sys

from shellemu.dialog import run_script
from shellemu.identity import current_user, hostname
from shellemu.script import ScriptError, read_script
from shellemu.shell import Shell
from shellemu.vfs_xml import VfsError

EXIT_OK = 0
EXIT_USAGE = 2
NOT_SET = "(не задан)"


def build_parser():
    """Создаёт разборщик аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="shellemu",
        description="Эмулятор командной оболочки UNIX (GUI).",
    )
    parser.add_argument("--vfs", help="путь к физическому расположению VFS")
    parser.add_argument("--script", help="путь к стартовому скрипту")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="служебный режим без окна: диалог выводится в консоль",
    )
    return parser


def debug_events(args):
    """Возвращает события отладочного вывода всех параметров запуска."""
    return [
        ("debug", f"[debug] vfs: {args.vfs or NOT_SET}\n"),
        ("debug", f"[debug] script: {args.script or NOT_SET}\n"),
        ("debug", f"[debug] headless: {args.headless}\n"),
    ]


def load_startup_vfs(shell, path):
    """Загружает VFS, заданную параметром --vfs; возвращает события."""
    if not path:
        return []
    try:
        return [("out", shell.load_vfs(path))]
    except VfsError as err:
        return [
            ("err", f"Ошибка загрузки VFS: {err}\n"),
            ("err", "Продолжаю работу с пустой VFS.\n"),
        ]


def console_emit(kind, text):
    """Выводит сообщение диалога в стандартный вывод."""
    sys.stdout.write(text)


def run_headless(shell, events, lines):
    """Выполняет скрипт или команды со стандартного ввода без окна."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for kind, text in events:
        console_emit(kind, text)
    if lines is None:
        lines = sys.stdin.read().splitlines()
    code = run_script(shell, lines, console_emit)
    return EXIT_OK if code is None else code


def main(argv=None):
    """Запускает эмулятор и возвращает код завершения."""
    args = build_parser().parse_args(argv)
    try:
        lines = read_script(args.script) if args.script else None
    except ScriptError as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        return EXIT_USAGE
    shell = Shell(current_user(), hostname())
    events = debug_events(args) + load_startup_vfs(shell, args.vfs)
    if args.headless:
        return run_headless(shell, events, lines)
    from shellemu.gui import run_gui
    run_gui(shell, events, lines)
    return EXIT_OK
