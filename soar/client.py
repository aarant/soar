from argparse import ArgumentParser
from queue import Queue
import threading
from threading import Thread
import importlib.util

from soar.gui.soar_ui import SoarUI
from soar.gui import plugin
from soar.geometry import Point, Pose
from soar.controller import *

headless = False
brain = None
world = None
robot = None
controller = None
gui = None
queue = Queue(maxsize=1000)

def reset_queue():
    """ Reset the queue """
    global queue
    queue = Queue(maxsize=1000)

def message(func, *data):
    queue.put((func, data))

def load_module(path):
    spec = importlib.util.spec_from_file_location('', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def output(*strs):
    if gui:
        gui.print_queue.put('> ' + ' '.join([str(s) for s in strs]) + '\n')
    else:
        print(*strs)

def set_brain_plugins():
    global brain
    for key in plugin.__dict__:
        if key == 'Toplevel':
            print(key, plugin.__dict__[key])
            setattr(brain, key, plugin.__dict__[key])
            print(getattr(brain, key))

# Public functions TODO
def make_gui(*data):
    global gui
    gui = SoarUI(**data[0])
    plugin.Toplevel = gui.toplevel
    gui.mainloop()

def load_brain(*data):
    global brain, robot
    brain = load_module(data[0])
    set_brain_plugins()
    robot = brain.robot

def load_world(*data):
    global world
    world = load_module(data[0]).world

def draw(*data):
    global gui
    for obj in data:
        gui.draw_queue.put(obj)

def make_sim(*data):
    global robot, brain, world, controller
    controller = Controller(robot, brain, world)
    controller.on_load()

def make_interface(*data):
    global robot, brain, controller
    controller = Controller(robot, brain)
    controller.on_load()

def start_controller(*data):
    global controller
    t = Thread(target=controller.on_start)
    controller.thread = t
    t.start()

def pause_controller(*data):
    global controller
    controller.running = False
    controller.thread.join()

def step_controller(*data):
    global controller
    controller.on_step()

def stop_controller(*data):
    global controller
    controller.running = False
    try:
        controller.thread.join()
    except AttributeError:
        pass
    controller.on_stop()

def shutdown_controller(*data):
    global controller
    controller.running = False
    try:
        controller.thread.join()
    except AttributeError:
        pass
    controller.on_shutdown()

def controller_failure(*data):
    if gui:
        gui.close_cmd(False)

def mainloop():
    while True:
        func, data = queue.get()
        print('Threads: ' + str(threading.active_count()), func, data)
        if func != 'CLOSE':
            func(*data)
        else:
            queue.task_done()
            break
        queue.task_done()


def main():
    """ Main entrypoint, for use from the command line """
    global headless, brain, world, robot, queue
    parser = ArgumentParser(prog='soar', description='SoaR v0.7.2\nSnakes on a Robot: An extensible Python framework '
                                                     'for simulating and interacting with robots')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('-b', metavar='brain', type=str, help='Path to the brain file', required=False)
    parser.add_argument('-w', metavar='world', type=str, help='Path to the world file', required=False)
    args = parser.parse_args()
    headless = args.headless
    brain_path = args.b
    world_path = args.w
    if brain_path is not None:
        message(load_brain, brain_path)
    if world_path is not None:
        message(load_world, world_path)
    if not headless:
        message(make_gui, {'brain_path': brain_path, 'world_path': world_path})
    mainloop()
    print('Post-processing')
    quit()
