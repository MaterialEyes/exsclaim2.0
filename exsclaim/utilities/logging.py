"""Logging and sending output to stdout code"""
import os
import sys
from logging import Formatter, Handler


__all__ = ["blockPrint", "enablePrint", "Printer", "PrinterFormatter", "ExsclaimFormatter"]


def blockPrint():
    """Disable printing output to stdout"""
    sys.stdout = open(os.devnull, "w")


# Restore
def enablePrint():
    """Enable printing output to stdout"""
    sys.stdout = sys.__stdout__


class ExsclaimFormatter(Formatter):
    def __init__(self):
        super().__init__(
            "%(levelname)5s %(asctime)s.%(msecs)03d - PID: %(process)s - Thread: %(thread)d - %(name)s - Function: %(funcName)s() in %(pathname)s on line %(lineno)3d - %(message)s",
            "%m/%d/%Y %H:%M:%S")


class PrinterFormatter(Formatter):
    def __init__(self):
        super().__init__("%(asctime)s\t%(pathname)s:%(lineno)3d: %(message)s", "%m/%d/%Y %H:%M:%S")
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
