""" Soar BaseRobot class, intended as a parent class for nontrivial/useful robots.

All robots usable in Soar should either subclass from BaseRobot and re-implement its methods, or, if `fv` or `rv`,
etc are not needed, subclass from :class:`soar.sim.world.WorldObject` and re-implement BaseRobot's methods.
"""
from math import sin, cos

from soar.errors import SoarError, SoarIOError
from soar.sim.geometry import Pose
from soar.sim.world import WorldObject


class BaseRobot(WorldObject):
    """ A base robot class, intended to be subclassed and overridden.

    Any robot usable in SoaR should implement all of this class's methods, as well as any required additional behavior.

    Attributes:
        type: (str): A human readable name for robots of this type.
        world: The instance of :class:`soar.sim.world.World` (or a subclass) in which the robot resides, or `None`,
               if the robot is real.
        simulated (bool): Any BaseRobot subclass should consider the robot to be simulated if this is `True`, and real
                          otherwise. By default, it is `False`.
        pos: An instance of :class:`soar.sim.geometry.Pose` representing the robot's `(x, y, theta)` position.
             In simulation, this is the actual position; on a real robot this may be determined through other means.

    Args:
        **options: Arbitrary keyword arguments. This may include Tkinter keywords passed to the `WorldObject`
            constructor, or robot options also supported as arguments to `set_robot_options`.
    """

    def __init__(self, **options):
        WorldObject.__init__(self, do_draw=True, do_step=True, **options)  # Robots are always drawn and stepped
        self.type = 'BaseRobot'
        self.simulated = False
        self.world = None
        self.pos = Pose(0, 0, 0)
        self.__fv = 0.0
        self.__rv = 0.0

    def set_robot_options(self, **options):
        """ Set one or many keyworded, robot-specific options. Document these options here.

        Args:
            **options: `BaseRobot` does not support any robot options.
        """
        pass

    @property
    def fv(self):
        """ `float` The robot's forward velocity.

         The units of this value may be anything, and should be interpreted by a subclass as it wishes.
         """
        return self.__fv

    @fv.setter
    def fv(self, value):
        self.__fv = value

    @property
    def rv(self):
        """ `float` The robot's rotational velocity in radians/second. """
        return self.__rv

    @rv.setter
    def rv(self, value):
        self.__rv = value

    def to_dict(self):
        """ Return a dictionary representation of the robot, usable for serialization. """
        return {'x_pos': self.pos[0], 'y_pos': self.pos[1], 't_pos': self.pos[2], 'fv': self.fv, 'rv': self.rv,
                'type': self.type}

    def move(self, pose):
        """ Move the robot to the specified `(x, y, theta)` pose.

        Args:
            pose: An :class:`soar.sim.geometry.Pose` or 3-tuple-like object to move the robot to.
        """
        x, y, t = pose
        self.pos = Pose(x, y, t)

    def draw(self, canvas):
        """ Draw the robot on a canvas.

        Args:
            canvas: An instance of :class:`soar.gui.canvas.SoarCanvas`.
        """
        raise SoarError('BaseRobot has no drawing method')

    def delete(self, canvas):
        """ Delete the robot from a canvas.

        Args:
            canvas: An instance of :class:`soar.gui.canvas.SoarCanvas`.
        """
        raise SoarError('BaseRobot has no canvas deletion method')

    def on_load(self):
        """ Called when the controller of the robot is loaded.

        The behavior of this method should differ depending on the value of `simulated`; if it is `False`, this
        method should be used to connect with the real robot. If a connection error occurs, a
        :class:`soar.errors.SoarIOError` should be raised to notify the client that the error was not due to other
        causes.
        """
        raise SoarIOError('BaseRobot has no real interface to connect to')

    def on_start(self):
        """ Called when the controller of the robot is started. 
        
        This method is called exactly once per controller session--when the user first starts or steps the controller.
        """
        pass

    def on_step(self, step_duration):
        """ Called when the controller of the robot undergoes a single step of a specified duration.

        For BaseRobot, this simply updates the robot's position in the world if it is simulated. Subclasses will
        typically have more complex `on_step()` methods.

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
