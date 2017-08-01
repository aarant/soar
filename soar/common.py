""" Soar common constants.

Contains named constants for sending messages to the client and determining the type of a controller.

TODO: Finish defining constants
"""
# Client futures
MAKE_GUI = 0  #: No arguments. Build the main Tkinter-based GUI and enter its event loop
LOAD_BRAIN = 1
LOAD_WORLD = 2
MAKE_CONTROLLER = 3
START_CONTROLLER = 4
PAUSE_CONTROLLER = 5
STEP_CONTROLLER = 6
STOP_CONTROLLER = 7
SHUTDOWN_CONTROLLER = 8
CONTROLLER_COMPLETE = 9
CONTROLLER_SOFT_ERROR = 10
CONTROLLER_IO_ERROR = 11
CONTROLLER_FAILURE = 12
LOGGING_ERROR = 13
STEP_FINISHED = 14
GUI_LOAD_BRAIN = 15
GUI_LOAD_WORLD = 16
NOP = 17

# Messages shared between the client and UI
DRAW = 'DRAW'
CLOSE_LINKED = 'CLOSE_LINKED'
CLOSE_ALL = 'CLOSE_ALL'
MAKE_WORLD_CANVAS = 'MAKE_WORLD_CANVAS'
RELOAD_FINISHED = 'RELOAD_FINISHED'
GUI_ERROR = 'GUI_ERROR'

# Other constants
SIM = 'SIM'
REAL = 'REAL'
EXCEPTION = 'EXCEPTION'
