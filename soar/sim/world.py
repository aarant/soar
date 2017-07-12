""" World and WorldObject classes/subclasses, for simulating and drawing worlds """

import uuid

import numpy as np

from soar.sim.geometry import PointCollection


class WorldObject:
    """ An object that can be simulated and drawn in a :class:`soar.sim.world.World` on a
    :class:`soar.gui.canvas.SoarCanvas`

    Classes that are designed to work with a World in Soar may either subclass from this class or implement its methods
    and attributes to be considered valid

    Attributes:
        do_draw (bool): Used by a World instance to decide whether to draw the object on a canvas
        do_step (bool): Used by a World instance to decide whether to step the object in simulation

    Args:
        do_draw (bool): Sets the value of the do_draw attribute
        do_step (bool): Sets the value of the do_step attribute
        **options: Tk options
    """
    def __init__(self, do_draw, do_step, **options):
        self.do_draw = do_draw
        self.do_step = do_step
        self.options = options
        if 'tags' in options:
            self.tags = options['tags']
        else:  # If tags are not specified, make sure this object has a (hopefully) unique tag
            self.tags = uuid.uuid4().hex

    def draw(self, canvas):
        """ Draws the object on a canvas

        Args:
            canvas: A Tk Canvas or a subclass, typically a SoarCanvas, on which the object will be drawn
        """
        pass

    def delete(self, canvas):
        """ Deletes the object from a canvas

        Args:
            canvas: A Tk Canvas or a subclass, typically a SoarCanvas, on which the object will be drawn
        """
        canvas.delete(self.tags)

    def on_step(self, step_duration):
        """ Simulates the object for a step of a specified duration

        Args:
            step_duration: The duration of the step, in seconds
        """
        pass


class Polygon(PointCollection, WorldObject):
    """ A movable polygon with Tk options

    Args:
        points: A list of x, y tuples or Points
        center: An x, y tuple or Point as the pivot or center of the collection
        **options: Tk options
    """
    def __init__(self, points, center=None, **options):
        PointCollection.__init__(self, points, center)
        WorldObject.__init__(self, do_draw=True, do_step=False, **options)

    def draw(self, canvas):
        flat_points = []
        for p in self.points:
            flat_points.extend([p.x, p.y])
        canvas.create_polygon(*flat_points, **self.options)


class Line(WorldObject):
    """ A line segment with Tk options and collision detection

    Args:
        p1: An x, y tuple or an instance of :class:`soar.sim.geometry.Point` as the first endpoint of the line segment
        p1: An x, y tuple or an instance of :class:`soar.sim.geometry.Point` as the second endpoint of the line segment
        **options: Tk options
    """
    def __init__(self, p1, p2, **options):
        WorldObject.__init__(self, do_draw=True, do_step=False, **options)
        self.p1 = p1
        self.p2 = p2
        if 'width' not in options:
            self.options.update({'width': 2.0})
        self.redraw = True
        x0, y0 = p1
        x1, y1 = p2
        if x0 == x1:
            self.equ = [1, 0]
            self.c = x0
        elif y0 == y1:
            self.equ = [0, 1]
            self.c = y0
        else:
            m = (y1-y0)/(x1-x0)
            self.equ = [-m, 1]
            self.c = y1-m*x1

    def draw(self, canvas):
        canvas.create_line(self.p1[0], self.p1[1], self.p2[0], self.p2[1], **self.options)
        self.do_draw = False  # For a line drawn each frame, subclass this class

    def collision(self, other):
        """ Determines whether two Line segments intersect

        Args:
            other: An instance of Line or supporter :class:`soar.sim.world.WorldObject` subclass

        Returns:
            An x, y tuple representing the intersection point, or `None` if there is none
        """
        # First solve for the intersections of the infinite length lines
        a = np.array([other.equ, self.equ])
        b = np.array([[other.c],
                      [self.c]])
        try:
            x = np.linalg.solve(a, b)
        except np.linalg.LinAlgError:
            return None  # TODO: Does this always work?
        else:
            p = x[0][0], x[1][0]
            if self.has_point(p) and other.has_point(p):  # Check whether the point is on the line *segments*
                return p
            else:
                return None

    def has_point(self, p):
        """ Determines if a point lies on the line segment

        Args:
            p: An x, y tuple or an instance of :class:`soar.sim.geometry.Point` as the point to check

        Returns:
            True if the point is on the line segment, and false otherwise
        """
        x, y = p[0], p[1]
        a, b = self.equ[0], self.equ[1]
        c = self.c
        if abs(c-(a*x+b*y)) < 1e-8:
            min_x, min_y = min(self.p1[0], self.p2[0]), min(self.p1[1], self.p2[1])
            max_x, max_y = max(self.p1[0], self.p2[0]), max(self.p1[1], self.p2[1])
            return min_x <= x <= max_x and min_y <= y <= max_y
        return False


