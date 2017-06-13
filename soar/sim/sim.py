from time import sleep

from soar.main import client
from soar.main.messages import *
from soar.geometry import *


class Simulator:
    def __init__(self, robot, brain, world, headless):
        self.robot = robot
        self.brain = brain
        self.world = world
        self.headless = headless
        self.running = False
        self.started = False
        self.tick = 0.1  # 1 decisecond

    def on_load(self):
        self.robot.pos = Pose(self.world.initial_position[0], self.world.initial_position[1], 0.0)
        self.robot.world = self.world
        if not self.headless:
            client.message(DRAW, self.world, self.robot)
        self.brain.on_load()

    def on_step(self):
        self.brain.on_step()
        self.robot.tick(self.tick)
        if not self.headless:
            client.message(DRAW, self.robot)

    def on_start(self, single_step=False):
        if not self.started:
            self.brain.on_start()
            self.started = True
        self.running = True
        if single_step:
            self.on_step()
            return
        while self.running:
            self.on_step()
            sleep(self.tick)

    def on_stop(self):
        self.running = False
        self.started = False
        self.brain.on_stop()
