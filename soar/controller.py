""" soar.controller """

import traceback as tb
from time import sleep
from threading import current_thread

from soar import client


class SoarIOError(Exception):
    """ Raised whenever an error occurs communicating with a real robot """


class Controller:
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
    def __init__(self, robot, brain, world=None, step_duration=0.1):
        self.robot = robot
        self.brain = brain
        self.world = world
        self.step_duration = step_duration
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
            self.robot.move(self.world.initial_position)
            self.world.add(self.robot)
            if client.gui:
                client.message(client.draw, self.world)
        self.brain.print = lambda *args, **kwargs: print('>>>', *args, **kwargs)
        self.protected_exc(self.robot.on_load, self.brain.on_load)

    def on_start(self):
        """ Called when the controller is started/unpaused """
        if not self.started:
            self.protected_exc(self.robot.on_start, self.brain.on_start)
            self.started = True
            self.protected_exc(lambda: self.brain.on_step(self.step_duration))  # Do the initial robot step
        self.running = True
        while self.running:
            self.on_step()
            sleep(self.step_duration)

    def on_step(self):
        """ Called when the controller undergoes a single step """
        if not self.started:
            self.protected_exc(self.robot.on_start, self.brain.on_start)
            self.started = True
            self.protected_exc(lambda: self.brain.on_step(self.step_duration))  # Do the initial robot step
        self.protected_exc(lambda: self.brain.on_step(self.step_duration))  # First step the brain
        if self.world:  # If simulating, the world will handle the robot's step
            self.protected_exc(lambda: self.world.on_step(self.step_duration))  # TODO: Do this without lambdas?
            if client.gui:
                client.message(client.draw, self.world)
        else:  # Otherwise step the robot
            self.protected_exc(lambda: self.robot.on_step(self.step_duration))

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
        try:
            self.robot.on_shutdown()  # If the shutdown fails, handle it silently
        except Exception:
            pass
