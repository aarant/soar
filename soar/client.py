# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/client.py
""" Soar client entrypoint.

Classes and functions for interacting with Soar in general. This module serves as the main entrypoint to the package.
Projects desiring to invoke a Soar instance should import this module and call :func:`soar.client.main`.

Examples:
    This will invoke a GUI instance, which will terminate when the main window is closed, and always return 0::

        from soar.client import main
        return_value = main()

    If invoking a headless instance, paths to brain and world files should be specified::

        from soar.client import main
        return_value = main(brain_path='path/to/brain.py', world_path='path/to/world.py', headless=True)

    In this case, the return value will be 1 if an exception occurred and 0 otherwise.

    Logging is handled via passing a path::

        from soar.client import main
        return_value = main(logfile='path/to/logfile')

    or, using a file-like object::

        from soar.client import main
        return_value = main(logfile=open('path/to/logfile', 'r+'))
    """
import os
import sys
import atexit
import json
import traceback as tb
from io import BytesIO
from queue import Queue
from threading import current_thread, main_thread

import soar.hooks
from soar import __version__
from soar.common import *
from soar.errors import *
from soar.controller import Controller
from soar.gui.soar_ui import SoarUI
from soar.gui.plot_window import PlotWindow
from soar.update import get_update_message
from soar.sim.geometry import *
from soar.sim.world import *

MAIN_THREAD = main_thread()  # Defines the main thread for later comparisons

brain = None
brain_path = None
__module_paths = []
__brain_modules = []
world = None
world_path = None
__world_modules = []
robot = None
controller = None
gui = None
logfile = None
step_duration = 0.1
realtime = True
options = None
plots = []
queue = Queue()


def empty_queue():  # Empty the queue
    global queue
    while not queue.empty():
        _ = queue.get()
        queue.task_done()


def tkinter_execute(func, after_idle=False):  # Run functions on Tk's main thread, synchronously
    def tk_wrap(*args, **kwargs):
        global gui, MAIN_THREAD
        if current_thread() != MAIN_THREAD:  # Only force Tk to call the function if not already on the main thread
            def return_exceptions(*args, **kwargs):  # Force a function to return any exception it raises
                try:
                    return_val = func(*args, **kwargs)
                except Exception as e:
                    return e
                else:
                    return return_val
            return_val = gui.synchronous_future(return_exceptions, *args, after_idle=after_idle, **kwargs)
            if isinstance(return_val, Exception):  # If the function returned an exception, raise it
                raise return_val
            return return_val
        else:  # If already on the main thread, just call the function
            return func(*args, **kwargs)
    return tk_wrap


def catch_exceptions(func):  # Catch exceptions that occur and notify the client, via futures
    def catch_wrap(*args, **kwargs):
        try:
            return_val = func(*args, **kwargs)
        except LoggingError as e:
            printerr('LoggingError: ' + str(e))
            future(LOGGING_ERROR)
            return EXCEPTION
        except SoarIOError as e:
            printerr('SoarIOError: ' + str(e))
            future(CONTROLLER_IO_ERROR)
            return EXCEPTION
        except GUIError as e:
            tb.print_exc()
            future(GUI_ERROR)
            return EXCEPTION
        except Exception as e:  # Any other exception (likely occurring in the brain) signifies controller failure
            tb.print_exc()
            future(CONTROLLER_FAILURE)
            return EXCEPTION
        else:  # Otherwise return the function's return value
            return return_val
    return catch_wrap


@catch_exceptions  # Logging that doesn't explode if something goes wrong
def log(obj, mode='a'):
    """ Log a serialized JSON object to a path or file-like object, adding a newline after.

    Args:
        obj: The object to be serialized.
        mode: The mode in which the file is to be opened.
    """
    global logfile
    # Recast any write errors as Soar errors
    if hasattr(logfile, 'write'):  # Try and treat logfile as a file-like object that has been opened
        try:
            logfile.write(json.dumps(obj) + '\n')
        except Exception as e:
            raise LoggingError(str(e))
    else:  # Otherwise treat it as a path, and open it
        try:
            with open(logfile, mode) as f:
                f.write(json.dumps(obj) + '\n')
        except (OSError, IOError) as e:
            raise LoggingError(str(e))


def future(name, *args, **kwargs):
    """ Adds a function with data for the client to execute in the future, by putting it on the client's internal queue.

    Note that if an exception or controller failure occurs, the future may never be executed as the client's queue will
    be purged.

    Certain futures accept an optional callback parameter.

    Args:
        name: The future to execute, defined in :mod:`soar.common`. and contained in `future_map`.
        *args: The variable length arguments to pass to the function.
        **kwargs: The keyword arguments to pass to the function.
    """
    global queue
    queue.put((name, args, kwargs))


