from soar.gui.plot_window import PlotWindow
from soar.robot.pioneer import PioneerRobot
from soar.hooks import sim_completed
from soar.sim.geometry import Pose, normalize_angle_180, Point
from soar.robot.arcos import *

from threading import current_thread
from math import pi
from time import sleep

robot = PioneerRobot()


def calc_distance(sonars):
    s3, s4 = sonars[3], sonars[4]
    if s3 is None and s4 is None:
        return 1.5
    elif s3 is None:
        return s4
    elif s4 is None:
        return s3
    else:
        return (s3+s4)/2.0


#  This function is called when the brain is loaded
def on_load():
    print(current_thread())
    pass

#  This function is called when the start button is pushed
def on_start():
    robot.readings = []


#  This function is called every step_duration seconds. By default, it is called 10 times/second
def on_step(step_duration):
    distance = calc_distance(robot.sonars)
    print(distance)
    robot.readings.append(distance)
    robot.fv = 1.0*(distance-0.6)
    if abs(distance-0.6) < 0.001:
        sim_completed('hello')
    sleep(5.0)


# This function is called when the stop button is pushed
def on_stop():
    p = PlotWindow()
    p.plot(robot.readings)


# This function is called when the robot's controller is shut down
def on_shutdown():
    pass
