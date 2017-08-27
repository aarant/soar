# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/common.py
""" Soar common constants.

Contains named constants for sending messages to the client and determining the type of a controller.

Most use cases of soar will never need to use these constants or order client futures.

The values of the constants themselves are arbitrary.
"""
# Client futures
MAKE_GUI = 0  #: No arguments. Build the main Tkinter-based GUI and enter its event loop
LOAD_BRAIN = 1  #: Loads a brain, optionally calling the `callback` argument, and prints if `silent` is `False`.
LOAD_WORLD = 2  #: Loads a world, optionally calling the `callback` argument, and prints if `silent` is `False`.
MAKE_CONTROLLER = 3  #: Makes and loads the controller (type is based on `simulated`), and calls `callback`.
START_CONTROLLER = 4  #: Starts the controller, calling an optional callback.
PAUSE_CONTROLLER = 5  #: Pauses the controller, calling an optional callback.
STEP_CONTROLLER = 6  #: Steps the controller, where the first argument is the number of steps, infinite if `None`.
STOP_CONTROLLER = 7  #: Stops the controller and calls an optional callback.
SHUTDOWN_CONTROLLER = 8  #: Shuts down the controller.
CONTROLLER_COMPLETE = 9  #: Signal that the controller has completed and the simulation can end.
CONTROLLER_IO_ERROR = 11  #: Signals an IO error, which usually occurs when connecting with a real robot.
CONTROLLER_FAILURE = 12  #: Signals a controller failure.
LOGGING_ERROR = 13  #: Signals a logging error. These are typically ignored entirely.
STEP_FINISHED = 14  #: Signals that the step thread has finished.
GUI_LOAD_BRAIN = 15  #: Forces loading a brain as if it were done through the GUI.
GUI_LOAD_WORLD = 16  #: Forces loading a world as if it were done through the GUI.
SET_HOOKS = 17  #: Initializes the hooks
NOP = 18  #: Does nothing besides calling an optional callback

# Messages shared between the client and UI
DRAW = 19  #: Draw an object on the GUI's canvas.
MAKE_WORLD_CANVAS = 20  #: Tell the GUI to make the simulator canvas.
GUI_ERROR = 21  #: Signals an exception occurring somewhere in Tkinter callback

# Other constants
EXCEPTION = 22  #: Returned by wrapped functions to signal that an exception occurred during their execution.