# Loads a module from a path and returns its namespace, as well as any modules it loaded, as a list
def load_module(path, namespace=None):
    global __module_paths
    if namespace is None:
        # Input is replaced with a non-blocking dummy function.
        # The builtins are copied to the new namespace.
        namespace = {'input': lambda *args, **kwargs: print('Intercepted call to blocking input().',
                                                            file=sys.stderr), '__builtins__': __builtins__.copy()}
    path = os.path.abspath(path)  # Load from absolute paths

    namespace['__name__'] = os.path.splitext(os.path.basename(path))[0]  # Base name of the module
    module_dir = os.path.dirname(path)  # Module directory; this is added to sys.path for loading the modules
    before_load = sys.modules.copy()  # Make a copy of sys.modules to compare to later
    try:
        __module_paths.append(module_dir)
        sys.path.append(module_dir)
        code_object = compile(open(path, 'r').read(), path, 'exec')
        exec(code_object, namespace)  # Execute the module in an isolated namespace
    except Exception as e:  # Unload any loaded modules if, say, a syntax error occurred during load
        loaded = [modname for modname in sys.modules if modname not in before_load]  # List the modules that were loaded
        for modname in loaded:
            try:
                del sys.modules[modname]
            except KeyError:  # Assume that if there is a KeyError, the module is no longer loaded
                pass
        raise e  # Re-raise the exception
    finally:
        # Remove any module paths from sys.path
        for module_path in __module_paths:
            try:
                __module_paths.remove(module_path)
                sys.path.remove(module_path)
            except ValueError:  # If the path is not in sys.path, that's fine
                pass
        loaded = [modname for modname in sys.modules if modname not in before_load]  # List the modules that were loaded
    return namespace, loaded
    # Below is the old way of importing modules, as actual module objects, not namespaces
    # spec = importlib.util.spec_from_file_location(os.path.splitext(path)[0], path)
    # module = importlib.util.module_from_spec(spec)
    # spec.loader.exec_module(module)


def brain_setup():  # Setup a freshly loaded brain by wrapping the necessary methods
    global brain, gui, logfile, plots
    force_main_thread = False  # If this gets set to True, brain methods must run in the main thread

    # If the brain uses Tkinter and we're running in GUI mode, force brain methods to run in the main thread
    if gui and 'tkinter_hook' in brain:
        force_main_thread = True

    # Clear any plot objects that may have been listed by any previously loaded brain
    plots = []

    # Wrap brain methods, running them in Tk's thread if necessary
    for func in ['on_load', 'on_start', 'on_step', 'on_stop', 'on_shutdown']:
        if func in brain and callable(brain[func]):
            if force_main_thread:  # We hack a bit to run methods on the Tk thread, even when called from any thread
                brain[func] = tkinter_execute(brain[func])
        else:  # Make undefined functions do nothing
            brain[func] = lambda *args, **kwargs: None


def log_all_plots():  # Log any PlotWindow objects to the logfile. Use with caution.
    global plots
    for p in filter(lambda p: not p._destroyed, plots):  # Every plot that has not been destroyed
        image_bytes = BytesIO()
        p.save(image_bytes, format='png')
        log({'type': 'plot', 'data': image_bytes.getvalue().hex()})
        p._destroyed = True


def wrap_attrs(obj, names):  # Wrap object callables with the client exception decorator
    for name in names:
        if hasattr(obj, name) and callable(getattr(obj, name)):
            setattr(obj, name, catch_exceptions(getattr(obj, name)))


def nop(*args, callback=None, **kwargs):  # A NOP, typically used for callbacks
    if callback:
        callback()


