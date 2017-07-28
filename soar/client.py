""" Soar client entrypoint.

Classes and functions for interacting with Soar in general. This module serves as the main entrypoint to the package.
Projects desiring to invoke a Soar instance should import this module and call :func:`soar.client.main`.

Examples:
    This will invoke a GUI instance, which will terminate when the main window is closed, and always return 0.
    ::
        from soar.client.main import main
        return_value = main()

    If invoking a headless instance, paths to brain and world files should be specified:
    ::
        from soar.client.main import main
        return_value = main(brain_path='path/to/brain.py', world_path='path/to/world.py', headless=True)

    In this case, the return value will be 1 if an exception occurred and 0 otherwise.

    Logging is handled via passing a path:
    ::
        from soar.client.main import main
        return_value = main(logfile='path/to/logfile')

    or, using a file-like object:
    ::
        from soar.client.main import main
        return_value = main(logfile=open('path/to/logfile', 'r+'))
    """
import importlib.util
import os
import traceback as tb
import atexit
from queue import Queue

from soar import __version__
from soar.common import *
from soar.controller import Controller
from soar.controller import log
from soar.errors import *
from soar.gui.plot_window import PlotWindow
from soar.gui.soar_ui import SoarUI

brain = None
brain_path = None
world = None
world_path = None
robot = None
controller = None
gui = None
logfile = None
step_duration = 0.1
realtime = True
queue = Queue()


def empty_queue():  # Empties the queue
    global queue
    while not queue.empty():
        _ = queue.get()
        queue.task_done()


def exception_decorator(func):  # Catches exceptions and notifies the client
    def exception_wrap(*args, **kwargs):
        try:
            val = func(*args, **kwargs)
        except LoggingError as e:
            printerr('LoggingError: ' + str(e))
            message(LOGGING_ERROR)
            return EXCEPTION
        except SoarIOError as e:
            printerr('SoarIOError: ' + str(e))
            message(CONTROLLER_IO_ERROR)
            return EXCEPTION
        except GUIError as e:
            tb.print_exc()
            message(GUI_ERROR)
            return EXCEPTION
        except Exception:  # Any other exception (likely occurring in the brain) signifies controller failure
            tb.print_exc()
            message(CONTROLLER_FAILURE)
            return EXCEPTION
        else:  # Otherwise return the function's return value
            return val

    return exception_wrap


@exception_decorator
def wrapped_log(obj, mode='a'):
    global logfile
    log(obj, logfile, mode)


def message(msg, *args, **kwargs):
    """ Sends a message with data for the client to execute in the future, by putting it on the client's internal queue.

    Note that if an exception or controller failure occurs, the message may never be read as the queue will be purged.

    Args:
        msg: The message to send, defined in :mod:`soar.common`.
        *args: The variable length arguments to pass to the function.
        **kwargs: The keyword arguments to pass to the function.
    """
    global queue
    queue.put((msg, args, kwargs))


