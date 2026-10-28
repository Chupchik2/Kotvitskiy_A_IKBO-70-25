"""Разбор коротких опций команд в стиле UNIX (-l, -la, --)."""

END_OF_OPTIONS = "--"


class OptionError(Exception):
    """Неизвестная опция команды."""


def parse_options(name, args, allowed):
    """Делит args на множество опций и список операндов.

    Допускаются объединённые опции (-la), разделитель ``--`` и одиночный
    ``-`` как операнд. Неизвестная опция вызывает OptionError.
    """
    flags = set()
    operands = []
    options_done = False
    for arg in args:
        if options_done or arg == "-" or not arg.startswith("-"):
            operands.append(arg)
        elif arg == END_OF_OPTIONS:
            options_done = True
        else:
            for char in arg[1:]:
                if char not in allowed:
                    raise OptionError(f"{name}: invalid option -- '{char}'")
                flags.add(char)
    return flags, operands
