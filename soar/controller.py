from time import sleep

from soar import client
import traceback

class ControllerError(Exception):
    """ Raised when an issue arises in either the simulated or real controller """


class Controller:
    def __init__(self, robot, brain, world=None, tick_duration=0.1):
        self.robot = robot
        self.brain = brain
        self.world = world
        self.tick_duration = tick_duration
        self.running = False
        self.started = False

    def on_load(self):
        """ Called when the controller is first loaded """
        self.brain.print = client.output  # Capture the brain's output
        if self.world:  # If there is a world, we are simulating, and potentially drawing it
            self.robot.move(self.world.initial_position)  # TODO
            self.world.add(self.robot)
            if not client.headless:
                client.message(client.draw, self.world)
        try:
            self.robot.on_load()
        except ControllerError as e:
            client.output(e)
            client.message(client.controller_failure)
        self.brain.on_load()

    def on_start(self):
        """ Called when the controller is started/unpaused """
        if not self.started:
            self.robot.on_start()
            self.brain.on_start()
            self.started = True
        self.running = True
        while self.running:
            self.on_step()
            sleep(self.tick_duration)

    def on_step(self):
        """ Called when the controller undergoes a single step """
        if not self.started:
            self.robot.on_start()
            self.brain.on_start()
            self.started = True
        self.robot.on_step()
        self.brain.on_step()  # Perform a single step on the brain
        if self.world:
            self.world.tick(self.tick_duration)
            if not client.headless:
                client.message(client.draw, self.world)

    def on_stop(self):
        """ Called when the controller is stopped """
        self.running = False
        self.started = False
        self.robot.on_stop()
        self.brain.on_stop()

    def on_shutdown(self):
        """ Called when the controller is shut down """
        self.robot.on_shutdown()
        self.brain.on_shutdown()
        #if self.world and not client.headless:
            #client.message(client.draw, 'CLOSE_SIM')
