from soar.controller import sim_completed
from soar.robot.pioneer import PioneerRobot
from soar.gui.plot_window import PlotWindow
from soar.robot.arcos import *

robot = PioneerRobot()


#  This function is called when the brain is loaded
def on_load():
    robot.arcos.send_command(SONAR, 0)


#  This function is called when the start button is pushed
def on_start():
    robot.fv = -1.0
    print(robot.fv)


#  This function is called every step_duration seconds. By default, it is called 10 times/second
def on_step(step_duration):
    print(robot.pos[0], robot.pos[1])


# This function is called when the stop button is pushed
def on_stop():
    pass


# This function is called when the robot's controller is shut down
def on_shutdown():
    pass
