import traceback as tb
from time import sleep
from threading import current_thread

from soar import client


class SoarIOError(Exception):
    """ Raised whenever an error occurs communicating with a real robot """


class Controller:
    def __init__(self, robot, brain, world=None, tick_duration=0.1):
        """ A class for interacting with simulated or real robots

        Initialized by the client and used to call the user defined methods of the robot and brain

        Attributes:
            running (bool): Indicates whether the controller is currently running; i.e, repeatedly stepping
            started (bool): Indicates whether the controller has been started
            thread (Thread): The thread in which the controller is currently running

        Args:
            robot: An instance of a subclass of BaseRobot
            brain: The currently loaded brain module, supporting the on_load(), on_start(), on_step(), on_stop(), and
                   on_shutdown() methods
            world: An instance of World or one of its subclasses. If this argument is omitted or None, the Controller
                   will be interacting with a real robot
        """
        self.robot = robot
        self.brain = brain
        self.world = world
        self.tick_duration = tick_duration
        self.running = False
        self.started = False
        self.thread = current_thread()

    def protected_exc(self, *funcs):
        """ Executes function(s) with protection, notifying the client of exceptions which occur

        If a SoarIOError exception occurs during the execution of any function, print the exception's content to stderr.
        This triggers a controller soft error, which necessitates reloading the brain and world

        If any other exception occurs, print the full traceback to stderr, and signal a controller failure to the client

        Args:
            *funcs: A variable length list of callables
        """
        try:
            for func in funcs:
                func()
        except SoarIOError as e:  # If a communication error occurs, trigger a soft error
            client.eprint('SoarIOError: ' + str(e))
            client.message(client.controller_soft_error)
        except Exception:  # Any other exception (likely occurring in the brain) signifies controller failure
            tb.print_exc()
            client.message(client.controller_failure)

    def on_load(self):
        """ Called when the controller is loaded """
        if self.world:  # If there is a world, we are simulating, and potentially drawing it
            self.robot.move(self.world.initial_position)  # TODO
            self.world.add(self.robot)
            if client.gui:
                client.message(client.draw, self.world)
        self.protected_exc(self.robot.on_load, self.brain.on_load)

    def on_start(self):
        """ Called when the controller is started/unpaused """
        if not self.started:
            self.protected_exc(self.robot.on_start, self.brain.on_start)
            self.started = True
        self.running = True
        while self.running:
            self.on_step()
            sleep(self.tick_duration)

    def on_step(self):
        """ Called when the controller undergoes a single step """
        if not self.started:
            self.protected_exc(self.robot.on_start, self.brain.on_start)
            self.started = True
        self.protected_exc(self.robot.on_step, self.brain.on_step)
        if self.world:
            self.world.tick(self.tick_duration)
            if client.gui:
                client.message(client.draw, self.world)

    def on_stop(self):
        """ Called when the controller is stopped """
        self.running = False
        self.started = False
        self.protected_exc(self.robot.on_stop, self.brain.on_stop)

    def on_shutdown(self):
        """ Called when the controller is shut down """
        self.protected_exc(self.robot.on_shutdown, self.brain.on_shutdown)

    def on_failure(self):
        """ Called when the controller fails """
        self.robot.on_shutdown()  # No protection here; if the shutdown fails, let the client handle it
