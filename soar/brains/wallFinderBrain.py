from soar.robot.pioneer import PioneerRobot
from soar.gui.plugin import *
from soar.gui.plotWindow import PlotWindow

robot = PioneerRobot()


#  This function is called when the brain is loaded
def on_load():
    pass


#  This function is called when the start button is pushed
def on_start():
    robot.readings = []


#  This function is called every step_duration seconds. By default, it is called 10 times/second
def on_step(step_duration):
    # read in the sonar readings from the robot.
    # s will be a list of 8 values, with the value at index
    # 0 representing the left-most sonar
    s = robot.get_sonars()

    # print the reading from the central sonar
    distance = s[3]
    # print(s[3])
    robot.readings.append(distance)

    # BANG BANG
    if distance > 0.6:
        velocity = 1.0
    else:
        velocity = -1.0

    # PROPORTIONAL
    k = 2.5
    velocity = k * (distance - 0.6)
    robot.set_forward_velocity(velocity)


# This function is called when the stop button is pushed
def on_stop():
    PlotWindow(toplevel=Toplevel).plot(robot.readings)


# This function is called when the robot's controller is shut down
def on_shutdown():
    pass