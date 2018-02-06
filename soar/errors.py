# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/errors.py
""" Soar error classes. """
# TODO: In 2.0, move these into __init__
import sys


def printerr(*args, **kwargs):
    """ A wrapper around `print` to print to `sys.stderr`. """
    print(*args, file=sys.stderr, **kwargs)


class SoarError(Exception):
    """ An umbrella class for Soar exceptions.

    This is raised by the client if it encounters an error it cannot handle, such as an exception that occurs in
    headless mode.
    """
    pass


class LoggingError(SoarError):
    """ Raised when an error occurs writing to a log file. Typically, these are ignored and merely printed. """
    pass


class SoarIOError(SoarError):
    """ Raised whenever an error occurs communicating with a real robot.

    Typically, this is raised within the robot class when a connection could not be established, timed out, or invalid
    data that cannot be dealt with was received.
    """
    pass


class GUIError(SoarError):
    """ Raised when an error occurs while drawing the world or one of its objects. """
    pass
