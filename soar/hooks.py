# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/hooks.py
""" Functions for brains to hook into various elements of Soar.

To make use of a given hook, a brain should import it from here. It will be redefined by the client or controller
accordingly.

Treat all hook names as reserved words, and do not use them as arbitrary variable names.
"""


def tkinter_hook(window, linked=True):
    """ Hook a Tkinter window created by the brain into Soar, so that the UI is aware of it.

    This function is redefined by the client before a brain is ever loaded.

    Brains that import this hook can expect that their methods will always run in the main thread when running in GUI
    mode, as Tkinter is not thread-safe. Otherwise, this is not guaranteed.

    If not running in GUI mode, importing and using this hook simply returns its argument unchanged and does nothing.

    Args:
        window: The Tkinter window to attach to Soar. This may also be some object that supports a `destroy()` method.
        linked (bool): If `True`, the window will be destroyed whenever the controller reloads.

    Returns:
        The window or object that was attached.
    """
    return window


def is_gui():
    """ Return whether Soar is running in GUI mode.

    Set by the client when it first loads.

    Returns:
        bool: `True` if running in GUI mode, `False` if headless.
    """
    return False


def sim_completed(obj=None):
    """ Called by the brain to signal that the simulation has completed.

    Set by the controller before the brain's `on_load()` function is called.

    Args:
        obj (optional): Optionally, an object to log to the logfile after the simulation has completed.
    """
    pass


def elapsed():
    """ Get the time that has elapsed running the controller.

    Set by the controller before the brain's `on_load()` function is called.

    Returns:
        float: The elapsed time in seconds, as defined in :attr:`soar.controller.Controller.elapsed`.
    """
    return 0.0


def raw_print(*args, **kwargs):
    """ Allows a brain to print without the `'>>>'` prepended.

    All arguments and keyword arguments are passed to `print()`.
    """
    return print(*args, **kwargs)



