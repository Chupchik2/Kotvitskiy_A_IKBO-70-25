"""Имитация диалога: показ введённой команды и её вывода."""


def _with_newline(text):
    """Добавляет перевод строки в конец текста, если его нет."""
    return text if text.endswith("\n") else text + "\n"


def run_and_emit(shell, line, emit):
    """Выполняет line и передаёт в emit(вид, текст) приглашение и вывод.

    Виды сообщений: "echo" (приглашение с командой), "out", "err".
    Возвращает Result команды.
    """
    emit("echo", shell.prompt() + line + "\n")
    result = shell.run_line(line)
    if result.out:
        emit("out", _with_newline(result.out))
    if result.err:
        emit("err", _with_newline(result.err))
    return result


def run_script(shell, lines, emit):
    """Выполняет строки скрипта, показывая и ввод, и вывод.

    Пустые строки и комментарии пропускаются. Если команда запросила
    выход, выполнение прекращается. Возвращает код выхода или None.
    """
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        result = run_and_emit(shell, line, emit)
        if result.exit_code is not None:
            return result.exit_code
    return None
