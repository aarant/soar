from soar.controller import sim_completed
from soar.robot.pioneer import PioneerRobot
from soar.gui.plot_window import PlotWindow
from soar.robot.arcos import *

robot = PioneerRobot()


#  This function is called when the brain is loaded
def on_load():
    if not robot.simulated:
        robot.arcos.send_command(SONAR, 0)


#  This function is called when the start button is pushed
def on_start():
    robot.i = 0


#  This function is called every step_duration seconds. By default, it is called 10 times/second
def on_step(step_duration):
    ai1, ai3, ai5, ai7 = robot.analogs
    robot.set_analog_voltage(robot.i)
    print(robot.i)
    robot.i += 1
    robot.i %= 11


# This function is called when the stop button is pushed
def on_stop():
    pass


# This function is called when the robot's controller is shut down
def on_shutdown():
    pass
