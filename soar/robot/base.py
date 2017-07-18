""" Soar v0.11.0 BaseRobot

Base robot class, intended to serve as a guideline and parent class for actually useful robots.
"""
from math import sin, cos

from soar.errors import SoarIOError
from soar.sim.geometry import Pose
from soar.sim.world import WorldObject


class BaseRobot(WorldObject):
    """ A base robot class, intended to be subclassed and overridden.

    Any robot usable in SoaR should implement all of this class's methods, as well as any required additional behavior.

    Attributes:
        type: (str): A human readable name for robots of this type.
        world: An instance of :class:`soar.sim.world.World` or a subclass of it, or ``None``, if the robot is real.
        simulated (bool): Any BaseRobot subclass should consider the robot to be simulated if this is ``True``, and real
                          otherwise.
        pos: An instance of :class:`soar.sim.geometry.Pose` representing the robot's ``(x, y, theta)`` position.
             In simulation, this is the actual position; on a real robot this may or may not be accurate.
        fv (float): Represents the robot's forward velocity in some units.
        rv (float): Represents the robot's rotational velocity in rad/s, where positive values correspond to
                    counterclockwise.
    """

    def __init__(self):
        WorldObject.__init__(self, do_draw=True, do_step=True)  # Robots are always drawn and stepped
        self.type = 'BaseRobot'
        self.simulated = False
        self.world = None
        self.pos = Pose(0, 0, 0)
        self._fv = 0.0
        self._rv = 0.0

    @property
    def fv(self):
        """ Get or set the robot's forward velocity in some units. """
        return self._fv

    @fv.setter
    def fv(self, value):
        self._fv = value

    @property
    def rv(self):
        """ Get or set the robot's rotational velocity in radians/second. """
        return self._rv

    @rv.setter
    def rv(self, value):
        self._rv = value

    def to_dict(self):
        """ Return a dictionary representation of the robot, usable for serialization. """
        return {'x_pos': self.pos[0], 'y_pos': self.pos[1], 't_pos': self.pos[2], 'fv': self.fv, 'rv': self.rv,
                'type': self.type}

    def move(self, pose):
        """ Move the robot to the specified x, y, theta position.

        Args:
            pose: An x, y, t Pose or 3-tuple-like object to move the robot to.
        """
        x, y, t = pose
        self.pos = Pose(x, y, t)

    def draw(self, canvas):
        """ Draw the robot on a canvas.

        Args:
            canvas: An instance of :class:`soar.gui.canvas.SoarCanvas`.
        """
        raise NotImplementedError

    def delete(self, canvas):
        """ Delete the robot from a canvas.

        Args:
            canvas: An instance of :class:`soar.gui.canvas.SoarCanvas`.
        """
        raise NotImplementedError

    def on_load(self):
        """ Called when the controller of the robot is loaded.

        The behavior of this method should differ depending on the value of ``self.simulated``; if it is ``False``, this
        method should be used to connect with the real robot. If a connection error occurs, a SoarIOError exception
        should be raised to notify the client that the error was not due to other causes.
        """
        raise SoarIOError('BaseRobot has no real interface to connect to')

    def on_start(self):
        """ Called when the controller of the robot is started. """
        pass

    def on_step(self, step_duration):
        """ Called when the controller of the robot undergoes a single step of a specified duration.

        For BaseRobot, this simply updates the robot's position in the world if it is simulated. Subclasses will
        typically have more complex ``on_step()`` methods.

        Args:
            step_duration (float): The duration of the step, in seconds.
        """
        if self.simulated:  # Updates the robot's pose in the world
            theta = self.pos.xyt_tuple()[2]
            d_x, d_y, d_t = cos(theta)*self.fv*step_duration, sin(theta)*self.fv*step_duration, self.rv*step_duration
            self.pos = self.pos.transform(Pose(d_x, d_y, d_t))

    def on_stop(self):
        """ Called when the controller of the robot is stopped. """
        pass

    def on_shutdown(self):
        """ Called when the controller of the robot is shutdown.

        If interacting with a real robot, the connection should be safely closed and reset for any later connections.
        """
        pass

    def on_failure(self):
        """ Called when the controller of the robot fails for whatever reason.

        Typically, this method should merely call on_shutdown; however if additional work needs to be done on a failure
        then this may be overridden.
        """
        self.on_shutdown()
