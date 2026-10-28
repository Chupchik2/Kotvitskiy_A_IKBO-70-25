"""Тесты команд ls, cd, date, tac на примерах VFS (этап 4)."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shellemu.cmd_text import reverse_records
from shellemu.options import OptionError, parse_options
from shellemu.shell import Shell
from shellemu.vfs import Directory, Vfs
from shellemu.vfs_xml import load_vfs

VFS_DIR = Path(__file__).resolve().parent.parent / "vfs"
NOW = datetime(2026, 10, 28, 12, 30, 45, tzinfo=timezone.utc)


def make_shell(name="deep.xml"):
    """Создаёт оболочку с загруженной VFS и неподвижными часами."""
    shell = Shell("u", "h", load_vfs(VFS_DIR / name))
    shell.clock = lambda: NOW
    return shell


class OptionsTest(unittest.TestCase):
    """Разбор опций."""

    def test_parse(self):
        """Объединённые опции, операнды, '--' и '-'."""
        flags, operands = parse_options("x", ["-la", "a", "-", "--", "-b"],
                                        "la")
        self.assertEqual(flags, {"l", "a"})
        self.assertEqual(operands, ["a", "-", "-b"])

    def test_unknown(self):
        """Неизвестная опция."""
        with self.assertRaises(OptionError):
            parse_options("x", ["-z"], "l")


class CdTest(unittest.TestCase):
    """Команда cd."""

    def test_navigation(self):
        """Абсолютные и относительные переходы, '..', '.', без аргумента."""
        shell = make_shell()
        shell.run_line("cd /home/alice")
        self.assertEqual(shell.cwd, "/home/alice")
        shell.run_line("cd projects/emulator")
        self.assertEqual(shell.cwd, "/home/alice/projects/emulator")
        shell.run_line("cd ../..")
        self.assertEqual(shell.cwd, "/home/alice")
        shell.run_line("cd .")
        self.assertEqual(shell.cwd, "/home/alice")
        shell.run_line("cd")
        self.assertEqual(shell.cwd, "/")

    def test_prompt_changes(self):
        """Приглашение показывает текущий каталог."""
        shell = make_shell()
        shell.run_line("cd /etc")
        self.assertEqual(shell.prompt(), "u@h:/etc$ ")

    def test_oldpwd(self):
        """cd - возвращает в предыдущий каталог и печатает его."""
        shell = make_shell()
        self.assertIn("OLDPWD not set", shell.run_line("cd -").err)
        shell.run_line("cd /etc")
        shell.run_line("cd /var")
        result = shell.run_line("cd -")
        self.assertEqual((shell.cwd, result.out), ("/etc", "/etc\n"))

    def test_errors(self):
        """Нет каталога, это файл, много аргументов, плохая опция."""
        shell = make_shell()
        self.assertIn("cd: nope: No such file or directory",
                      shell.run_line("cd nope").err)
        self.assertIn("cd: /etc/hostname: Not a directory",
                      shell.run_line("cd /etc/hostname").err)
        self.assertIn("too many arguments", shell.run_line("cd a b").err)
        self.assertIn("invalid option", shell.run_line("cd -x").err)
        self.assertEqual(shell.cwd, "/")

    def test_quoted_name(self):
        """Имя с пробелом в кавычках."""
        root = Directory("")
        root.children["my dir"] = Directory("my dir")
        shell = Shell("u", "h", Vfs(root))
        shell.run_line('cd "my dir"')
        self.assertEqual(shell.cwd, "/my dir")


class LsTest(unittest.TestCase):
    """Команда ls."""

    def test_plain(self):
        """Простой список, сортировка без учёта регистра."""
        out = make_shell().run_line("ls").out
        self.assertEqual(out, "etc  home  var\n")

    def test_path_and_relative(self):
        """Путь абсолютный и относительный."""
        shell = make_shell()
        self.assertEqual(shell.run_line("ls /home/alice").out,
                         "projects  todo.txt\n")
        shell.run_line("cd /home")
        self.assertEqual(shell.run_line("ls alice/projects").out,
                         "emulator\n")
        self.assertEqual(shell.run_line("ls ..").out, "etc  home  var\n")

    def test_hidden_and_all(self):
        """Скрытые файлы показываются только с -a, плюс . и .."""
        shell = make_shell("files.xml")
        self.assertNotIn(".hidden", shell.run_line("ls").out)
        out = shell.run_line("ls -a").out
        self.assertTrue(out.startswith(".  ..  .hidden"))

    def test_long(self):
        """Длинный формат: права, владелец, размер, дата, имя."""
        out = make_shell("files.xml").run_line("ls -l").out.splitlines()
        hello = [line for line in out if line.endswith("hello.txt")][0]
        self.assertTrue(hello.startswith("-rw-r--r-- 1 alice staff"))
        self.assertIn("13 Sep  1 10:30 hello.txt", hello)
        docs = [line for line in out if line.endswith("docs")][0]
        self.assertTrue(docs.startswith("drwxr-xr-x"))
        self.assertTrue(any("data.bin" in line and " 16 " in line
                            for line in out))

    def test_long_old_date_shows_year(self):
        """Старые файлы показываются с годом вместо времени."""
        shell = make_shell("files.xml")
        shell.clock = lambda: datetime(2028, 1, 1, tzinfo=timezone.utc)
        self.assertIn("Sep  1  2026 hello.txt", shell.run_line("ls -l").out)

    def test_file_operand_and_multiple(self):
        """Файл как операнд; несколько операндов с заголовками."""
        shell = make_shell()
        self.assertEqual(shell.run_line("ls /etc/hostname").out,
                         "/etc/hostname\n")
        out = shell.run_line("ls /etc /var").out
        self.assertEqual(out, "/etc:\nhostname  passwd\n\n/var:\nlog\n")

    def test_errors(self):
        """Нет файла (остальное выводится), неизвестная опция."""
        shell = make_shell()
        result = shell.run_line("ls /nope /etc")
        self.assertIn("ls: cannot access '/nope': No such file", result.err)
        self.assertIn("/etc:", result.out)
        self.assertIn("invalid option -- 'z'", shell.run_line("ls -z").err)
        self.assertIn("Not a directory",
                      shell.run_line("ls /etc/hostname/x").err)

    def test_empty_dir(self):
        """Пустой каталог ничего не выводит."""
        self.assertEqual(make_shell().run_line("ls /home/bob").out, "")


class TacTest(unittest.TestCase):
    """Команда tac."""

    def test_reverse_records(self):
        """Правила GNU tac для строк без перевода строки в конце."""
        self.assertEqual(reverse_records(b"a\nb\nc\n"), b"c\nb\na\n")
        self.assertEqual(reverse_records(b"a\nb"), b"ba\n")
        self.assertEqual(reverse_records(b""), b"")
        self.assertEqual(reverse_records(b"\n\nx\n"), b"x\n\n\n")

    def test_file(self):
        """Файл выводится построчно в обратном порядке."""
        shell = make_shell()
        out = shell.run_line("tac /var/log/syslog").out
        self.assertEqual(out, "третья запись\nвторая запись\n"
                              "первая запись\n")

    def test_several_files(self):
        """Несколько файлов выводятся подряд."""
        shell = make_shell()
        out = shell.run_line("tac /etc/hostname /var/log/syslog").out
        self.assertTrue(out.startswith("emu-host"))
        self.assertIn("первая запись", out)

    def test_relative_path(self):
        """Относительный путь."""
        shell = make_shell()
        shell.run_line("cd /home/alice")
        self.assertIn("позвонить маме", shell.run_line("tac todo.txt").out)

    def test_errors(self):
        """Нет файла, каталог, нет операндов, плохая опция."""
        shell = make_shell()
        self.assertIn("tac: failed to open 'x' for reading",
                      shell.run_line("tac x").err)
        self.assertIn("tac: /etc: read error: Is a directory",
                      shell.run_line("tac /etc").err)
        self.assertIn("missing file operand", shell.run_line("tac").err)
        self.assertIn("invalid option", shell.run_line("tac -q a").err)

    def test_partial_failure(self):
        """Ошибка в одном файле не мешает выводу других."""
        result = make_shell().run_line("tac nope /etc/hostname")
        self.assertIn("emu-host", result.out)
        self.assertIn("nope", result.err)

    def test_binary(self):
        """Двоичный файл не роняет команду."""
        result = make_shell("files.xml").run_line("tac data.bin")
        self.assertEqual(result.err, "")
        self.assertTrue(result.out)


class DateTest(unittest.TestCase):
    """Команда date."""

    def test_default(self):
        """Формат по умолчанию как в GNU date."""
        out = make_shell().run_line("date").out
        self.assertEqual(out, "Wed Oct 28 12:30:45 UTC 2026\n")

    def test_utc_and_formats(self):
        """-u, -R, -I и +ФОРМАТ."""
        shell = make_shell()
        zone = timezone(timedelta(hours=3))
        local = datetime(2026, 10, 28, 15, 30, 45, tzinfo=zone)
        shell.clock = lambda: local
        self.assertIn("UTC 2026", shell.run_line("date -u").out)
        self.assertIn("12:30:45", shell.run_line("date -u").out)
        self.assertEqual(shell.run_line("date -R").out,
                         "Wed, 28 Oct 2026 15:30:45 +0300\n")
        self.assertEqual(shell.run_line("date -I").out, "2026-10-28\n")
        self.assertEqual(shell.run_line("date +%Y/%m/%d").out,
                         "2026/10/28\n")
        self.assertEqual(shell.run_line('date "+%H h %M min"').out,
                         "15 h 30 min\n")

    def test_errors(self):
        """Неверная дата, лишний операнд, неверная опция."""
        shell = make_shell()
        self.assertIn("invalid date 'abc'", shell.run_line("date abc").err)
        self.assertIn("extra operand", shell.run_line("date +%Y +%m").err)
        self.assertIn("invalid option", shell.run_line("date -z").err)


if __name__ == "__main__":
    unittest.main()
