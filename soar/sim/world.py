# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/sim/world.py
""" Soar World and WorldObject classes/subclasses, for simulating and drawing worlds. """
import random
from math import sin, cos, pi

from soar.sim.geometry import Point, LineSegment, PointCollection


class WorldObject:
    """ An object that can be simulated and drawn in a :class:`soar.sim.world.World` on a
    :class:`soar.gui.canvas.SoarCanvas`.

    Classes that are designed to work with a World in Soar may either subclass from this class or implement its methods
    and attributes to be considered valid.

    Attributes:
        do_draw (bool): Used by a `World` to decide whether to draw the object on a canvas.
        do_step (bool): Used by a `World` to decide whether to step the object in simulation.

    Args:
        do_draw (bool): Sets the value of the `do_draw` attribute.
        do_step (bool): Sets the value of the `do_step` attribute.
        dummy (bool): Whether the object is a dummy--that is, not intended to be drawn or stepped, but used for
            some intermediate calcuation (usually collision).
        **options: Tkinter options. This may include 'tags', for drawing on a canvas, line thickness, etc.
    """
    _unique_id = 0

    def __init__(self, do_draw, do_step, dummy=False, **options):  # TODO: Replace do_draw, do_step with static, dummy, etc in 2.0
        self.do_draw = do_draw
        self.do_step = do_step
        self.dummy = dummy
        self.options = options
        if dummy:
            self.tags = None
        elif 'tags' in options:
            self.tags = options['tags']
        else:  # If tags are not specified, make sure this object has a unique tag
            self.tags = self.__class__.__name__ + str(self.__class__._unique_id)
            self.__class__._unique_id += 1
        self.options['tags'] = self.tags

    def draw(self, canvas):
        """ Draw the object on a canvas.

        Args:
            canvas: A Tkinter Canvas or a subclass, typically a :class:`soar.gui.canvas.SoarCanvas`,
                on which the object will be drawn.
        """
        pass

    def delete(self, canvas):  # TODO: Deprecate this in 2.0
        """ Delete the object from a canvas.

        Args:
            canvas: A Tkinter Canvas or a subclass, typically a :class:`soar.gui.canvas.SoarCanvas`, from which the
                object will be deleted.
        """
        if not self.dummy:
            canvas.delete(self.tags)

    def on_step(self, step_duration):
        """ Simulate the object for a step of a specified duration.

        Args:
            step_duration: The duration of the step, in seconds.
        """
        pass

    def collision(self, other, eps=1e-8):
        """ Determine whether two `WorldObject` (s) collide.

        Objects that subclass `WorldObject` should implement collision detection for every applicable class from which
        they inherit.

        Args:
            other: A supported `WorldObject` subclass with which this object could potentially collide.
            eps (float, optional): The epsilon within which to consider a collision to have occurred, different for
                each subclass.

        Returns:
            list: A list of `(x, y)` tuples consisting of all the collision points with `other`, or `None`
            if there weren't any.
        """
        pass


class Wall(WorldObject, LineSegment):
    """ A straight wall with Tk options and collision detection.

    Note that these walls are infinitely thin, so on-edge collision cannot occur.

    Args:
        p1: An `(x, y)` tuple or a :class:`soar.sim.geometry.Point` as the first endpoint of the wall.
        p1: An `(x, y)` tuple or a :class:`soar.sim.geometry.Point` as the second endpoint of the wall.
        eps (float): The epsilon within which to consider a wall vertical or horizontal.
        **options: Tkinter options.
    """
    def __init__(self, p1, p2, eps=1e-8, **options):
        WorldObject.__init__(self, do_draw=True, do_step=False, **options)
        LineSegment.__init__(self, p1, p2, eps)
        if 'width' not in options:
            self.options['width'] = 2.0  # By default walls are 2 pixels wide

    def draw(self, canvas):
        """ Draw the object on a canvas.

        Args:
            canvas: A Tkinter Canvas or a subclass, typically a :class:`soar.gui.canvas.SoarCanvas`, on which the
                object will be drawn.
        """
        if not self.dummy:
            canvas.create_line(self.p1[0], self.p1[1], self.p2[0], self.p2[1], **self.options)
            self.do_draw = False  # For a line drawn each frame, subclass this class

    def collision(self, other, eps=1e-8):
        """ Determine whether two walls intersect.

        Args:
            other: A `Wall`, or other `LineSegment` subclass.
            eps (float): The epsilon within which to consider two parallel lines the same line.

        Returns:
            A list of `(x, y)` tuples consisting of the intersection(s), or `None` if the segments do not intersect.
        """
        if isinstance(other, LineSegment):
            intersects = LineSegment.intersection(self, other, eps)
            return intersects


