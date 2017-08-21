from soar.robot.base import BaseRobot
from soar.gui.plot_window import PlotWindow
from soar.hooks import sim_completed
from soar.sim.world import Polygon

robot = BaseRobot(polygon=Polygon([(-0.5, 0.5), (0.5, 0.5), (0.5, -0.5), (-0.5, -0.5)], tags='base'))


#  This function is called when the brain is loaded
def on_load():
    pass


#  This function is called when the start button is pushed
def on_start():
    print(robot.polygon.tags)
    pass


#  This function is called every step_duration seconds. By default, it is called 10 times/second
def on_step(step_duration):
    robot.fv = 1.0
    pass


# This function is called when the stop button is pushed
def on_stop():
    pass


# This function is called when the robot's controller is shut down
def on_shutdown():
    pass