def set_hooks(*args, **kwargs):  # Set the hooks that must be defined before a brain is ever loaded
    global gui, plots, MAIN_THREAD
    hooks = soar.hooks

    # Give the brain access to the mode soar is running in
    hooks.is_gui = lambda: gui is not None

    # First make sure all calls to PlotWindow use Toplevel() rather than Tk()
    PlotWindow._tk_started = True

    # Wrap PlotWindow, ensuring it plays nicely with Soar and Tk
    # This includes keeping track of open plots, attaching the window to the UI, and wrapping class methods
    plots = []
    class WrappedPlotWindow(PlotWindow):
        if gui:
            def __init__(self, title='Plotting Window', visible=True):
                # Wrap the class init so that it runs in the Tk mainloop
                if current_thread() != MAIN_THREAD:  # If not on the main thread, force it
                    tkinter_execute(PlotWindow.__init__)(self, title, visible=visible)
                else:  # If we're already on the main thread, do a normal init
                    PlotWindow.__init__(self, title, visible=visible)
                # Attach the window to the UI, and add it to the list of plots
                gui.attach_window(self)
                plots.append(self)

            def __getattribute__(self, name):
                if current_thread() != MAIN_THREAD:  # If not on the main thread
                    # Force accessing the attribute to run on the main thread
                    attr = tkinter_execute(PlotWindow.__getattribute__)(self, name)
                    # If the attribute is callable, wrap it so that it runs on the main thread
                    if callable(attr):
                        return tkinter_execute(attr)
                    return attr
                else:
                    return PlotWindow.__getattribute__(self, name)
        else:
            def __init__(self, title='Plotting Window', visible=True):
                # Ensure the window is not visible, and add the plot to the global list
                PlotWindow.__init__(self, title, visible=False)
                plots.append(self)
    sys.modules['soar.gui.plot_window'].PlotWindow = WrappedPlotWindow

    # Set the Tkinter hook to attach windows to the GUI
    if gui:
        hooks.tkinter_hook = gui.attach_window

    # Set the Tkinter wrap to execute widget callables on the Tk mainloop
    if gui:
        def tk_wrap(widget, linked=True):
            methods = [func for func in dir(widget) if callable(getattr(widget, func)) and not func.startswith('__')]
            for func_name in methods:
                func = getattr(widget, func_name)
                setattr(widget, func_name, tkinter_execute(func, after_idle=False))
            return hooks.tkinter_hook(widget, linked)
        hooks.tkinter_wrap = tk_wrap


def make_gui(*args, **kwargs):  # Creates the GUI and enters the main UI loop
    global gui
    gui = SoarUI(client_future=future, client_mainloop=mainloop)
    gui.mainloop()  # Enter the Tk event loop, which only ends when the GUI closes
    return True  # Exit client mainloop after GUI closes


def load_brain(path, *args, callback=None, silent=False, **kwargs):  # Loads a brain file, optionally calling a callback
    global brain, brain_path, robot, gui, __brain_modules, options
    brain_path = path
    for modname in __brain_modules:  # Try and delete previously loaded modules
        try:
            del sys.modules[modname]
        except KeyError:  # Assume if there is a KeyError that the module no longer exists
            pass
    brain, __brain_modules = load_module(brain_path)
    robot = brain['robot']
    if options is not None:
        robot.set_robot_options(**options)  # Set the robot options
    brain_setup()
    if not silent:
        print('LOAD BRAIN:', path)
    if callback:
        callback()


def load_world(path, *args, callback=None, silent=False, **kwargs):  # Loads a world file, optionally calling a callback
    global world, world_path, __world_modules
    world_path = path
    for modname in __world_modules:  # Try and delete previously loaded modules
        try:
            del sys.modules[modname]
        except KeyError:  # Assume if there is a KeyError that the module no longer exists
            pass
    world, __world_modules = load_module(world_path)
    world = world['world']  # Grab the actual world object, not the module
    if not silent:
        print('LOAD WORLD:', path)
    if callback:
        callback()


def gui_load_brain(path, *args, **kwargs):  # Simulates loading a brain through the GUI
    global gui
    gui.future(gui.loading)
    gui.brain_path = os.path.abspath(path)
    load_brain(os.path.abspath(path), callback=lambda: gui.future(gui.brain_ready))


def gui_load_world(path, *args, **kwargs):  # Simulates loading a world through the GUI
    global gui
    gui.future(gui.loading)
    gui.world_path = os.path.abspath(path)
    load_world(os.path.abspath(path), callback=lambda: gui.future(gui.world_ready))


def make_controller(*args, simulated=True, callback=None, **kwargs):  # Makes the controller and loads it
    global robot, brain, brain_path, world, world_path, controller, gui, logfile, step_duration, realtime
    if logfile:  # Write initial meta information to file
        log({'type': 'meta', 'simulated': simulated, 'version': __version__, 'brain': os.path.abspath(brain_path),
             'world': os.path.abspath(world_path)}, mode='w')
        controller_log = log
    else:
        controller_log = None
    controller = Controller(client_future=future, robot=robot, brain=brain, world=world, simulated=simulated, gui=gui,
                            step_duration=step_duration, realtime=realtime, log=controller_log)
    wrap_attrs(controller, ['load', 'run', 'step_thread', 'stop', 'shutdown'])
    if not simulated:  # If working with a real robot, register its shutdown to be called at exit
        atexit.register(shutdown_robot, robot)
    if controller.load() == EXCEPTION:
        return
    if callback:
        callback()


def make_world_canvas(world, *args, callback=None, **kwargs):  # Builds the canvas in the gui
    global gui
    if gui:
        gui.future(gui.make_world_canvas, world, callback=callback)


