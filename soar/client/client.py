from argparse import ArgumentParser
from queue import Queue
import threading

from soar.gui.soar_ui import SoarUI
from soar.client.messages import *

headless = False
brain = None
world = None
robot = None
queue = Queue(maxsize=1000)

def reset_queue():
    """ Reset the queue """
    global queue
    queue = Queue(maxsize=1000)

def message(topic, data=None):
    queue.put((topic, data))

def mainloop():
    global headless, brain, world, robot, queue
    while True:
        topic, data = queue.get()
        print(threading.active_count())
        print(topic, data)
        print(queue)
        if topic == MAKE_GUI:
            app = SoarUI(brain=brain, world=world)
            app.mainloop()  # Run Tk in main thread
            print('foo')
        elif topic == LOAD_BRAIN:  # TODO Make sure brain/world actually exists
            brain = data  # TODO Might have to reload other things
        elif topic == LOAD_WORLD:
            world = data
        elif topic == CLOSE:
            break



def main():
    """ Main entrypoint, for use from the command line """

    global headless, brain, world, robot, queue
    parser = ArgumentParser(prog='soar',
                                     description='SoaR v0.1.0\n'
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
    quit()
