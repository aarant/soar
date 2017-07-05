from math import sin, cos
from soar.geometry import Pose
from soar.controller import SoarIOError


class BaseRobot:
    """ A base robot class, intended to be subclassed and overridden

    Any robot usable in SoaR should implement all of this class's methods, as well as any required additional behavior

    Attributes:
        world: An instance of BaseWorld or a subclass of it, or None. Any BaseRobot subclass should consider the robot
               to be real if this is None, and simulated otherwise
        pos: An instance of Pose representing the robot's x, y, theta position. In simulation, this is the actual
             position; on a real robot this may or may not be accurate
        fv (float): Represents the robot's forward velocity in some units
        rv (float): Represents the robot's rotational velocity in rad/s, where positive values correspond to
                    counterclockwise
    """

    def __init__(self):
        self.world = None
        self.pos = Pose(0, 0, 0)
        self.fv = 0.0
        self.rv = 0.0

    def tick(self, duration):
        """ Performs a tick of some duration on the robot, updating its internal pose

        Args:
            duration (float): The duration of the tick in seconds
        """
        theta = self.pos.xyt_tuple()[2]
        d_x, d_y, d_t = cos(-theta)*self.fv*duration, sin(-theta)*self.fv*duration, self.rv*duration  # TODO: Negative theta, move this into on_step
        self.pos = self.pos.transform(Pose(d_x, d_y, d_t))

    def draw(self, canvas):
        """ Draw the robot on a canvas with units

        Args:
            canvas: An instance of SoarCanvas, supporting all of Tk's Canvas methods, but measured in units, not pixels
        """
        raise NotImplementedError

    def delete(self, canvas):
        """ Delete the robot from a canvas

        Args:
            canvas: An instance of SoarCanvas, supporting all of Tk's Canvas methods, but measured in units, not pixels
        """
        raise NotImplementedError

    def on_load(self):
        """ Called when the controller of the robot is loaded

        The behavior of this method should differ depending on the value of self.world; if it is None, this method
        should be used to connect with the real robot. If a connection error occurs, a SoarIOError exception can be
        raised to trigger a softer error for the client
        """
        raise SoarIOError('BaseRobot has no real interface to connect to')

    def on_start(self):
        """ Called when the controller of the robot is started """
        pass

    def on_step(self):
        """ Called when the controller of the robot undergoes a single step """
        pass

    def on_stop(self):
        """ Called when the controller of the robot is stopped"""
        pass

    def on_shutdown(self):
        """ Called when the controller of the robot is shutdown

        If interacting with a real robot, the connection should be safely closed and reset for any later connections
        """
        pass