def load_module(path):  # Loads a module from a path and returns it as an object
    cd = os.getcwd()  # Get the current directory so we can restore it later
    path = os.path.abspath(path)  # Load from absolute paths
    try:  # Try to load the module in its own directory
        os.chdir(os.path.dirname(path))
        spec = importlib.util.spec_from_file_location(os.path.splitext(path)[0], path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:  # Restore the current directory
        os.chdir(cd)
    return module


def set_brain_attrs():  # Set attributes for the brain
    global brain, gui, logfile
    # Ensure that if the brain has not defined any required functions that they exist as NOPs
    for attr in ['on_load', 'on_start', 'on_step', 'on_stop', 'on_shutdown']:
        if not (hasattr(brain, attr) and callable(getattr(brain, attr))):
            setattr(brain, attr, lambda *args, **kwargs: None)
    if hasattr(brain, 'PlotWindow'):  # Ensure that PlotWindow() calls are properly wrapped
        if logfile:
            plot_log = wrapped_log
        else:
            plot_log = None
        if gui:
            def plot_window_wrap(title='Plotting Window', visible=True, linked=True):
                return PlotWindow(title, visible=visible, toplevel=gui.toplevel, log=plot_log, linked=linked)
        else:

            def plot_window_wrap(title='Plotting Window', visible=True, linked=True):
                return PlotWindow(title, visible=False, log=plot_log, linked=linked)
        setattr(brain, 'PlotWindow', plot_window_wrap)
    # Finally, ensure the brain has access to sim_completed
    setattr(brain, 'sim_completed', lambda obj=None: message(CONTROLLER_COMPLETE, obj))


def wrap_attrs(obj, names):  # Wrap object callables in the client exception decorator
    for name in names:
        if hasattr(obj, name) and callable(getattr(obj, name)):
            setattr(obj, name, exception_decorator(getattr(obj, name)))


def nop(*args, callback=None, **kwargs):  # A NOP, typically used for callbacks
    if callback:
        callback()


def make_gui(*args, **kwargs):  # Creates the GUI and enters the main UI loop
    global gui
    gui = SoarUI(client_msg=message, client_mainloop=mainloop)
    gui.mainloop()
    return True  # Exit client mainloop after GUI closes


def load_brain(path, *args, callback=None, silent=False, **kwargs):  # Loads a brain file, optionally calling a callback
    global brain, brain_path, robot, gui
    brain_path = path
    brain = load_module(brain_path)
    robot = brain.robot
    set_brain_attrs()
    if not silent:
        print('LOAD BRAIN:', path)
    if callback:
        callback()


def load_world(path, *args, callback=None, silent=False, **kwargs):  # Loads a world file, optionally calling a callback
    global world, world_path
    world_path = path
    world = load_module(world_path).world
    if not silent:
        print('LOAD WORLD:', path)
    if callback:
        callback()


def gui_load_brain(path, *args, **kwargs):  # Simulates loading a brain through the GUI
    global gui
    gui.after(0, gui.loading)
    gui.brain_path = os.path.abspath(path)
    load_brain(os.path.abspath(path), callback=lambda: gui.after(0, gui.brain_ready))


def gui_load_world(path, *args, **kwargs):  # Simulates loading a world through the GUI
    global gui
    gui.after(0, gui.loading)
    gui.world_path = os.path.abspath(path)
    load_world(os.path.abspath(path), callback=lambda: gui.after(0, gui.world_ready))


def make_controller(*args, simulated=True, callback=None, **kwargs):  # Makes the controller and loads it
    global robot, brain, brain_path, world, world_path, controller, gui, logfile, step_duration, realtime
    if logfile:  # Write initial meta information to file
        wrapped_log({'type': 'meta', 'simulated': simulated, 'version': '1.0.0.dev0', 'brain': os.path.abspath(brain_path),
                     'world': os.path.abspath(world_path)}, mode='w')
        controller_log = wrapped_log
    else:
        controller_log = None
    controller = Controller(client_msg=message, robot=robot, brain=brain, world=world, simulated=simulated, gui=gui,
                            step_duration=step_duration, realtime=realtime, log=controller_log)
    wrap_attrs(controller, ['step_timer', 'on_load', 'run', 'on_stop', 'on_shutdown'])
    if not simulated:  # If working with a real robot, register its shutdown to be called at exit
        atexit.register(shutdown_robot, robot)
    if controller.on_load() == EXCEPTION:
        return
    if callback:
        callback()


def make_world_canvas(world, *args, **kwargs):  # Builds the canvas in the gui
    global gui
    if gui:
        gui.message(MAKE_WORLD_CANVAS, world)


def draw(*args, **kwargs):  # Draws one or more objects by placing them on the UI's draw queue
    global gui
    for obj in args:
        gui.message(DRAW, obj)


def start_controller(*args, callback=None, **kwargs):
    global controller, gui
    if controller:
        if controller.run() == EXCEPTION:
            return
    if callback:
        callback()


def pause_controller(*args, callback=None, **kwargs):
    global controller
    if controller:
        controller.stop_thread()
    if callback:
        callback()


def step_controller(n, *args, **kwargs):
    global controller
    if controller:
        controller.run(n=n)


def step_finished(*args, **kwargs):
    global gui, controller
    if gui:  # If there is a gui, notify it that the steps have completed.
        if controller and not controller.stopped:  # However only do so if the controller has not stopped.
            gui.step_finished()
    else:  # Break out of the mainloop after the steps have finished
        return True


def stop_controller(*args, callback=None, **kwargs):
    global controller
    if controller:
        if controller.on_stop() == EXCEPTION:
            return
    if callback:
        callback()


def shutdown_controller(*args, **kwargs):
    global controller
    if controller:
        controller.on_shutdown()
        atexit.unregister(shutdown_robot)  # No need to shut down the robot at exit anymore
    controller = None


def logging_error(*args, **kwargs):  # Called when a LoggingError occurs
    global gui
    if not gui:  # Quit out of the mainloop if not running in GUI mode
        raise SoarError('Unable to handle logging errors in headless mode')


def gui_error(*args, **kwargs):
    global gui
    if gui:
        gui.gui_error()
    else:
        raise SoarError('GUIErrors should not occur in headless mode')


def controller_io_error(*args, **kwargs):  # Called after a SoarIOError occurs
    global brain, brain_path, world, world_path, robot, gui
    if gui:
        gui.controller_io_error()
    else:  # Err out of the mainloop
        raise SoarError('Unable to handle SoarIOError in headless mode')


def controller_failure(*args, **kwargs):  # The controller has failed in an unanticipated way
    global controller
    empty_queue()  # Empty the client queue
    if controller:
        controller.on_failure()
    if gui:
        gui.controller_failure()
        atexit.unregister(shutdown_robot)  # No need to shut down the robot at exit anymore
    else:
        raise SoarError('Unable to handle controller failures in headless mode')


def controller_complete(*args, **kwargs):  # Called when the simulation has completed
    global gui, controller, logfile
    if controller:
        print('Simulation completed.')
        if controller.on_stop() == EXCEPTION:
            return
        if gui:
            gui.stop_ready()
        if controller.on_shutdown() == EXCEPTION:
            return
        if logfile:
            if len(args) > 0 and args[0]:
                wrapped_log(args[0])
            wrapped_log({'type': 'meta', 'completed': controller.elapsed})
        if not gui:  # Prepare to quit out of the mainloop if no gui
            return True


def shutdown_robot(robot):  # Called by the mainloop and at exit to ensure the robot is shutdown
    print('Shutting down robot')  # TODO: Remove after debug
    try:
        robot.on_shutdown()
    except Exception:  # Ignore errors
        pass


msg_map = {MAKE_GUI: make_gui,
           LOAD_BRAIN: load_brain,
           LOAD_WORLD: load_world,
           MAKE_CONTROLLER: make_controller,
           DRAW: draw,
           START_CONTROLLER: start_controller,
           PAUSE_CONTROLLER: pause_controller,
           STEP_CONTROLLER: step_controller,
           STOP_CONTROLLER: stop_controller,
           SHUTDOWN_CONTROLLER: shutdown_controller,
           CONTROLLER_COMPLETE: controller_complete,
           CONTROLLER_IO_ERROR: controller_io_error,
           CONTROLLER_FAILURE: controller_failure,
           STEP_FINISHED: step_finished,
           MAKE_WORLD_CANVAS: make_world_canvas,
           GUI_LOAD_BRAIN: gui_load_brain,
           GUI_LOAD_WORLD: gui_load_world,
           NOP: nop,
           LOGGING_ERROR: logging_error,
           GUI_ERROR: gui_error,}


def mainloop():
    global gui
    while True:
        msg, args, kwargs = queue.get()
        try:
            quit_loop = msg_map[msg](*args, **kwargs)
        except Exception as e:  # Catch any unhandled exceptions
            tb.print_exc()
            if gui:  # If there is a GUI, treat the exception as non-fatal and signal a controller failure
                controller_failure()
            else:  # Otherwise, return and signify an error
                return 1
        else:  # Successful client function execution
            if quit_loop:  # If a function returns true, end the loop and complete
                return 0
        finally:
            queue.task_done()


def main(brain_path=None, world_path=None, headless=False, logfile=None, step_duration=0.1, realtime=True):
    """ Main entrypoint, for use from the command line or other packages. Starts a Soar instance.

    Args:
        brain_path (optional): The path to the initial brain to load. Required if headless, otherwise not required.
        world_path (optional): The path to the initial world to load. Required if headless, otherwise not required.
        headless (bool): If `True`, run Soar in headless mode, immediately running a simulation.
        logfile (optional): The path to the log file, or a file-like object to log data to.
        step_duration (float): The duration of a controller step, in seconds.
        realtime (bool): If `True`, the controller will never sleep to make a step last the proper length. Instead,
        it will run as fast as possible.

    Returns:
        0 if Soar's execution successfully completed, 1 otherwise.
    """
    global robot
    globals()['logfile'] = logfile
    globals()['step_duration'] = step_duration
    globals()['realtime'] = realtime
    if headless:
        if brain_path and world_path:
            message(LOAD_BRAIN, brain_path)
            message(LOAD_WORLD, world_path)
        else:
            printerr('Brain and world files required while running in headless mode.')
            return 1
        message(MAKE_CONTROLLER, simulated=True)
        message(START_CONTROLLER)
    else:
        message(MAKE_GUI)
        if brain_path:
            message(GUI_LOAD_BRAIN, brain_path)
        if world_path:
            message(GUI_LOAD_WORLD, world_path)

    return_val = mainloop()
    shutdown_robot(robot)
    atexit.unregister(shutdown_robot)  # No need to shut down the robot at exit anymore
    return return_val