class Ray(Wall):
    """ A ray of a specified length, origin and direction.

    Args:
        pose: An `(x, y, theta)` tuple or :class:`soar.sim.geometry.Pose` as the origin of the ray.
        length (float): The length of the ray.
        **options: Tkinter options.
    """
    def __init__(self, pose, length, eps=1e-8, **options):
        x0, y0, theta = pose
        x1, y1 = x0+cos(theta)*length, y0+sin(theta)*length
        Wall.__init__(self, (x0, y0), (x1, y1), eps=eps, **options)
        self.length = length


class Polygon(PointCollection, WorldObject):
    """ A movable polygon with Tkinter options.

    Args:
        points: A list of `(x, y)` tuples or :class:`soar.sim.geometry.Point`.
        center: An `(x, y)` tuple or :class:`soar.sim.geometry.Point` as the pivot or center of the collection.
        **options: Tkinter options.
    """
    def __init__(self, points, center=None, **options):
        PointCollection.__init__(self, points, center)
        WorldObject.__init__(self, do_draw=True, do_step=False, **options)

    @property
    def borders(self):  # Build perimeter lines for collision detection
        return [LineSegment(self.points[i-1], self.points[i]) for i in range(len(self.points))]

    def draw(self, canvas):
        """ Draw the object on a canvas.

        Args:
            canvas: A Tkinter Canvas or a subclass, typically a :class:`soar.gui.canvas.SoarCanvas`, on which the
                object will be drawn.
        """
        if not self.dummy:
            flat_points = [p for pair in self.points for p in pair]
            canvas.create_polygon(*flat_points, **self.options)
            self.do_draw = False

    def collision(self, other, eps=1e-8):
        """ Determine whether the polygon intersects with another `WorldObject`.

        Args:
            other: Either a `Polygon` or a `Wall` as the other object.
            eps (float, optional): The epsilon within which to consider a collision to have occurred.
        """
        if isinstance(other, Polygon):  # Might be able to do this better I suppose
            intersects = []
            for i in self.borders:
                for j in other.borders:
                    line_intersects = i.intersection(j, eps=eps)
                    if line_intersects:
                        intersects.extend(line_intersects)
            return intersects if len(intersects) > 0 else None
        elif isinstance(other, Wall):
            intersects = []
            for i in self.borders:
                line_intersects = i.intersection(other, eps=eps)
                if line_intersects:
                    intersects.extend(line_intersects)
            return intersects if len(intersects) > 0 else None


class Block(Polygon):
    """ An arbitrarily thick wall centered on a line.

    Useful when infinitely-thin lines are causing issues with collision detection.

    Args:
        p1: An `(x, y)` tuple or :class:`soar.sim.geometry.Point` as the first endpoint of the line segment.
        p1: An `(x, y)` tuple or :class:`soar.sim.geometry.Point` as the second endpoint of the line segment.
        thickness (float): The thickness of the block to expand out from the line on which it is centered.
        **options: Tkinter options.
    """
    def __init__(self, p1, p2, thickness=0.002, **options):
        self.thickness = thickness
        # Build the perimeter of the wall as points
        p1 = Point(*p1)
        p2 = Point(*p2)
        mid = p1.midpoint(p2)
        points = []
        for endpoint in [p1, p2]:
            temp = endpoint.scale(1.0+thickness/endpoint.distance(mid), mid)
            pivot = temp.midpoint(endpoint)
            temp2 = temp.rotate(pivot, -pi / 2)
            temp = temp.rotate(pivot, pi/2)
            points.extend([temp, temp2])
        Polygon.__init__(self, points, center=None, **options)
        if 'fill' not in options:
            options.update({'fill': 'black'})

    @property
    def borders(self):  # Build perimeter lines dynamically
        return [Wall(self.points[i-1], self.points[i], **self.options) for i in range(len(self.points))]

    def draw(self, canvas):
        """ Draw the object on a canvas.

        Args:
            canvas:  A Tkinter Canvas or a subclass, typically a :class:`soar.gui.canvas.SoarCanvas`, on which the
                object will be drawn.
        """
        if not self.dummy:
            for wall in self.borders:
                wall.draw(canvas)
            self.do_draw = False


