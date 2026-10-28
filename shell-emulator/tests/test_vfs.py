"""Тесты VFS: пути, загрузка из XML, ошибки."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from shellemu.vfs import FsError, normalize
from shellemu.vfs_xml import VfsError, build_vfs, load_vfs

VFS_DIR = Path(__file__).resolve().parent.parent / "vfs"


def vfs_from(text):
    """Строит Vfs из XML-текста."""
    return build_vfs(ET.fromstring(text))


class NormalizeTest(unittest.TestCase):
    """Нормализация путей."""

    def test_cases(self):
        """Абсолютные, относительные пути, '.', '..' и '//'."""
        cases = [
            ("/a/b", "/", ["a", "b"]),
            ("b", "/a", ["a", "b"]),
            ("../c", "/a/b", ["a", "c"]),
            ("/a/./b//c/", "/", ["a", "b", "c"]),
            ("../../..", "/a", []),
            ("/", "/x", []),
            ("", "/x", ["x"]),
        ]
        for path, cwd, expected in cases:
            with self.subTest(path=path, cwd=cwd):
                self.assertEqual(normalize(path, cwd), expected)


class LoadTest(unittest.TestCase):
    """Загрузка готовых примеров VFS."""

    def test_minimal(self):
        """Минимальная VFS."""
        vfs = load_vfs(VFS_DIR / "minimal.xml")
        self.assertEqual(vfs.count(), (0, 1))

    def test_files(self):
        """Несколько файлов: текст, пустой, base64, владельцы."""
        vfs = load_vfs(VFS_DIR / "files.xml")
        hello = vfs.get("hello.txt", "/")
        self.assertEqual(hello.data, b"Hello, world!")
        self.assertEqual((hello.owner, hello.group), ("alice", "staff"))
        self.assertEqual(hello.mtime.year, 2026)
        self.assertEqual(vfs.get("data.bin", "/").data, bytes(range(16)))
        self.assertEqual(vfs.get("empty.txt", "/").size, 0)
        self.assertTrue(vfs.get("docs", "/").is_dir)

    def test_deep(self):
        """Не менее трёх уровней вложенности."""
        vfs = load_vfs(VFS_DIR / "deep.xml")
        path = "/home/alice/projects/emulator/tests/test_main.py"
        self.assertEqual(vfs.get(path, "/").data, b"assert True\n")
        self.assertEqual(vfs.count(), (9, 6))

    def test_tree(self):
        """Печать дерева."""
        vfs = load_vfs(VFS_DIR / "minimal.xml")
        self.assertEqual(vfs.tree_lines(), ["/", "`-- readme.txt"])
        deep = load_vfs(VFS_DIR / "deep.xml").tree_lines()
        self.assertEqual(deep[:6], [
            "/", "|-- etc/", "|   |-- hostname", "|   `-- passwd",
            "|-- home/", "|   |-- alice/",
        ])
        self.assertEqual(deep[-1], "        `-- syslog")


class LookupTest(unittest.TestCase):
    """Поиск узлов и ошибки."""

    def setUp(self):
        """Загружает вложенную VFS."""
        self.vfs = load_vfs(VFS_DIR / "deep.xml")

    def test_relative(self):
        """Относительные пути с '..'."""
        node = self.vfs.get("../bob", "/home/alice")
        self.assertEqual(node.name, "bob")

    def test_errors(self):
        """Нет файла; путь через файл."""
        with self.assertRaisesRegex(FsError, "No such file"):
            self.vfs.get("/nope", "/")
        with self.assertRaisesRegex(FsError, "Not a directory"):
            self.vfs.get("/etc/hostname/x", "/")


class ErrorsTest(unittest.TestCase):
    """Ошибки загрузки VFS."""

    def test_missing_file(self):
        """Файл не найден."""
        with self.assertRaisesRegex(VfsError, "файл не найден"):
            load_vfs(VFS_DIR / "absent.xml")

    def test_broken_files(self):
        """Каждый битый файл даёт VfsError."""
        for path in sorted((VFS_DIR / "broken").glob("*.xml")):
            with self.subTest(file=path.name):
                with self.assertRaises(VfsError):
                    load_vfs(path)

    def test_messages(self):
        """Понятные сообщения для разных ошибок."""
        cases = {
            "not_xml": "неверный формат XML",
            "wrong_root": "корневой элемент",
            "bad_base64": "base64",
            "unknown_tag": "неизвестный элемент",
            "duplicate": "дубликат",
            "no_name": "нет атрибута name",
        }
        for name, text in cases.items():
            with self.subTest(file=name):
                with self.assertRaisesRegex(VfsError, text):
                    load_vfs(VFS_DIR / "broken" / f"{name}.xml")

    def test_attribute_errors(self):
        """Неверные атрибуты узлов."""
        for text in (
            '<vfs><file name="a/b"/></vfs>',
            '<vfs><file name=".."/></vfs>',
            '<vfs><file name="a" mtime="вчера"/></vfs>',
            '<vfs><file name="a" encoding="rot13"/></vfs>',
            '<vfs><file name="a"><x/></file></vfs>',
        ):
            with self.subTest(text=text):
                with self.assertRaises(VfsError):
                    vfs_from(text)


if __name__ == "__main__":
    unittest.main()
