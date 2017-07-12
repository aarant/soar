from argparse import ArgumentParser
from queue import Queue
import threading
from threading import Thread, current_thread
import importlib.util
import importlib
import traceback as tb
import sys

import soar.gui.soar_ui as soar_ui
from soar.gui import plugin
from soar.controller import *

headless = False
brain = None
brain_path = None
world = None
world_path = None
robot = None
controller = None
gui = None
queue = Queue(maxsize=1000)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def reset_queue():
    """ Reset the queue """
    global queue
    queue = Queue(maxsize=1000)


def message(func, *data):
    global queue
    queue.put((func, data))


def load_module(path):
    spec = importlib.util.spec_from_file_location('', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def set_brain_plugins():
    global brain
    for key in plugin.__dict__:
        if key == 'Toplevel':
            #print(key, plugin.__dict__[key])
            setattr(brain, key, plugin.__dict__[key])
            #print(getattr(brain, key))


# Public functions TODO
def make_gui(*data):
    """ Creates the GUI, updates plugin attributes, and enters the main UI loop """
    global gui
    gui = soar_ui.SoarUI()
    plugin.Toplevel = gui.toplevel
    gui.mainloop()
    print('Mainloop over')  # TODO


def load_brain(*data):
    """ Loads a brain file """
    global brain, brain_path, robot
    brain_path = data[0]
    brain = load_module(brain_path)
    set_brain_plugins()
    robot = brain.robot
    print('LOAD BRAIN:', data[0])


def load_world(*data):
    """ Loads a world file """
    global world, world_path
    world_path = data[0]
    world = load_module(world_path).world
    print('LOAD WORLD:', data[0])


def draw(*data):
    """ Draws one or more objects by placing them on the UI's draw queue """
    global gui
    for obj in data:
        gui.draw_queue.put(obj)


def make_sim(*data):
    global robot, brain, world, controller, gui
    controller = Controller(robot, brain, world)
    controller.on_load()
    gui.sim_ready()


def make_interface(*data):
    global robot, brain, controller
    controller = Controller(robot, brain)
    controller.on_load()
    gui.real_ready()


def start_controller(*data):
    global controller
    t = Thread(target=controller.on_start)
    controller.thread = t
    t.start()


def pause_controller(*data):
    global controller
    controller.running = False
    if controller.thread != current_thread():
        controller.thread.join()


def step_controller(*data):
    global controller
    controller.on_step()


def stop_controller(*data):
    global controller
    controller.running = False
    if controller.thread != current_thread():
        controller.thread.join()
    controller.on_stop()


def shutdown_controller(*data):
    global controller
    if controller:
        controller.running = False
        if controller.thread != current_thread():
            controller.thread.join()
        controller.on_shutdown()


def controller_soft_error(*data):
    """ Called after a controller error we can recover from occurs """
    global brain, brain_path, world, world_path, robot, gui
    if brain:
        brain = load_module(brain_path)
        set_brain_plugins()
        robot = brain.robot
    if world:
        world = load_module(world_path).world
    if gui:
        gui.soft_reload()


def controller_failure(*data):
    """ The controller has failed in an unanticipated way """
    global controller
    if controller:
        controller.running = False
        controller.on_failure()
        if gui:
            gui.controller_failure()


def close(*data):
    global robot
    try:
        robot.on_shutdown()
    except Exception:
        pass
    return True


def mainloop():
    global gui
    while True:
        func, data = queue.get()
        try:
            quit_loop = func(*data)
        except Exception:  # Catch any unhandled exceptions
            tb.print_exc()
            if gui:  # If there is a GUI, treat the exception as non-fatal and reset it
                controller_failure()
                gui.reset(clear_output=False)
                gui.reset_ui()
            else:  # Otherwise break, because no recovery is possible
                break
        else:
            if quit_loop:  # If a function returns true, abort the loop
                break
        finally:
            queue.task_done()


def main():
    """ Main entrypoint, for use from the command line """
    global headless, brain, world, robot, queue
    parser = ArgumentParser(prog='soar', description='SoaR v0.9.0\nSnakes on a Robot: An extensible Python framework '
                                                     'for simulating and interacting with robots')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('-b', metavar='brain', type=str, help='Path to the brain file', required=False)
    parser.add_argument('-w', metavar='world', type=str, help='Path to the world file', required=False)
    args = parser.parse_args()
    headless = args.headless
    brain_path = args.b
    world_path = args.w
    if headless:
        if brain_path:
            message(load_brain, brain_path)
        if world_path:
            message(load_world, world_path)
    else:
        message(make_gui)
        if brain_path:
            message(load_brain, brain_path)
        if world_path:
            message(load_world, world_path)
    mainloop()
    print('Post-processing')
    quit()
