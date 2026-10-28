"""Тесты параметров командной строки и стартовых скриптов (этап 2)."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

from shellemu.cli import EXIT_USAGE, main
from shellemu.dialog import run_script
from shellemu.parser import ParseError, parse_line
from shellemu.shell import Shell

ROOT = Path(__file__).resolve().parent.parent


def run_main(argv, stdin_text=""):
    """Запускает main в служебном режиме; возвращает (код, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        with mock_stdin(stdin_text):
            code = main(argv)
    return code, out.getvalue(), err.getvalue()


@contextlib.contextmanager
def mock_stdin(text):
    """Подменяет sys.stdin строкой."""
    old = sys.stdin
    sys.stdin = io.StringIO(text)
    try:
        yield
    finally:
        sys.stdin = old


class ParserCommentsTest(unittest.TestCase):
    """Комментарии и кавычки."""

    def test_comments(self):
        """Комментарий отбрасывается."""
        self.assertIsNone(parse_line("# просто комментарий"))
        parsed = parse_line("ls -l # хвост")
        self.assertEqual(parsed.args, ["-l"])

    def test_quotes(self):
        """Кавычки группируют слова."""
        self.assertEqual(parse_line('cd "a b"').args, ["a b"])

    def test_unclosed_quote(self):
        """Незакрытая кавычка — ParseError."""
        with self.assertRaises(ParseError):
            parse_line('ls "abc')


class ScriptTest(unittest.TestCase):
    """Выполнение скрипта."""

    def test_dialog_shows_input_and_output(self):
        """В диалоге есть и ввод, и вывод; комментарии пропущены."""
        events = []
        code = run_script(
            Shell("u", "h"),
            ["# комментарий", "", "vfs-tree", "exit 4", "ls b"],
            lambda kind, text: events.append(text),
        )
        self.assertEqual(code, 4)
        joined = "".join(events)
        self.assertIn("u@h:/$ vfs-tree", joined)
        self.assertNotIn("ls b", joined)
        self.assertNotIn("комментарий", joined)


class HeadlessTest(unittest.TestCase):
    """Параметры командной строки в служебном режиме."""

    def test_debug_output(self):
        """Отладочный вывод содержит все параметры."""
        code, out, _ = run_main(
            ["--headless", "--vfs", "x.xml"], "exit\n")
        self.assertEqual(code, 0)
        self.assertIn("[debug] vfs: x.xml", out)
        self.assertIn("[debug] script: (не задан)", out)

    def test_script_param(self):
        """--script выполняет скрипт и возвращает его код."""
        path = ROOT / "scripts" / "emu" / "exit_code.emu"
        code, out, _ = run_main(["--headless", "--script", str(path)])
        self.assertEqual(code, 7)
        self.assertIn("$ cd /tmp", out)

    def test_script_not_found(self):
        """Нет скрипта — код 2 и сообщение."""
        code, _, err = run_main(["--headless", "--script", "/no/such.emu"])
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("скрипт не найден", err)

    def test_stdin_commands(self):
        """Без скрипта команды читаются со стандартного ввода."""
        _, out, _ = run_main(["--headless"], "ls q\n")
        self.assertIn("ls: cannot access 'q'", out)

    def test_script_file_utf8(self):
        """Скрипт с BOM и кириллицей читается."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.emu"
            path.write_text("\ufeffcd папка\n", encoding="utf-8")
            _, out, _ = run_main(["--headless", "--script", str(path)])
        self.assertIn("cd: папка: No such file or directory", out)


if __name__ == "__main__":
    unittest.main()
