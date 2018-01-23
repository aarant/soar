# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/controller.py
""" Controller classes and functions for controlling robots, simulated or real. """
from io import StringIO
from threading import Thread
from time import sleep
from timeit import default_timer as timer

from soar.common import DRAW, CONTROLLER_COMPLETE, STEP_FINISHED, MAKE_WORLD_CANVAS, EXCEPTION


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
        client_future: The function to call to schedule a future for the client to execute.
        gui: The currently :class:`soar.gui.soar_ui.SoarUI` instance, if any, or `None` if in headless mode.
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
    def __init__(self, client_future, robot, brain, simulated, gui, step_duration=0.1, realtime=True, world=None,
                 log=None):
        self.client_future = client_future
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

    def load(self):
        """ Called when the controller is loaded. """
        # Set brain print function
        def brain_print(*args, **kwargs):
            raw = kwargs.pop('raw', False)
            if raw:  # Print without the three carets '>>>'
                print(*args, **kwargs)
            else:
                print('>>>', *args, **kwargs)
            if self.log:  # If logging, ensure anything printed is logged
                print(*args, file=self._brain_log_contents, **kwargs)
        self.brain['print'] = brain_print

        if 'elapsed' in self.brain:  # Give brain read-only access to the elapsed time
            self.brain['elapsed'] = lambda: self.elapsed
        if 'sim_completed' in self.brain:  # Give brain the ability to end the simulation
            def sim_completed(obj=None):
                self.client_future(CONTROLLER_COMPLETE, obj)
                self.running = False
            self.brain['sim_completed'] = sim_completed

        self.robot.simulated = self.simulated
        if self.simulated:  # If we are simulating, we have to initialize the world
            self.robot.move(self.world.initial_position)
            self.world.add(self.robot)
            if self.gui:  # If a GUI exists, we make it try to draw the world before finishing loading
                if self.gui.synchronous_future(self.gui.make_world_canvas, self.world) == EXCEPTION:
                    return EXCEPTION
        # The robot is always loaded first, in case the brain depends on it
        self.robot.on_load()
        # TODO: Figure out how to force a brain crash
        # t = Thread(target=self.force_brain_crash, daemon=True)
        # t.start()
        self.brain['on_load']()

    # def force_brain_crash(self):
    #     sleep(5.0)
    #     class Dummy:
    #         def __getattribute__(*args, **kwargs):
    #             raise Exception
    #         def __call__(*args, **kwargs):
    #             raise Exception
    #     dummy_obj = Dummy()
    #     for key in self.brain.keys():
    #         if key == '__builtins__':
    #             for b_key in self.brain[key].keys():
    #                 self.brain[key][b_key] = dummy_obj
    #         else:
    #             self.brain[key] = dummy_obj
    #     print('Attempted to force brain crash', file=sys.stderr)

    def run(self, n=None):
        """ Runs the controller, starting it if necessary, for one or many steps, or without stopping.

        Args:
            n: If `None`, run forever, at least until stopped. If 0, start the controller, if it has not yet been
                started. Otherwise, for `n > 0`, run for that many steps.
        """
        if not self.started:
            self.robot.on_start()
            self.brain['on_start']()
            self.started = True
        if n == 0:  # Don't do any steps
            return
        if n == 1:  # If we're just doing one step, no need to start a new thread
            step_time = self.single_step()
            if step_time < self.step_duration:  # Just add self.step_duration to the elapsed time
                self.elapsed += self.step_duration
            else:  # If the step took longer than it should have, add its length to self.elapsed
                self.elapsed += step_time
            self.client_future(STEP_FINISHED)
        else:  # Otherwise let the step timer run the steps
            self._step_thread = Thread(target=lambda: self.step_thread(n=n), daemon=True)
            self._step_thread.start()

    def step_thread(self, n=None):  # If n is unspecified, run forever until stopped.
        # step_thread is typically wrapped by the client so that any exceptions that occur are made known.
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
            self.client_future(STEP_FINISHED)

    def single_step(self):  # Undergoes a single step, returns the number of seconds the step took
        if self.log:  # Log information before the step to the log file
            self.log_step_info()
        start = timer()
        # First step the brain
        self.brain['on_step'](self.step_duration)
        # Measure how long the brain took. If it took longer, the robot and world should be stepped accordingly
        brain_duration = timer()-start
        if brain_duration > self.step_duration:
            step_duration = brain_duration
        else:
            step_duration = self.step_duration
        if self.simulated:  # If simulating, the world will handle the robot's step
            self.world.on_step(step_duration)
            if self.gui:
                self.client_future(DRAW, self.world)
        else:  # Otherwise step the robot on its own
            self.robot.on_step(step_duration)
        self.step_count += 1
        return timer()-start

    def log_step_info(self):
        """ Log information about the current step. """
        log_object = {'type': 'step', 'elapsed': self.elapsed, 'step': self.step_count, 'robot': self.robot.to_dict()}
        if self._brain_log_contents.getvalue() != '':
            log_object.update({'brain_print': self._brain_log_contents.getvalue()})
            self._brain_log_contents.truncate(0)
            self._brain_log_contents.seek(0)
        self.log(log_object)

    def pause(self):  # Stops the currently running step thread, if it exists
        self.running = False
        if self._step_thread:
            self._step_thread.join()

    def stop(self):
        """ Called when the controller is stopped. """
        self.pause()
        self.brain['on_stop']()
        self.robot.on_stop()
        if self.log:  # Log position information after all steps have completed
            self.log_step_info()
        self.started = False
        self.stopped = True

    def shutdown(self):
        """ Called when the controller is shut down. """
        self.pause()
        self.brain['on_shutdown']()
        self.robot.on_shutdown()

    def failure(self):
        """ Called when the controller fails. """
        self.pause()
        self.started = False
        self.stopped = True
        try:
            self.robot.on_shutdown()  # Ignore any errors while trying to shutdown
        except Exception:
            pass
