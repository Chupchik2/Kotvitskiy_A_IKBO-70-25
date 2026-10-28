"""Тесты chown, touch и vfs-load (этап 5)."""
import unittest
from datetime import datetime, timezone
from pathlib import Path

from shellemu.cmd_fs import SpecError, parse_owner_spec
from shellemu.parser import parse_line
from shellemu.shell import Shell
from shellemu.vfs_xml import load_vfs

VFS_DIR = Path(__file__).resolve().parent.parent / "vfs"
NOW = datetime(2026, 10, 28, 12, 30, 45, tzinfo=timezone.utc)


def make_shell(name="deep.xml"):
    """Создаёт оболочку с VFS и неподвижными часами."""
    shell = Shell("student", "h", load_vfs(VFS_DIR / name))
    shell.clock = lambda: NOW
    return shell


def node_of(shell, path):
    """Возвращает узел VFS по пути."""
    return shell.vfs.get(path, "/")


class OwnerSpecTest(unittest.TestCase):
    """Разбор спецификации владельца."""

    def test_valid(self):
        """Допустимые формы."""
        self.assertEqual(parse_owner_spec("bob"), ("bob", None))
        self.assertEqual(parse_owner_spec("bob:staff"), ("bob", "staff"))
        self.assertEqual(parse_owner_spec(":staff"), (None, "staff"))
        self.assertEqual(parse_owner_spec("bob:"), ("bob", None))
        self.assertEqual(parse_owner_spec("1000:1000"), ("1000", "1000"))
        self.assertEqual(parse_owner_spec(":"), (None, None))

    def test_invalid(self):
        """Недопустимые формы."""
        for spec in ("", "b!d", "bob:g!", "-x", "a b"):
            with self.subTest(spec=spec):
                with self.assertRaises(SpecError):
                    parse_owner_spec(spec)


class ChownTest(unittest.TestCase):
    """Команда chown."""

    def test_owner(self):
        """Смена владельца файла."""
        shell = make_shell()
        result = shell.run_line("chown bob /etc/hostname")
        self.assertEqual((result.out, result.err), ("", ""))
        self.assertEqual(node_of(shell, "/etc/hostname").owner, "bob")
        self.assertEqual(node_of(shell, "/etc/hostname").group, "root")

    def test_owner_and_group(self):
        """Владелец и группа; только группа."""
        shell = make_shell()
        shell.run_line("chown bob:staff /etc/hostname")
        node = node_of(shell, "/etc/hostname")
        self.assertEqual((node.owner, node.group), ("bob", "staff"))
        shell.run_line("chown :wheel /etc/hostname")
        self.assertEqual((node.owner, node.group), ("bob", "wheel"))

    def test_directory_not_recursive(self):
        """Без -R потомки не меняются."""
        shell = make_shell()
        shell.run_line("chown bob /home/alice")
        self.assertEqual(node_of(shell, "/home/alice").owner, "bob")
        self.assertEqual(node_of(shell, "/home/alice/todo.txt").owner,
                         "alice")

    def test_recursive(self):
        """-R меняет всё поддерево."""
        shell = make_shell()
        shell.run_line("chown -R bob:team /home/alice")
        for path in ("/home/alice", "/home/alice/todo.txt",
                     "/home/alice/projects/emulator/tests/test_main.py"):
            with self.subTest(path=path):
                node = node_of(shell, path)
                self.assertEqual((node.owner, node.group), ("bob", "team"))
        self.assertEqual(node_of(shell, "/home/bob").owner, "bob")
        self.assertEqual(node_of(shell, "/etc").owner, "root")

    def test_verbose(self):
        """-v сообщает об изменении и о том, что владелец прежний."""
        shell = make_shell()
        out = shell.run_line("chown -v bob /etc/hostname").out
        self.assertEqual(
            out, "changed ownership of '/etc/hostname' from root to bob\n")
        out = shell.run_line("chown -v bob /etc/hostname").out
        self.assertEqual(
            out, "ownership of '/etc/hostname' retained as bob\n")
        out = shell.run_line("chown -Rv a:b /home/bob").out
        self.assertIn("from bob:bob to a:b", out)

    def test_recursive_verbose_order(self):
        """С -R -v обход в глубину в алфавитном порядке."""
        shell = make_shell()
        lines = shell.run_line("chown -Rv x /home/alice").out.splitlines()
        paths = [line.split("'")[1] for line in lines]
        self.assertEqual(paths[0], "/home/alice")
        self.assertEqual(paths[-1], "/home/alice/todo.txt")
        self.assertEqual(len(paths), 7)

    def test_relative_path(self):
        """Относительный путь."""
        shell = make_shell()
        shell.run_line("cd /etc")
        shell.run_line("chown bob hostname")
        self.assertEqual(node_of(shell, "/etc/hostname").owner, "bob")

    def test_errors(self):
        """Ошибки: операнды, спецификация, путь, опция."""
        shell = make_shell()
        self.assertIn("missing operand\n", shell.run_line("chown").err)
        self.assertIn("missing operand after 'bob'",
                      shell.run_line("chown bob").err)
        self.assertIn("invalid user: 'b!d'",
                      shell.run_line("chown b!d /etc").err)
        self.assertIn("invalid group: 'g!'",
                      shell.run_line("chown bob:g! /etc").err)
        self.assertIn("chown: cannot access '/nope'",
                      shell.run_line("chown bob /nope").err)
        self.assertIn("invalid option", shell.run_line("chown -x a b").err)

    def test_partial_failure(self):
        """Ошибка в одном пути не мешает остальным."""
        shell = make_shell()
        result = shell.run_line("chown bob /nope /etc/hostname")
        self.assertIn("/nope", result.err)
        self.assertEqual(node_of(shell, "/etc/hostname").owner, "bob")