class World:
    """ A simulated world containing objects that can be simulated stepwise and drawn on a
    :class:`soar.gui.canvas.SoarCanvas`.

    Attributes:
        dimensions (tuple): An `(x, y)` tuple representing the worlds length and height.
        initial_position: An `(x, y, theta)` or :class:`soar.sim.geometry.Pose` representing the robot's
                          initial position in the world.
        objects (list): A list of (`WorldObject`, layer) tuples containing all of the world's objects.
        layer_max (int): The highest layer currently allocated to an object in the world.
        canvas: An instance of :class:`soar.gui.canvas.SoarCanvas`, if the world is being drawn, otherwise `None`.

    Args:
        dimensions (tuple): An `(x, y)` tuple representing the worlds length and height.
        initial_position: An `(x, y, theta)` or :class:`soar.sim.geometry.Pose` representing the robot's
                          initial position in the world.
        objects (list): The initial `WorldObject` (s) to add to the world
    """
    def __init__(self, dimensions, initial_position, objects=None):
        self.dimensions = dimensions
        self.initial_position = initial_position
        self.objects = []
        self.layer_max = -1
        self.canvas = None
        if objects:
            for obj in objects:
                self.add(obj)
        # Build boundary walls
        x, y = self.dimensions
        for wall in [Wall((0, 0), (x, 0)), Wall((x, 0), (x, y)), Wall((x, y), (0, y)), Wall((0, y), (0, 0))]:
            self.add(wall)

    def __getitem__(self, item):
        """ Iterating over a world is the same as iterating over the (sorted) object list. """
        return self.objects[item][0]

    def add(self, obj, layer=None):
        """ Add an object to the world, with an optional layer specification.

        Args:
            obj: A `WorldObject` (or a subclass instance).
            layer (int): The layer on which the object is to be drawn. Objects are drawn in order from smallest to
                largest layer. If this argument is `None`, the object's layer will be set to one higher than the
                highest layer in the objects list.
        """
        if layer is None:
            layer = self.layer_max + 1
            self.layer_max += 1
        elif layer > self.layer_max:
            self.layer_max = layer
        self.objects.append((obj, layer))
        self.objects.sort(key=lambda tup: tup[1])  # Sort the list of objects by layer priority
        setattr(obj, 'world', self)  # Ensure that every object has a back reference to the world

    def draw(self, canvas):
        """ Draw the world on a canvas.

        Objects are drawn in order from the lowest to highest layer if their `do_draw` attribute is True.

        Args:
            canvas: The :class:`soar.gui.canvas.SoarCanvas` on which to draw the world. How each object is drawn is up
                to the object.
        """
        self.canvas = canvas
        for obj, layer in self.objects:  # The list of objects is already sorted by layer
            if obj.do_draw:
                obj.draw(canvas)

    def delete(self, canvas):  # TODO: Deprecate this in 2.0
        """ Delete the world from a canvas, by deleting each object at a time.

        Args:
            canvas: The :class:`soar.gui.canvas.SoarCanvas` from which to delete.
        """
        for obj, layer in self.objects:
            if obj.do_draw:  # Objects only need to be deleted if they were drawn
                obj.delete(canvas)

    def on_step(self, step_duration):
        """ Perform a single step on the world's objects.

        Args:
            step_duration (float): The duration of the step in seconds.
        """
        for obj, layer in self.objects:
            if obj.do_step:
                obj.on_step(step_duration)

    def find_all_collisions(self, obj, eps=1e-8, condition=None):
        """ Finds all the collisions of a `WorldObject` subclass with objects in the world.

        Args:
            obj: A `WorldObject` or subclass instance. Objects in the world must know how to collide with it.
            eps (float, optional): An optional epsilon within which to consider a collision to have occurred. What that
                means differs between `WorldObject` subclasses.
            condition (optional): A function to apply to each object in the world that must be `True` in order for it
                to be considered.

        Returns:
            list: A list of `(world_obj, p)` tuples, where `world_obj` is the object that collided and `p` is the
            :class:`soar.sim.geometry.Point` at which the collision occurred. If multiple collision points occurred with
            the same object, each will be listed separately. If no collisions occurred, returns `None`.
        """
        collisions = []
        for world_obj in self:
            if condition is None or condition(world_obj):  # True if no condition or if the object matches
                obj_collisions = world_obj.collision(obj, eps)
                if obj_collisions:
                    for single_collision in obj_collisions:
                        collisions.append((world_obj, single_collision))
        return collisions if len(collisions) > 0 else None

