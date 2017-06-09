from argparse import ArgumentParser
from queue import Queue
import threading
from threading import Thread
import importlib.util

from soar.gui.soar_ui import SoarUI, polygon
from soar.geometry import Point
from soar.client.messages import *
from soar.sim.sim import start_sim

headless = False
brain = None
world = None
robot = None
queue = Queue(maxsize=1000)
tk_queue = None

def reset_queue():
    """ Reset the queue """
    global queue
    queue = Queue(maxsize=1000)

def message(topic, *data):
    if len(data) == 0:
        data = None
    queue.put((topic, data))

def load_module(path):
    spec = importlib.util.spec_from_file_location('', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def mainloop():
    global headless, brain, world, robot, queue, tk_queue
    while True:
        topic, data = queue.get()
        print('Threads: ' + str(threading.active_count()), topic, data)
        if topic == MAKE_GUI:
            app = SoarUI(brain=brain, world=world)
            tk_queue = app.queue
            app.mainloop()  # Run Tk in main thread
        elif topic == LOAD_BRAIN:  # TODO Make sure brain/world actually exists
            brain = load_module(data[0])  # TODO Might have to reload other things
            robot = brain.robot
        elif topic == LOAD_WORLD:
            world = load_module(data[0])
        elif topic == MAKE_SIM:
            robot = brain.robot
            robot.pos = Point(*world.initial_position)
            if not headless:
                tk_queue.put(world.options)
                tk_queue.put(robot)
        elif topic == CLOSE_SIM:
            tk_queue.put('DESTROY')
        elif topic == CLOSE:
            queue.task_done()
            break
        queue.task_done()


def main():
    """ Main entrypoint, for use from the command line """

    global headless, brain, world, robot, queue
    parser = ArgumentParser(prog='soar',
                                     description='SoaR v0.3.0\n'
                                                 'Snakes on a Robot: An extensible Python framework '
                                                 'for simulating and interacting with robots')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('-b', metavar='brain', type=str, help='Path to the brain file', required=False)
    parser.add_argument('-w', metavar='world', type=str, help='Path to the world file', required=False)
    args = parser.parse_args()
    headless = args.headless
    brain = args.b
    world = args.w
    if not headless:
        if brain is not None:
            message(LOAD_BRAIN, brain)
        if world is not None:
            message(LOAD_WORLD, world)
        message(MAKE_GUI)
    mainloop()
    print('Post-processing')
    quit()
