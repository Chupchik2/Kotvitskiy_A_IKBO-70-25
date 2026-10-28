"""Тесты парсера, ядра оболочки и диалога."""
import unittest

from shellemu.commands import COMMANDS
from shellemu.dialog import run_and_emit
from shellemu.identity import window_title
from shellemu.parser import parse_line
from shellemu.shell import Shell


def make_shell():
    """Создаёт оболочку с фиксированными именами."""
    return Shell("alice", "box")


class ParserTest(unittest.TestCase):
    """Разбор строки на команду и аргументы."""

    def test_split(self):
        """Команда и аргументы делятся по пробелам."""
        parsed = parse_line("ls  -l   /home ")
        self.assertEqual(parsed.name, "ls")
        self.assertEqual(parsed.args, ["-l", "/home"])

    def test_empty(self):
        """Пустая строка даёт None."""
        self.assertIsNone(parse_line(""))
        self.assertIsNone(parse_line("   "))


class CommandsTest(unittest.TestCase):
    """Общее поведение оболочки и команда exit."""

    def test_commands_registered(self):
        """Все команды эмулятора зарегистрированы."""
        for name in ("ls", "cd", "date", "tac", "exit", "vfs-tree"):
            with self.subTest(name=name):
                self.assertIn(name, COMMANDS)

    def test_unknown_command(self):
        """Неизвестная команда — ошибка."""
        result = make_shell().run_line("foo bar")
        self.assertIn("foo: command not found", result.err)
        self.assertIsNone(result.exit_code)

    def test_empty_line(self):
        """Пустая строка ничего не делает."""
        result = make_shell().run_line("  ")
        self.assertEqual((result.out, result.err), ("", ""))

    def test_exit(self):
        """exit завершает работу; код и ошибки аргументов."""
        shell = make_shell()
        self.assertEqual(shell.run_line("exit").exit_code, 0)
        self.assertEqual(shell.run_line("exit 3").exit_code, 3)
        bad = shell.run_line("exit abc")
        self.assertIn("numeric argument required", bad.err)
        self.assertEqual(bad.exit_code, 2)
        many = shell.run_line("exit 1 2")
        self.assertIn("too many arguments", many.err)
        self.assertIsNone(many.exit_code)


class DialogTest(unittest.TestCase):
    """Имитация диалога."""

    def test_prompt_and_output(self):
        """Выводятся приглашение с командой и результат."""
        events = []
        run_and_emit(make_shell(), "vfs-tree",
                     lambda kind, text: events.append((kind, text)))
        self.assertEqual(events[0], ("echo", "alice@box:/$ vfs-tree\n"))
        self.assertEqual(events[1], ("out", "/\n"))

    def test_error_kind(self):
        """Ошибки идут отдельным видом сообщений."""
        events = []
        run_and_emit(make_shell(), "zzz",
                     lambda kind, text: events.append(kind))
        self.assertEqual(events, ["echo", "err"])


class TitleTest(unittest.TestCase):
    """Заголовок окна."""

    def test_title(self):
        """Заголовок строится по шаблону."""
        self.assertEqual(window_title("alice", "box"),
                         "Эмулятор - [alice@box]")


if __name__ == "__main__":
    unittest.main()