class TouchTest(unittest.TestCase):
    """Команда touch."""

    def test_create(self):
        """Создаёт пустой файл владельца-пользователя."""
        shell = make_shell()
        result = shell.run_line("touch /etc/new.txt")
        self.assertEqual((result.out, result.err), ("", ""))
        node = node_of(shell, "/etc/new.txt")
        self.assertEqual((node.size, node.owner), (0, "student"))
        self.assertIn("new.txt", shell.run_line("ls /etc").out)

    def test_relative_and_several(self):
        """Несколько файлов, относительные пути."""
        shell = make_shell()
        shell.run_line("cd /home/bob")
        shell.run_line("touch a b ../c")
        self.assertEqual(shell.run_line("ls").out, "a  b\n")
        self.assertTrue(node_of(shell, "/home/c"))

    def test_update_time_keeps_data(self):
        """Существующий файл: время обновляется, данные целы."""
        shell = make_shell()
        shell.run_line("touch /etc/hostname")
        node = node_of(shell, "/etc/hostname")
        self.assertEqual(node.mtime, NOW.replace(tzinfo=None))
        self.assertEqual(node.data, b"emu-host")
        shell.run_line("touch /etc")
        self.assertEqual(node_of(shell, "/etc").mtime,
                         NOW.replace(tzinfo=None))

    def test_no_create(self):
        """-c не создаёт файл."""
        shell = make_shell()
        result = shell.run_line("touch -c /etc/ghost")
        self.assertEqual(result.err, "")
        self.assertNotIn("ghost", shell.run_line("ls /etc").out)

    def test_errors(self):
        """Нет каталога, родитель — файл, нет операндов, плохая опция."""
        shell = make_shell()
        self.assertIn("touch: cannot touch '/no/dir/f': No such file",
                      shell.run_line("touch /no/dir/f").err)
        self.assertIn("Not a directory",
                      shell.run_line("touch /etc/hostname/f").err)
        self.assertIn("missing file operand", shell.run_line("touch").err)
        self.assertIn("invalid option", shell.run_line("touch -q a").err)

    def test_then_tac_and_chown(self):
        """Созданный файл работает с другими командами."""
        shell = make_shell()
        shell.run_line("touch /f")
        self.assertEqual(shell.run_line("tac /f").out, "")
        shell.run_line("chown bob /f")
        self.assertIn(" bob ", shell.run_line("ls -l /f").out)

    def test_disk_file_untouched(self):
        """XML-файл на диске не изменяется операциями в памяти."""
        path = VFS_DIR / "deep.xml"
        before = path.read_bytes()
        shell = make_shell()
        shell.run_line("touch /new")
        shell.run_line("chown -R x /home")
        self.assertEqual(path.read_bytes(), before)


class VfsLoadTest(unittest.TestCase):
    """Команда vfs-load."""

    def test_load_replaces_vfs(self):
        """Новая VFS заменяет старую, каталог сбрасывается в корень."""
        shell = make_shell()
        shell.run_line("cd /home/alice")
        result = shell.run_line(f"vfs-load {VFS_DIR / 'files.xml'}")
        self.assertIn("VFS загружена", result.out)
        self.assertEqual(shell.cwd, "/")
        self.assertIn("hello.txt", shell.run_line("ls").out)
        self.assertNotIn("etc", shell.run_line("ls").out)

    def test_error_keeps_old_vfs(self):
        """Ошибка загрузки не ломает текущую VFS."""
        shell = make_shell()
        shell.run_line("cd /etc")
        for name in ("absent.xml", "broken/not_xml.xml"):
            result = shell.run_line(f"vfs-load {VFS_DIR / name}")
            self.assertIn("vfs-load:", result.err)
        self.assertEqual(shell.cwd, "/etc")
        self.assertIn("hostname", shell.run_line("ls").out)

    def test_argument_errors(self):
        """Нет аргумента, лишний аргумент."""
        shell = make_shell()
        self.assertIn("missing file operand",
                      shell.run_line("vfs-load").err)
        self.assertIn("too many arguments",
                      shell.run_line("vfs-load a b").err)

    def test_changes_are_lost_after_reload(self):
        """Изменения в памяти пропадают при повторной загрузке."""
        shell = make_shell("minimal.xml")
        shell.run_line("touch extra")
        self.assertIn("extra", shell.run_line("ls").out)
        shell.run_line(f"vfs-load {VFS_DIR / 'minimal.xml'}")
        self.assertNotIn("extra", shell.run_line("ls").out)

    def test_windows_path(self):
        """Обратные слэши в пути не пропадают при разборе."""
        parsed = parse_line(r"vfs-load vfs\deep.xml")
        self.assertEqual(parsed.args, [r"vfs\deep.xml"])


if __name__ == "__main__":
    unittest.main()
