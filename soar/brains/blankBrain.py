from soar.robot.pioneer import PioneerRobot
from soar.gui.plugin import *

robot = PioneerRobot()


#  This function is called when the brain is loaded
def on_load():
    pass


#  This function is called when the start button is pushed
def on_start():
    pass


#  This function is called every step_duration seconds. By default, it is called 10 times/second
def on_step(step_duration):
    pass


# This function is called when the stop button is pushed
def on_stop():
    pass


# This function is called when the robot's controller is shut down
def on_shutdown():
    pass
