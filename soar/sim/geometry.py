# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/sim/geometry.py
""" Geometry classes, for manipulating points, collections of points, lines, and normalizing angles. """
from math import sin, cos, pi, sqrt, atan2


def clip(value, m1, m2):
    """ Clip a value between two bounds.

    Args:
        value (float): The value to clip.
        m1 (float): The first bound.
        m2 (float): The second bound.

    Returns:
        float: A clipped value guaranteed to be between the min and max of the bounds.
    """
    lower = min(m1, m2)
    upper = max(m1, m2)
    if value > upper:
        return upper
    elif value < lower:
        return lower
    else:
        return value


def ccw(p1, p2, p3):
    """ Determine whether the turn formed by points p1, p2, and p3 is counterclockwise.

    Args:
        p1: An `(x, y)` tuple or `Point` as the start of the turn.
        p2: An `(x, y)` tuple or `Point` as the midpoint of the turn.
        p3: An `(x, y)` tuple or `Point` as the end of the turn.
    """
    return (p2[0]-p1[0]) * (p3[1]-p1[1]) > (p2[1]-p1[1]) * (p3[0]-p1[0])


def normalize_angle_180(theta):
    """ Normalize an angle in radians to be within `-pi` and `pi`.

    Args:
        theta (float): The angle to normalize, in radians.

    Returns:
        float: The normalized angle.
    """
    return ((theta+pi) % (2*pi)) - pi


def normalize_angle_360(theta):
    """ Normalize an angle in radians to be within `0` and `2*pi`.

    Args:
        theta (float): The angle to normalize, in radians.

    Returns:
        float: The normalized angle.
    """
    return theta % 2*pi


