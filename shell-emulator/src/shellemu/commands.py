"""Команды эмулятора."""
from shellemu.cmd_fs import cmd_chown, cmd_touch, cmd_vfs_load
from shellemu.cmd_nav import cmd_cd, cmd_ls
from shellemu.cmd_text import cmd_date, cmd_tac
from shellemu.result import Result

EXIT_USAGE = 2
MAX_EXIT_ARGS = 1


def cmd_exit(shell, args):
    """Завершает работу: exit [код]."""
    if len(args) > MAX_EXIT_ARGS:
        return Result(err="exit: too many arguments\n")
    if not args:
        return Result(exit_code=0)
    try:
        return Result(exit_code=int(args[0]))
    except ValueError:
        return Result(
            err=f"exit: {args[0]}: numeric argument required\n",
            exit_code=EXIT_USAGE,
        )


def cmd_vfs_tree(shell, args):
    """Служебная команда: печатает дерево текущей VFS."""
    return Result(out="\n".join(shell.vfs.tree_lines()) + "\n")


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "date": cmd_date,
    "tac": cmd_tac,
    "chown": cmd_chown,
    "touch": cmd_touch,
    "vfs-load": cmd_vfs_load,
    "exit": cmd_exit,
    "vfs-tree": cmd_vfs_tree,
}
