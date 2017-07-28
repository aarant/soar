""" Soar controller classes and functions for controlling robots, simulated or real. """
import json
from io import StringIO
from threading import Thread
from time import sleep
from timeit import default_timer as timer

from soar.common import DRAW, CONTROLLER_COMPLETE, STEP_FINISHED, MAKE_WORLD_CANVAS
from soar.errors import LoggingError


def sim_completed(obj=None):
    """ Called by the brain to signal that the simulation has completed.

    This is set by the controller before the brain is loaded.

    Args:
        obj (optional): Optionally, an object to log to the logfile after the simulation has completed.
    """
    pass


def log(obj, logfile, mode='a'):
    """ Log a serialized JSON object to a path or file-like object, adding a newline after.

    Args:
        obj: The object to be serialized.
        logfile: The path to the log file, or a file-like object that has a `write()` method.
        mode: The mode in which the file is to be opened.
    """
    # Recast file errors as Soar errors
    if hasattr(logfile, 'write'):
        try:
            logfile.write(json.dumps(obj) + '\n')
        except Exception as e:
            raise LoggingError(str(e))
    else:
        try:
            with open(logfile, mode) as f:
                f.write(json.dumps(obj) + '\n')
        except (OSError, IOError) as e:
            raise LoggingError(str(e))


