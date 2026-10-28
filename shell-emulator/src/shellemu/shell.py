"""Ядро оболочки: выполнение одной строки и состояние сеанса."""
from datetime import datetime

from shellemu.commands import COMMANDS
from shellemu.parser import ParseError, parse_line
from shellemu.result import Result
from shellemu.vfs import Vfs
from shellemu.vfs_xml import load_vfs

ROOT = "/"


class Shell:
    """Состояние эмулятора и выполнение команд."""

    def __init__(self, user, host, vfs=None):
        """Создаёт оболочку для пользователя user на компьютере host."""
        self.user = user
        self.host = host
        self.vfs = vfs if vfs is not None else Vfs()
        self.cwd = ROOT
        self.oldpwd = ""
        self.clock = lambda: datetime.now().astimezone()

    def load_vfs(self, path):
        """Загружает VFS из XML, переходит в корень, возвращает сообщение.

        При ошибке бросает VfsError, текущая VFS остаётся без изменений.
        """
        self.vfs = load_vfs(path)
        self.cwd = ROOT
        self.oldpwd = ""
        dirs, files = self.vfs.count()
        return f"VFS загружена: {path} (каталогов: {dirs}, файлов: {files})\n"

    def prompt(self):
        """Возвращает приглашение вида user@host:/dir$ ."""
        return f"{self.user}@{self.host}:{self.cwd}$ "

    def run_line(self, line):
        """Выполняет строку и возвращает Result."""
        try:
            parsed = parse_line(line)
        except ParseError as err:
            return Result(err=f"{err}\n")
        if parsed is None:
            return Result()
        command = COMMANDS.get(parsed.name)
        if command is None:
            return Result(err=f"{parsed.name}: command not found\n")
        return command(self, parsed.args)
