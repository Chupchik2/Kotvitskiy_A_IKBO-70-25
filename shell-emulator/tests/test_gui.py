"""Дымовой тест GUI с подменой tkinter (окно не создаётся)."""
import importlib
import sys
import unittest
from unittest import mock

from shellemu.shell import Shell


class GuiSmokeTest(unittest.TestCase):
    """Проверяет логику окна без настоящего tkinter."""

    def setUp(self):
        """Подменяет модуль tkinter и создаёт окно."""
        self.patcher = mock.patch.dict(sys.modules, {"tkinter": mock.Mock()})
        self.patcher.start()
        sys.modules.pop("shellemu.gui", None)
        self.gui = importlib.import_module("shellemu.gui")
        self.root = mock.Mock()
        self.window = self.gui.TerminalWindow(self.root, Shell("a", "b"))

    def tearDown(self):
        """Возвращает настоящие модули."""
        self.patcher.stop()
        sys.modules.pop("shellemu.gui", None)

    def test_title(self):
        """Заголовок окна содержит пользователя и компьютер."""
        self.root.title.assert_called_with("Эмулятор - [a@b]")

    def test_enter_runs_command(self):
        """Enter выполняет команду и пишет вывод в окно."""
        self.window.entry.get.return_value = "ls x"
        self.window.on_enter()
        written = [c.args[1] for c in self.window.output.insert.call_args_list]
        self.assertIn("a@b:/$ ls x\n", written)
        self.assertEqual(self.window.history, ["ls x"])

    def test_exit_closes_window(self):
        """exit планирует закрытие окна."""
        self.window.run_line("exit")
        self.root.after.assert_called_once()

    def test_startup_script(self):
        """Стартовый скрипт показывается в окне как диалог."""
        self.window.run_startup_script(["# c", "cd /x", "exit"])
        written = [c.args[1] for c in self.window.output.insert.call_args_list]
        self.assertIn("a@b:/$ cd /x\n", written)
        self.root.after.assert_called_once()

    def test_history_keys(self):
        """Стрелки листают историю."""
        self.window.history = ["one", "two"]
        self.window.position = 2
        self.window.on_up()
        self.window.entry.insert.assert_called_with(0, "two")
        self.window.on_up()
        self.window.entry.insert.assert_called_with(0, "one")
        self.window.on_down()
        self.window.entry.insert.assert_called_with(0, "two")


if __name__ == "__main__":
    unittest.main()