class Point:
    """ Represents a point in the x, y plane.

    Points can be interpreted and treated as x, y tuples in most cases.

    Attributes:
        x (float): The x coordinate of the point.
        y (float): The y coordinate of the point.

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
        """ Returns: An `(x, y)` tuple representing the point. """
        return self.x, self.y

    def scale(self, value, other=(0, 0)):
        """ Scale the vector from other to self by value, and return the endpoint of that vector.

        Args:
            value (float): The value to scale by.
            other: An `(x, y)` tuple or a  `Point` as the origin to scale from.

        Returns:
            The endpoint of the scaled vector, as a `Point`.
        """
        d_x, d_y = self.x-other[0], self.y-other[1]
        return Point(d_x*value+other[0], d_y*value+other[1])

    def add(self, other):
        """ Vector addition; adds two points.

        Args:
            other: An `(x, y)` tuple or an instance of `Point`.

        Returns:
            The `Point` that is the sum of this point and the argument.
        """
        return Point(self.x+other[0], self.y+other[1])

    def sub(self, other):
        """ Vector subtraction; subtracts subtracts two points.

        Args:
            other: An `(x, y)` tuple or an instance of `Point`.

        Returns:
            The `Point` that is the difference of this point and the argument.
        """
        return Point(self.x-other[0], self.y-other[1])

    def rotate(self, other, theta):
        """ Rotate about other by theta radians (positive values are counterclockwise).

        Args:
            other: An `(x, y)` tuple or an instance of `Point`.
            theta (float): The number of radians to rotate counterclockwise.

        Returns:
            The rotated `Point`.
        """
        x, y = self.x, self.y
        p_x, p_y = other[0], other[1]
        c, s = cos(theta), sin(theta)
        return Point((x-p_x)*c-(y-p_y)*s+p_x, (x-p_x)*s+(y-p_y)*c+p_y)

    def midpoint(self, other):
        """ Return a new `Point` that is the midpoint of self and other.

        Args:
            other: An `(x, y)` tuple or an instance of `Point`.

        Returns:
            A `Point` that is the midpoint of self and other.
        """
        return Point((self.x+other[0])/2.0, (self.y+other[1])/2.0)

    def distance(self, other):
        """ Calculate the distance between two points.

        Args:
            other: An `(x, y)` tuple or an instance of `Point`.

        Returns:
            float: The Euclidean distance between the points.
        """
        return sqrt(abs(self[0]-other[0])**2+abs(self[1]-other[1])**2)

    def is_near(self, other, eps):
        """ Determine whether the distance between two points is within a certain value.

        Args:
            other: An `(x, y)` tuple or an instance of `Point`.
            eps (float): The epilson within which to consider the points near one another.

        Returns:
            bool: `True` if the points are withing `eps` of each other, `False` otherwise.
        """
        return self.distance(other) < eps

    def magnitude(self):
        """ The magnitude of this point interpreted as a vector.

        Returns:
            float: The magnitude of the vector from the origin to this point.
        """
        return sqrt(self[0]**2+self[1]**2)

    def angle_to(self, other):
        """ Return the angle between two points.

        Args:
            other: An `(x, y)` tuple or an instance of `Point`.

        Returns:
            float: Angle in radians of the vector from self to other.
        """
        d_x = other[0]-self[0]
        d_y = other[1]-self[1]
        return atan2(d_y, d_x)

    def copy(self):
        """ Returns a copy of the `Point`. """
        return Point(*self)


class Pose(Point):
    """ A point facing a direction in the xy plane.

    Poses can be interpreted and treated as `(x, y, theta)` tuples in most cases.

    Args:
        x: The x coordinate of the pose.
        y: The y coordinate of the pose.
        t: The angle between the direction the pose is facing and the positive x axis, in radians.
    """

    def __init__(self, x, y, t):
        Point.__init__(self, x, y)
        self.t = t

    def __str__(self):
        return '(' + str(self.x) + ', ' + str(self.y) + ', ' + str(self.t) + ')'

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
        """ Returns: An `(x, y, t)` tuple representing the pose. """
        return self.x, self.y, self.t

    def transform(self, other):
        """ Return a new pose that has been transformed (translated and turned).

         Args:
             other: A `Pose` or 3-tuple-like object, by which to translate and turn.

         Returns:
             A new `Pose` equivalent to translating `self` by `(other[0], other[1])` and rotating by
             `other[2]`.
         """
        return Pose(self.x+other[0], self.y+other[1], (self.t+other[2]) % (2.0*pi))

    def rotate(self, pivot, theta):
        """ Rotate the point portion of the pose about a pivot. Leaves the theta portion unchanged.

        Args:
            pivot: A `Point`, subclass (like `Pose`), or `(x, y)` tuple as the pivot/axis of rotation.
            theta (float): The number of radians to rotate by. Positive values are counterclockwise.
        """
        x, y = Point.rotate(self, pivot, theta)
        return Pose(x, y, self.t)

    def is_near(self, other, dist_eps, angle_eps):
        """ Determine whether two poses are close.

        Args:
            other: An `(x, y, t)` tuple or  `Pose`.
            dist_eps (float): The distance epilson within which to consider the poses close.
            angle_eps (float): The angle episilon within which to consider the poses close.

        Returns:
            bool: `True` if the distance between the point portions is within `dist_eps`, and the normalized difference
            between the angle portions is within `angle_eps`.
        """
        return Point.is_near(self, other, dist_eps) and abs(normalize_angle_180(self[2]-other[2])) < angle_eps

    def point(self):
        """ Strips the angle component of the pose and returns a point at the same position.

        Returns:
            The `(x, y)` portion of the pose, as a `Point`.
        """
        return Point(self.x, self.y)

    def copy(self):
        """ Returns a copy of the Pose. """
        return Pose(*self)


class PointCollection:
    """ A movable collection of points.

    Can be iterated over like a list of `Point`. Unlike `Point`, PointCollections are mutable--that is, rotating them,
    translating them, etc. changes the internal point list.

    Args:
        points: A list of `(x, y)` tuples or `Point`.
        center: An `(x, y)` tuple or `Point` as the pivot or center of the collection.
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
            origin: An `(x, y)` tuple or `Point` from which the collection's points will move away/towards.
        """
        self.points = [p.scale(value, origin) for p in self.points]
        self.center = self.center.scale(value, origin)

    def translate(self, delta):
        """ Translate the collection by the vector delta.

        Args:
            delta: An `(x, y)` tuple or `Point`, treated as a vector and added to each point in the collection.
        """
        self.points = [p.add(delta) for p in self.points]
        self.center = self.center.add(delta)

    def rotate(self, pivot, theta):
        """ Rotate about other by theta radians (positive values are counterclockwise).

        Args:
            pivot: An `(x, y)` tuple or a `Point`.
            theta (float): The number of radians to rotate counterclockwise.
        """
        self.points = [p.rotate(pivot, theta) for p in self.points]
        self.center = self.center.rotate(pivot, theta)

    def recenter(self, new_center):
        """ Re-center the collection.

        Args:
            new_center: An `(x, y)` tuple or `Point` that will be the collection's new center.
        """
        diff = Point(new_center[0], new_center[1]).sub(self.center)
        self.translate(diff)


class Line:
    """ A line in the `(x, y)` plane defined by two points on the line.

    Args:
        p1: An `(x, y)` tuple or `Point` as one of the points on the line.
        p2: An `(x, y)` tuple or `Point` as another point on the line.
        eps (float, optional): The epsilon within which to consider a line horizontal or vertical, for precision
            purposes.
        normalize (bool, optional): If `True`, normalize the internal vector representation to be a unit vector.
    """
    def __init__(self, p1, p2, eps=1e-8, normalize=False):
        self.p1 = p1
        self.p2 = p2
        x0, y0 = p1
        x1, y1 = p2
        if abs(x1-x0) < eps:
            self.a = 1.0
            self.b = 0
            self.c = x0
        elif abs(y1-y0) < eps:
            self.a = 0.0
            self.b = 1.0
            self.c = y0
        else:
            d_x = x1-x0
            d_y = y1-y0
            if normalize:
                norm = sqrt(d_x**2+d_y**2)
                self.a = d_y/norm
                self.b = -d_x/norm
            else:
                self.a = d_y
                self.b = -d_x
            self.c = self.a*x0+self.b*y0

    def distance_from_line(self, p):
        """ Determine the (signed) distance of a point from the line.

        Args:
            p: An `(x, y)` tuple or `Point` to measure distance from.

        Returns:
            float: The signed distance from the line.
        """
        return self.a*p[0]+self.b*p[1] - self.c

    def has_point(self, p, eps=1e-8):
        """ Determine whether a point lies on the line.

        Args:
            p: The `(x, y)` tuple or `Point` to check.
            eps (float, optional): The distance to tolerate before a point is considered not to be on the line.

        Returns:
            bool: `True` if the point is on the line, `False` otherwise.
        """
        return abs(self.distance_from_line(p)) < eps

    def intersection(self, other, eps=1e-8):
        """ Determine whether two lines intersect.

        Args:
            other: The `Line` to find the intersection with.
            eps (float, optional): The smallest absolute difference to tolerate before the lines are considered to be
                converging.

        Returns:
            The `Point` of intersection, or `None` if the lines are parallel (based on epsilon).
        """
        det = self.a*other.b-other.a*self.b
        if abs(det) < eps:
            return None  # The lines are parallel, or almost parallel
        x = (other.b*self.c - self.b*other.c)/det
        y = (self.a*other.c - other.a*self.c)/det
        return Point(x, y)


class LineSegment(Line):
    """ A line segment in the `(x, y)` plane defined by two endpoints.

    Args:
        p1: An `(x, y)` tuple or `Point` as the first endpoint.
        p2: An `(x, y)` tuple or `Point` as the second endpoint.
        eps (float, optional): The minimum absolute difference in x or y before the line is considered horizontal or
            vertical.
    """
    def __init__(self, p1, p2, eps=1e-8):
        Line.__init__(self, p1, p2, eps)

    def has_point(self, p, eps=1e-8):
        """ Determine whether a point lies on the line segment.

        Args:
            p: The `(x, y)` tuple or `Point` to check.
            eps (float, optional): The distance to tolerate before a point is considered not to be on the line
                segment.

        Returns:
            bool: `True` if the point is on the line segment, `False` otherwise.
        """
        if not Line.has_point(self, p, eps):
            return False
        x, y = p[0], p[1]
        min_x, min_y = min(self.p1[0], self.p2[0]), min(self.p1[1], self.p2[1])
        max_x, max_y = max(self.p1[0], self.p2[0]), max(self.p1[1], self.p2[1])
        if abs(max_x-min_x) < eps:  # The line is vertical
            return abs(max_x-x) < eps and min_y <= y <= max_y
        elif abs(max_y - min_y) < eps:  # The line is horizontal
            return abs(max_y - y) < eps and min_x <= x <= max_x
        else:
            return min_x <= x <= max_x and min_y <= y <= max_y

    def has_intersect(self, other):
        """ Determine whether one segment intersects with another.

        Args:
            other: Another `LineSegment`.

        Returns:
            bool: `True` if the segments have an intersection, `False` otherwise.
        """
        if isinstance(other, LineSegment):  # We only check for intersections with other segments
            a1, b1 = self.p1, self.p2
            a2, b2 = other.p1, other.p2
            return ccw(a1, b1, a2) != ccw(a1, b1, b2) and ccw(a2, b2, a1) != ccw(a2, b2, b1)
        else:
            return False

    def intersection(self, other, eps=1e-8):
        """ Find the intersection(s) between two line segments, or this line segment and a `Line`.

        Args:
            other: The other `LineSegment` to find intersections with.
            eps (float, optional): The epsilon or tolerance to pass to the `Line` intersection and `has_point` checks.

        Returns:
            Either a list of `Point` (s) representing all of the intersections, or `None`, if there weren't any. Also
            returns `None` if the segment and a `Line` are exactly parallel.
        """
        if isinstance(other, LineSegment):  # Intersection between two segments
            if not self.has_intersect(other):  # Check whether the segments intersect in the first place
                return None
            potential = Line.intersection(self, other, eps)
            if potential is None:  # The segments are parallel, so find the endpoints they share
                potential = [self.p1, self.p2, other.p1, other.p2]
                potential = list(set(filter(lambda p: self.has_point(p, eps) and other.has_point(p, eps), potential)))
                return potential if len(potential) > 0 else None
            # Otherwise, just check whether the potential point is on both segments
            return [potential] if self.has_point(potential, eps) and other.has_point(potential, eps) else None
        # Otherwise, intersection between a segment (self) and a line (other)
        potential = Line.intersection(self, other, eps)
        return [potential] if potential is not None and self.has_point(potential, eps) else None
