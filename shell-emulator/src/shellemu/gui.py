"""Графический интерфейс эмулятора на tkinter."""
import tkinter as tk

from shellemu.dialog import run_and_emit, run_script
from shellemu.identity import window_title

FONT = ("Courier New", 11)
BACKGROUND = "#1e1e1e"
TEXT_COLOR = "#d4d4d4"
PROMPT_COLOR = "#6a9955"
ERROR_COLOR = "#f48771"
DEBUG_COLOR = "#808080"
SCRIPT_DELAY_MS = 200
WINDOW_SIZE = "820x520"
BANNER = (
    "Эмулятор оболочки. Команды: ls, cd, date, tac, chown, touch, "
    "vfs-load, vfs-tree, exit.\n"
)
TAGS = {
    "echo": PROMPT_COLOR,
    "out": TEXT_COLOR,
    "err": ERROR_COLOR,
    "debug": DEBUG_COLOR,
}


class TerminalWindow:
    """Окно эмулятора: вывод сверху, приглашение и поле ввода снизу."""

    def __init__(self, root, shell):
        """Строит интерфейс в окне root для оболочки shell."""
        self.root = root
        self.shell = shell
        self.history = []
        self.position = 0
        root.title(window_title(shell.user, shell.host))
        root.geometry(WINDOW_SIZE)
        self._build_widgets()
        self.write("out", BANNER)

    def _build_widgets(self):
        """Создаёт поле вывода, приглашение и строку ввода."""
        frame = tk.Frame(self.root, bg=BACKGROUND)
        scroll = tk.Scrollbar(frame)
        self.output = tk.Text(
            frame, bg=BACKGROUND, fg=TEXT_COLOR, font=FONT, wrap="word",
            state="disabled", yscrollcommand=scroll.set, borderwidth=0,
        )
        scroll.config(command=self.output.yview)
        for kind, color in TAGS.items():
            self.output.tag_configure(kind, foreground=color)
        scroll.pack(side="right", fill="y")
        self.output.pack(side="left", fill="both", expand=True)
        bottom = tk.Frame(self.root, bg=BACKGROUND)
        self.prompt_label = tk.Label(
            bottom, bg=BACKGROUND, fg=PROMPT_COLOR, font=FONT,
        )
        self.entry = tk.Entry(
            bottom, bg=BACKGROUND, fg=TEXT_COLOR, font=FONT,
            insertbackground=TEXT_COLOR, borderwidth=0,
        )
        self.prompt_label.pack(side="left")
        self.entry.pack(side="left", fill="x", expand=True)
        bottom.pack(side="bottom", fill="x")
        frame.pack(side="top", fill="both", expand=True)
        self._bind_keys()
        self._refresh_prompt()

    def _bind_keys(self):
        """Привязывает Enter и стрелки к обработчикам."""
        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<Up>", self.on_up)
        self.entry.bind("<Down>", self.on_down)
        self.entry.focus_set()

    def _refresh_prompt(self):
        """Обновляет текст приглашения (меняется при смене каталога)."""
        self.prompt_label.config(text=self.shell.prompt())

    def write(self, kind, text):
        """Дописывает text в поле вывода с оформлением kind."""
        self.output.config(state="normal")
        self.output.insert("end", text, kind)
        self.output.config(state="disabled")
        self.output.see("end")

    def run_line(self, line):
        """Выполняет строку, показывает диалог и при необходимости выходит."""
        result = run_and_emit(self.shell, line, self.write)
        self._finish(result.exit_code)

    def run_startup_script(self, lines):
        """Выполняет стартовый скрипт как диалог с пользователем."""
        self._finish(run_script(self.shell, lines, self.write))

    def _finish(self, exit_code):
        """Обновляет приглашение; при запросе выхода закрывает окно."""
        self._refresh_prompt()
        if exit_code is not None:
            self.root.after(0, self.root.destroy)

    def on_enter(self, event=None):
        """Обрабатывает нажатие Enter."""
        line = self.entry.get()
        self.entry.delete(0, "end")
        if line.strip():
            self.history.append(line)
        self.position = len(self.history)
        self.run_line(line)
        return "break"

    def _show_history(self):
        """Помещает в строку ввода запись истории по текущей позиции."""
        self.entry.delete(0, "end")
        if self.position < len(self.history):
            self.entry.insert(0, self.history[self.position])

    def on_up(self, event=None):
        """Стрелка вверх: предыдущая команда."""
        if self.position > 0:
            self.position -= 1
        self._show_history()
        return "break"

    def on_down(self, event=None):
        """Стрелка вниз: следующая команда."""
        if self.position < len(self.history):
            self.position += 1
        self._show_history()
        return "break"


def run_gui(shell, events, script_lines):
    """Запускает окно: стартовые сообщения, затем скрипт и главный цикл."""
    root = tk.Tk()
    window = TerminalWindow(root, shell)
    for kind, text in events:
        window.write(kind, text)
    if script_lines is not None:
        root.after(SCRIPT_DELAY_MS, window.run_startup_script, script_lines)
    root.mainloop()
