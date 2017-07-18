""" Soar v0.11.0 Geometry classes, for manipulating points and collections of points. """
from math import sin, cos, pi, sqrt


class Point:
    """ Represents a point in the x, y plane.

     Points can be interpreted and treated as x, y tuples in most cases.

    Args:
        x (float): The x coordinate of the point.
        y (float): The y coordinate of the point.
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return '(' + str(self.x) + ', ' + str(self.y) + ')'

    def __getitem__(self, key):  # This is so we can cheat and use xy tuples as 'other' inputs
        if key == 0:
            return self.x
        elif key == 1:
            return self.y
        else:
            raise IndexError('tuple index out of range')

    def xy_tuple(self):
        """ Returns: An x, y tuple representing the point. """
        return self.x, self.y

    def scale(self, value, other=(0, 0)):
        """ Scale the vector from other to self by value, and make this point the endpoint of that vector.

        Args:
            value (float): The value to scale by.
            other: An x, y tuple or an instance of Point as the origin to scale from.
        """
        d_x, d_y = self.x-other[0], self.y-other[1]
        self.x, self.y = d_x*value+other[0], d_y*value+other[1]

    def add(self, other):
        """ Vector addition; adds other to self.

        Args:
            other: An x, y tuple or an instance of Point.
        """
        self.x, self.y = self.x+other[0], self.y+other[1]

    def sub(self, other):
        """ Vector subtraction; subtracts other from self.

        Args:
            other: An x, y tuple or an instance of Point.
        """
        self.x, self.y = self.x-other[0], self.y-other[1]

    def rotate(self, other, theta):  # Rotate about other by theta radians
        """ Rotate about other by theta radians (positive values are counterclockwise).

        Args:
            other: An x, y tuple or an instance of Point.
            theta (float): The number of radians to rotate counterclockwise.
        """
        x, y = self.x, self.y
        p_x, p_y = other[0], other[1]
        c, s = cos(theta), sin(theta)
        self.x, self.y = (x-p_x)*c-(y-p_y)*s+p_x, (x-p_x)*s+(y-p_y)*c+p_y

    def midpoint(self, other):
        """ Returns a new Point that is the midpoint of self and other.

        Args:
            other: An x, y tuple or an instance of Point.

        Returns:
            A Point that is the midpoint of self and other.
        """
        return Point((self.x+other[0])/2.0, (self.y+other[1])/2.0)

    def distance(self, other):
        """ Calculates the distance between two points.

        Args:
            other: An x, y tuple or an instance of Point.

        Returns:
            A float representing the distance between the points.
        """
        return sqrt(abs(self[0]-other[0])**2+abs(self[1]-other[1])**2)


class Pose(Point):
    """ A point facing a direction in the xy plane.

    Poses can be interpreted and treated as x, y, t tuples in most cases.

    Args:
        x: The x coordinate of the pose.
        y: The y coordinate of the pose.
        t: The angle between the direction the pose is facing and the positive x axis, in radians.
    """

    def __init__(self, x, y, t):
        Point.__init__(self, x, y)
        self.t = t

    def __str__(self):
        return '(' + str(self.x) + ', ' + str(self.y) + str(self.t) + ')'

    def __getitem__(self, key):  # This is so we can cheat and use xyt tuples as 'other' inputs
        if key == 0:
            return self.x
        elif key == 1:
            return self.y
        elif key == 2:
            return self.t
        else:
            raise IndexError('tuple index out of range')

    def xyt_tuple(self):
        """ Returns: An (x, y, t) tuple representing the pose. """
        return self.x, self.y, self.t

    def transform(self, other):
        """ Return a new pose that has been transformed (translated and rotated).

         Args:
             other: A ``Pose`` or 3-tuple-like object, by which to translate and rotate.

         Returns: A new ``Pose`` equivalent to translating ``self`` by ``(other[0], other[1])`` and rotating by
                  ``other[2]``.
         """
        return Pose(self.x+other[0], self.y+other[1], (self.t+other[2]) % (2.0*pi))

    def draw(self, canvas, length, **options):  # TODO: Move this into a WorldObject subclass?
        x1, y1 = length*cos(self.t)+self.x, length*sin(self.t)+self.y
        canvas.create_line(self.x, self.y, x1, y1, **options)


class PointCollection:
    """ A movable collection of Points.

    Can be iterated over like a list of Points.

    Args:
        points: A list of (x, y) tuples or Points.
        center: An (x, y) tuple or Point as the pivot or center of the collection.
    """
    def __init__(self, points, center=None):
        self.points = []
        for p in points:
            if isinstance(p, Point):
                self.points.append(p)
            else:
                self.points.append(Point(p[0], p[1]))
        l = len(self.points)
        if center is None:
            self.center = Point(sum([t[0] for t in self.points])/l, sum([t[1] for t in self.points])/l)
        else:
            self.center = Point(*center)

    def __getitem__(self, item):
        return self.points[item]

    def __len__(self):
        return len(self.points)

    def __str__(self):
        return str([str(p) for p in self.points])

    def scale(self, value, origin=(0, 0)):
        """ Scale each point away/towards some origin.

        Args:
            value (float): The scale amount.
            origin: An x, y tuple or Point from which the collection's points will move away/towards.
        """
        for p in self.points:
            p.scale(value, origin)
        self.center.scale(value, origin)

    def translate(self, delta):
        """ Translate the collection by the vector delta.

        Args:
            delta: An x, y tuple or Point, treated as a vector and added to each point in the collection.
        """
        for p in self.points:
            p.add(delta)
        self.center.add(delta)

    def rotate(self, pivot, theta):
        """ Rotate about other by theta radians (positive values are counterclockwise).

        Args:
            pivot: An x, y tuple or an instance of Point.
            theta (float): The number of radians to rotate counterclockwise.
        """
        for p in self.points:
            p.rotate(pivot, theta)
        self.center.rotate(pivot, theta)

    def recenter(self, new_center):
        """ Re-center the collection.

        Args:
            new_center: An x, y tuple or Point that will be the collection's new center.
        """
        diff = Point(new_center[0], new_center[1])
        diff.sub(self.center)
        self.translate(diff)