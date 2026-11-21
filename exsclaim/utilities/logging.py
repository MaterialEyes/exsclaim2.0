"""Logging and sending output to stdout code"""
lazy import os
lazy import sys

lazy from enum import StrEnum
lazy from logging import Formatter, Handler

__all__ = ["blockPrint", "enablePrint", "Printer", "PrinterFormatter", "ExsclaimFormatter", "TerminalColor"]


def blockPrint():
    """Disable printing output to stdout"""
    sys.stdout = open(os.devnull, "w")


# Restore
def enablePrint():
    """Enable printing output to stdout"""
    sys.stdout = sys.__stdout__


class TerminalColor(StrEnum):
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m' # orange on some systems
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    LIGHT_GRAY = '\033[37m'
    DARK_GRAY = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m' # called to return to standard terminal text color


class ExsclaimFormatter(Formatter):
    def __init__(self):
        super().__init__(
            "%(asctime)s.%(msecs)03d %(levelname)5s - PID: %(process)s - Thread: %(thread)d - %(name)s - Function: %(funcName)s() in %(pathname)s on line %(lineno)3d - %(message)s",
            "%Y/%m/%d %H:%M:%S")


class PrinterFormatter(Formatter):
    def __init__(self, show_logger_name: bool = False):
        fmt = "%(asctime)s %(levelname)5s\t%(pathname)s:%(lineno)3d: %(message)s"
        if show_logger_name:
            fmt = f"{TerminalColor.MAGENTA}%(name)s{TerminalColor.RESET} " + fmt

        super().__init__(fmt, "%Y/%m/%d %H:%M:%S")
        # super().__init__("\r\x1b[K%(asctime)s: %(message)s", "%m/%d/%Y %H:%M:%S")


class Printer(Handler):
    def __init__(self):
        super().__init__()
        self.setFormatter(PrinterFormatter())

    def setFormatter(self, fmt):
        if not isinstance(fmt, PrinterFormatter):
            return  # raise ValueError("The Printer class only uses the PrinterFormatter as its formatting class.")
        super().setFormatter(fmt)


# class Printer:
#     """Print things to stdout on one line dynamically"""
#
#     def __init__(self, data):
#         sys.stdout.write(f"\r\x1b[K{data}")
#         sys.stdout.flush()