class Controller:
    """ A class for interacting with simulated or real robots.

    Initialized by the client and used to call the user defined methods of the robot and brain.

    Attributes:
        running (bool): Indicates whether the controller is currently running--that is, repeatedly stepping.
        started (bool): Indicates whether the controller has been started.
        stopped (bool): Indicates whether the controller has been stopped.
        step_count (int): The number of steps that have elapsed so far.
        elapsed (float): The number of seconds spent actually running. Unless a step takes longer than
            `step_duration`, this will typically be the `step_count` multiplied by `step_duration`. If any steps take
            longer, the additional time will also be counted here.

    Args:
        client_msg: The function to call to send a message to the client.
        gui (bool): If `True`, worlds must be drawn on each step.
        simulated (bool): If `True`, the controller will simulate the robot. Otherwise it will treat the robot as real.
        robot: An instance of :class:`soar.robot.base.BaseRobot` or a subclass.
        brain: The currently loaded brain module, supporting the `on_load()`, `on_start()`, `on_step()`, `on_stop()`,
            and `on_shutdown()` methods.
        realtime (bool): If `True`, stepping takes real time--that is, the controller will sleep for whatever time is
            not used running the step, until the step has taken at least `step_duration` seconds. Otherwise, no
            sleeping will occur; however the elapsed time will behave as if each step was at least `step_duration` long.
        world: An instance of :class:`soar.sim.world.World` or one of its subclasses if one is loaded, or `None`.
        step_duration (float): The duration of a single step, in seconds.
        log: A callable that accepts a `dict`-like object as an argument to log to a file, or `None`, if no logging
        is to take place.
    """
    def __init__(self, client_msg, robot, brain, simulated, gui, step_duration=0.1, realtime=True, world=None,
                 log=None):
        self.client_msg = client_msg
        self.robot = robot
        self.brain = brain
        self.step_duration = step_duration
        self.simulated = simulated
        self.gui = gui
        self.realtime = realtime
        self.world = world
        self.log = log
        self.running = False
        self.started = False
        self.stopped = False
        self.elapsed = 0.0
        self.step_count = 0
        self._step_thread = None
        self._avg_offset = 0.0
        self._brain_log_contents = StringIO()

    def step_timer(self, n=None):  # If n is unspecified, run forever until stopped.
        # step_timer is typically wrapped by the client so that any exceptions that occur are made known.
        self.running = True
        while self.running and (n is None or n > 0):
            start = timer()  # Time the actual step, with sleeping included
            step_time = self.single_step()
            if step_time < self.step_duration:  # Just add self.step_duration to the elapsed time
                self.elapsed += self.step_duration
                if self.realtime:  # If running in real time, sleep accordingly
                    sleep(max(0, self.step_duration-step_time-self._avg_offset))
            else:  # If the step took longer than it should have, add its length to self.elapsed and don't sleep
                self.elapsed += step_time
            if n:  # If running for a specific number of steps, decrement
                n -= 1
            if self.realtime:  # If running in real time, try and figure out by how much the sleep was too long or short
                real_step_duration = timer() - start
                offset = real_step_duration - self.step_duration
                self._avg_offset = 0.75 * self._avg_offset + 0.25 * offset  # Exponentially weighted moving average
        if self.running:  # If the timer finished naturally, without being stopped, notify the client
            self.running = False
            self.client_msg(STEP_FINISHED)

    def stop_thread(self):  # Stops the currently running step thread, if it exists
        self.running = False
        if self._step_thread:
            self._step_thread.join()

    def on_load(self):
        """ Called when the controller is loaded. """
        # Set brain print function and robot mode
        if self.log:  # If we are logging, make sure anything the brain prints is added to the log
            def brain_print(*args, **kwargs):
                print('>>>', *args, **kwargs)
                print(*args, file=self._brain_log_contents, **kwargs)
        else:
            def brain_print(*args, **kwargs):
                print('>>>', *args, **kwargs)
        setattr(self.brain, 'print', brain_print)
        self.robot.simulated = self.simulated
        if self.simulated:  # If we are simulating, we have to initialize the world
            self.robot.move(self.world.initial_position)
            self.world.add(self.robot)
            if self.gui:  # If a GUI exists, we have to tell it to draw the world
                self.client_msg(MAKE_WORLD_CANVAS, self.world)
        # The robot is loaded first so that any setup required for the brain's operation is done beforehand.
        self.robot.on_load()
        self.brain.on_load()

    def run(self, n=None):
        """ Runs the controller, starting it if necessary, for one or many steps, or without stopping.

        Args:
            n: If `None`, run forever, at least until stopped. If 0, start the controller, if it has not yet been
                started. Otherwise, for `n > 0`, run for that many steps.
        """
        if not self.started:
            self.robot.on_start()
            self.brain.on_start()
            self.started = True
        if n == 0:  # Don't do any steps
            return
        if n == 1:  # If we're just doing one step, no need to start a new thread
            step_time = self.single_step()
            if step_time < self.step_duration:  # Just add self.step_duration to the elapsed time
                self.elapsed += self.step_duration
            else:  # If the step took longer than it should have, add its length to self.elapsed
                self.elapsed += step_time
            self.client_msg(STEP_FINISHED)
        else:  # Otherwise let the step timer run the steps
            self._step_thread = Thread(target=lambda: self.step_timer(n=n), daemon=True)
            self._step_thread.start()

    def single_step(self):  # Undergoes a single step, returns the number of seconds the step took
        start = timer()
        # First step the brain
        self.brain.on_step(self.step_duration)
        if self.world:  # If simulating, the world will handle the robot's step
            self.world.on_step(self.step_duration)
            if self.gui:
                self.client_msg(DRAW, self.world)
        else:  # Otherwise step the robot on its own
            self.robot.on_step(self.step_duration)
        if self.log:  # Log information about the step to the log file
            log_object = {'type': 'step', 'time': self.elapsed, 'step': self.step_count, 'robot': self.robot.to_dict()}
            if self._brain_log_contents.getvalue() != '':
                log_object.update({'brain_print': self._brain_log_contents.getvalue()})
                self._brain_log_contents.truncate(0)
                self._brain_log_contents.seek(0)
            self.log(log_object)
        self.step_count += 1
        if self.step_count > 10000:  # So that no simulation runs forever TODO: Maybe this could be better?
            self.client_msg(CONTROLLER_COMPLETE)
        return timer()-start

    def on_stop(self):
        """ Called when the controller is stopped. """
        self.stop_thread()
        self.brain.on_stop()
        self.robot.on_stop()
        self.started = False
        self.stopped = True

    def on_shutdown(self):
        """ Called when the controller is shut down. """
        self.stop_thread()
        self.brain.on_shutdown()
        self.robot.on_shutdown()

    def on_failure(self):
        """ Called when the controller fails. """
        self.stop_thread()
        self.started = False
        self.stopped = True
        try:
            self.robot.on_shutdown()  # Ignore any errors while trying to shutdown
        except Exception:
            pass
