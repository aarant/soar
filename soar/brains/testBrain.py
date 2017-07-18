from soar.gui.plot_window import PlotWindow
from soar.controller import sim_completed
from soar.robot.pioneer import PioneerRobot

robot = PioneerRobot()


#  This function is called when the brain is loaded
def on_load():
    print('Brain on_load() called.')


#  This function is called when the start button is pushed
def on_start():
    robot.readings = []
    print('Brain on_start() called.')


#  This function is called every step_duration seconds. By default, it is called 10 times/second
def on_step(step_duration):
    print('Brain on_step() called.')
    distance = robot.sonars[3]
    robot.readings.append(distance)
    if abs(distance-0.6) < 0.001:
        sim_completed()
    robot.fv = distance-0.6


# This function is called when the stop button is pushed
def on_stop():
    p = PlotWindow()
    p.plot(robot.readings)
    p.plot(robot.readings[::-1])
    print('Brain on_stop() called.')


# This function is called when the robot's controller is shut down
def on_shutdown():
    print('Brain on_shutdown() called.')
