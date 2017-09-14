# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/robot/base.py
""" Soar BaseRobot class, intended as a parent class for nontrivial/useful robots.

All robots usable in Soar should either subclass from BaseRobot or, if this is not possible, reproduce its behaviors.
"""
from math import sin, cos

from soar.errors import SoarIOError
from soar.sim.geometry import Point, Pose
from soar.sim.world import WorldObject, Polygon, Wall


class BaseRobot(WorldObject):
    """ A base robot class, intended to be subclassed and overridden.

    Any robot usable in SoaR should supplement or re-implement this class' methods with the desired behavior.

    Attributes:
        type (str): A human readable name for robots of this type.
        world: The instance of :class:`soar.sim.world.World` (or a subclass) in which the robot resides, or `None`,
               if the robot is real.
        simulated (bool): Any BaseRobot subclass should consider the robot to be simulated if this is `True`, and real
                          otherwise. By default, it is `False`.
        pose: An instance of :class:`soar.sim.geometry.Pose` representing the robot's `(x, y, theta)` position.
            In simulation, this is the actual position; on a real robot this may be determined through other means.
        polygon: A :class:`soar.sim.world.Polygon` that defines the boundaries of the robot and is used for collision.
        fv (float): The robot's current translational velocity, in arbitrary units. Positive values indicate movement
            towards the front of the robot, and negative values indicate movement towards the back.
        rv (float): The robot's current rotational velocity, in radians/second. Positive values indicate
            counterclockwise rotation (when viewed from above), and negative values indicate clockwise rotation.

    Args:
        polygon: A :class:`soar.sim.world.Polygon` that defines the boundaries of the robot and is used for collision.
        **options: Arbitrary keyword arguments. This may include Tkinter keywords passed to the `WorldObject`
            constructor, or robot options supported as arguments to `set_robot_options`.
    """

    def __init__(self, polygon, **options):
        WorldObject.__init__(self, do_draw=True, do_step=True, **options)  # Robots are always drawn and stepped
        self.type = 'BaseRobot'
        self.simulated = True
        self.world = None
        self.pose = Pose(0, 0, 0)
        self.fv = 0.0
        self.rv = 0.0
        # Re-instantiate the polygon with the robot's tags
        del polygon.options['tags']
        self.polygon = Polygon(polygon.points, polygon.center, tags=self.tags, **polygon.options)
        # The maximum radius, used for pushing the robot back before a collision
        self._radius = sorted([self.polygon.center.distance(vertex) for vertex in self.polygon])[-1]

    def set_robot_options(self, **options):
        """ Set one or many keyworded, robot-specific options. Document these options here.

        Args:
            **options: `BaseRobot` does not support any robot options.
        """
        pass

    @property
    def pos(self):  # TODO: This property exists only for backwards compatibility. Deprecate by 2.0.
        return self.pose

    @pos.setter
    def pos(self, t):  # TODO: This property exists only for backwards compatibility. Deprecate by 2.0.
        self.pose = t

    def to_dict(self):
        """ Return a dictionary representation of the robot, usable for serialization. """
        return {'x_pos': self.pose[0], 'y_pos': self.pose[1], 't_pos': self.pose[2], 'fv': self.fv, 'rv': self.rv,
                'type': self.type}

    def move(self, pose):
        """ Move the robot to the specified `(x, y, theta)` pose.

        Args:
            pose: An :class:`soar.sim.geometry.Pose` or 3-tuple-like object to move the robot to.
        """
        x, y, t = pose
        current_theta = self.pose[2]
        self.pose = Pose(x, y, t)
        self.polygon.recenter(self.pose)
        self.polygon.rotate(self.polygon.center, t - current_theta)

    def collision(self, other, eps=1e-8):
        """ Determine whether the robot collides with an object.

        Supported objects include other robots, and subclasses of :class:`soar.sim.world.Polygon` and
        :class:`soar.sim.world.Wall`.

        Args:
            other: A supported `WorldObject` subclass with which this object could potentially collide.
            eps (float, optional): The epsilon within which to consider a collision to have occurred, different for
                each subclass.

        Returns:
            list: A list of `(x, y)` tuples consisting of all the collision points with `other`, or `None`
            if there weren't any.
        """
        if isinstance(other, BaseRobot):  # Dispatch to collisions between robot polygons
            return self.polygon.collision(other.polygon, eps=eps)
        elif isinstance(other, Polygon) or isinstance(other, Wall):
            return self.polygon.collision(other, eps=eps)

    def draw(self, canvas):
        """ Draw the robot on a canvas.

        Canvas items are preserved. If drawn more than once on the same canvas, the item will be moved and not redrawn.

        Args:
            canvas: An instance of :class:`soar.gui.canvas.SoarCanvas`.
        """
        try:  # Try and find the drawn polygon on the canvas, in case it already exists
            canvas_poly = canvas.find_withtag(self.tags)[0]
        except IndexError:  # If no such item exists, draw it for the first time
            self.polygon.draw(canvas)
        else:
            # Remap metered coordinates to pixel coordinates, and change the canvas polygon
            coords = canvas.remap_coords([p for pair in self.polygon for p in pair])
            canvas.coords(canvas_poly, coords)

    def delete(self, canvas):  # TODO: Deprecate this in 2.0
        """ Delete the robot from a canvas.

        Args:
            canvas: An instance of :class:`soar.gui.canvas.SoarCanvas`.
        """
        self.polygon.delete(canvas)

    def on_load(self):
        """ Called when the controller of the robot is loaded.

        The behavior of this method should differ depending on the value of `simulated`; if it is `False`, this
        method should be used to connect with the real robot. If a connection error occurs, a
        :class:`soar.errors.SoarIOError` should be raised to notify the client that the error was not due to other
        causes.
        """
        if not self.simulated:
            raise SoarIOError('BaseRobot has no real interface to connect to')

    def on_start(self):
        """ Called when the controller of the robot is started. 
        
        This method will always be called by the controller at most once per controller session, before the first step.
        """
        pass

    def on_pause(self):
        """ Called when the controller is paused. """
        pass

    def on_step(self, step_duration):
        """ Called when the controller of the robot undergoes a single step of a specified duration.

        For BaseRobot, this tries to perform an integrated position update based on the forward and rotational
        velocities. If the robot cannot move to the new position because there is an object in its way, it will be moved
        to a safe space just before it would have collided.

        Subclasses will typically have more complex `on_step()` methods, usually with behavior for stepping
        non-simulated robots.

        Args:
            step_duration (float): The duration of the step, in seconds.
        """
        if self.simulated:  # Do the simulated move update (with collision preemption)
            # Try and make sure that the robot can actually move to its new location
            # Integrate over the path, making the new position at the end of the arc
            theta = self.pose[2]
            d_t = self.rv*step_duration
            new_theta = theta+d_t
            if self.rv != 0:
                d_x = self.fv*(sin(new_theta)-sin(theta))/self.rv
                d_y = self.fv*(cos(theta)-cos(new_theta))/self.rv
            else:
                d_x, d_y = self.fv*cos(theta)*step_duration, self.fv*sin(theta)*step_duration
            new_pos = self.pose.transform((d_x, d_y, d_t))
            # Build a dummy wall between the old and new position and check if it collides with anything
            w = Wall(self.pose.point(), new_pos.point(), dummy=True)
            collisions = self.world.find_all_collisions(w, condition=lambda obj: obj is not self)
            if collisions:  # If there were collisions, push the robot to a safe distance from the closest one
                collisions.sort(key=lambda tup: self.pose.distance(tup[1]))
                safe_point = Point(*collisions[0][1])
                offset = Point(self._radius, 0.0).rotate((0, 0), new_pos[2])
                safe_point = safe_point.sub(offset)
                new_pos = Pose(safe_point.x, safe_point.y, new_pos[2])

            self.pose = new_pos
            self.polygon.recenter(new_pos)
            self.polygon.rotate(self.polygon.center, d_t)

    def on_stop(self):
        """ Called when the controller of the robot is stopped. """
        pass

    def on_shutdown(self):
        """ Called when the controller of the robot is shutdown.

        If interacting with a real robot, the connection should be safely closed and reset for any later connections.
        """
        pass