class World:
    """ A simulated world containing objects that can be simulated stepwise and drawn on a
    :class:`soar.gui.canvas.SoarCanvas`

    Attributes:
        dimensions (tuple): An x, y tuple representing the worlds length and height
        initial_position: A Pose or an x, y, theta tuple representing the robot's initial position in the world
        objects (list): A list of (WorldObject, layer) tuples containing all of the world's objects
        layer_max (int): The highest layer currently allocated to an object in the world

    Args:
        dimensions (tuple): An x, y tuple representing the worlds length and height
        initial_position: A :class:`soar.sim.geometry.Pose` or an x, y, theta tuple representing the robot's initial
                          position in the world
        objects (list): The initial WorldObject(s) to add to the world
    """
    def __init__(self, dimensions, initial_position, objects=None):
        self.dimensions = dimensions
        self.initial_position = initial_position
        self.objects = []
        self.layer_max = -1
        if objects:
            for obj in objects:
                self.add(obj)
        # Build boundary walls
        x, y = self.dimensions
        for wall in [Line((0, 0), (x, 0)), Line((x, 0), (x, y)), Line((x, y), (0, y)), Line((0, y), (0, 0))]:
            self.add(wall)

    def __getitem__(self, item):
        """ Iterating over a world is the same as interating over the (sorted) object list """
        return self.objects[item][0]

    def add(self, obj, layer=None):
        """ Add an object to the world, with an optional layer specification

        Args:
            obj: An instance of WorldObject or a subclass
            layer (int): The layer on which the object is to be drawn. Objects are drawn in order from smallest to
                         largest layer. If this argument is None, the object's layer will be set to one higher than the
                         highest layer in the objects list
        """
        if layer is None:
            layer = self.layer_max + 1
            self.layer_max += 1
        elif layer > self.layer_max:
            self.layer_max = layer

        self.objects.append((obj, layer))
        self.objects.sort(key=lambda tup: tup[1])  # Sort the list of objects by layer priority
        obj.world = self  # Ensure that every object has a back reference to the world

    def draw(self, canvas):
        """ Draws the world on a canvas

        Objects are drawn in order from the lowest to highest layer if their do_draw attribute is True.

        Args:
            canvas (Canvas): The :class:`soar.gui.canvas.SoarCanvas` on which to draw the world.
                             How each object is drawn is up to the object
        """
        for obj, layer in self.objects:  # The list of objects is already sorted by layer
            if obj.do_draw:
                obj.draw(canvas)

    def delete(self, canvas):
        """ Deletes the world from a canvas, by deleting each object at a time

        Args:
            canvas (Canvas): The :class:`soar.gui.canvas.SoarCanvas` from which to delete.
        """
        for obj, layer in self.objects:
            if obj.do_draw:  # Objects only need to be deleted if they were drawn
                obj.delete(canvas)

    def on_step(self, step_duration):
        """ Performs a single step on the world's objects

        Args:
            step_duration (float): The duration of the step in seconds.
        """
        for obj, layer in self.objects:
            if obj.do_step:
                obj.on_step(step_duration)