def draw(obj, *args, **kwargs):  # Draws one or more objects by placing them on the UI's draw queue
    global gui
    gui.future(gui.draw, obj)


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
        controller.pause()
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
            gui.future(gui.step_finished)
    else:  # Break out of the mainloop after the steps have finished
        return True


def stop_controller(*args, callback=None, **kwargs):
    global controller
    if controller:
        if controller.stop() == EXCEPTION:
            return
    if callback:
        callback()


def shutdown_controller(*args, **kwargs):
    global controller, logfile
    if controller:
        controller.shutdown()
        if logfile:  # Log any plots that were created
            log_all_plots()
        atexit.unregister(shutdown_robot)
    controller = None


def logging_error(*args, **kwargs):  # Called when a LoggingError occurs
    global gui
    if not gui:  # Quit out of the mainloop if not running in GUI mode
        raise SoarError('Unable to handle logging errors in headless mode')


def gui_error(*args, **kwargs):
    global gui
    if gui:
        gui.future(gui.gui_error)
    else:
        raise SoarError('GUIErrors should not occur in headless mode')


def controller_io_error(*args, **kwargs):  # Called after a SoarIOError occurs
    global brain, brain_path, world, world_path, robot, gui
    if gui:
        gui.future(gui.controller_io_error)
    else:  # Err out of the mainloop
        raise SoarError('Unable to handle SoarIOError in headless mode')


def controller_failure(*args, **kwargs):  # The controller has failed in an unanticipated way
    global controller
    empty_queue()  # Empty the client queue
    if controller:
        controller.failure()
    if gui:
        gui.future(gui.controller_failure)
        atexit.unregister(shutdown_robot)  # No need to shut down the robot at exit anymore
    else:
        raise SoarError('Unable to handle controller failures in headless mode')


def controller_complete(*args, **kwargs):  # Called when the simulation has completed
    global gui, controller, logfile, brain
    if controller:
        if controller.stop() == EXCEPTION:
            return
        if gui:
            gui.future(gui.stop_ready)
        if controller.shutdown() == EXCEPTION:
            return
        print('Simulation completed in', round(controller.elapsed, 3), '(simulated) seconds.')
        if logfile:
            if len(args) > 0 and args[0]:  # Log an object passed to sim_completed
                log(args[0])
            if 'PlotWindow' in brain:  # Log any plot window objects
                log_all_plots()
            log({'type': 'meta', 'completed': controller.elapsed})
        if not gui:  # Prepare to quit out of the mainloop if no gui
            return True


def shutdown_robot(robot):  # Called by the mainloop and at exit to ensure the robot is shutdown
    try:
        robot.on_shutdown()
    except Exception:  # Ignore errors
        pass


future_map = {MAKE_GUI: make_gui,
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
              GUI_ERROR: gui_error,
              SET_HOOKS: set_hooks}
""" A mapping from future names to their actual functions. """


def mainloop():
    global gui
    while True:
        name, args, kwargs = queue.get()
        try:
            quit_loop = future_map[name](*args, **kwargs)
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


def main(brain_path=None, world_path=None, headless=False, logfile=None, step_duration=0.1, realtime=True,
         options=None):
    """ Main entrypoint, for use from the command line or other packages. Starts a Soar instance.

    Args:
        brain_path (optional): The path to the initial brain to load. Required if headless, otherwise not required.
        world_path (optional): The path to the initial world to load. Required if headless, otherwise not required.
        headless (bool): If `True`, run Soar in headless mode, immediately running a simulation.
        logfile (optional): The path to the log file, or a file-like object to log data to.
        step_duration (float): The duration of a controller step, in seconds. By default, 0.1 seconds.
        realtime (bool): If `True`, the controller will never sleep to make a step last the proper length. Instead,
            it will run as fast as possible.
        options (dict): The keyword arguments to pass to the robot whenever it is loaded.

    Returns:
        0 if Soar's execution successfully completed, 1 otherwise.
    """
    global robot
    globals()['logfile'] = logfile
    globals()['step_duration'] = step_duration
    globals()['realtime'] = realtime
    globals()['options'] = options
    if headless:
        future(SET_HOOKS)
        if brain_path and world_path:
            future(LOAD_BRAIN, brain_path)
            future(LOAD_WORLD, world_path)
        else:
            printerr('Both a brain and world file are required while running in headless mode.')
            return 1
        future(MAKE_CONTROLLER, simulated=True)
        future(START_CONTROLLER)
    else:
        future(MAKE_GUI)
        future(SET_HOOKS)
        if brain_path:
            future(GUI_LOAD_BRAIN, brain_path)
        if world_path:
            future(GUI_LOAD_WORLD, world_path)
    return_val = mainloop()
    shutdown_robot(robot)
    atexit.unregister(shutdown_robot)  # No need to shut down the robot at program exit anymore, since we're done
    return return_val
