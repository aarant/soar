""" SoaR v0.5.0 geometry classes """

from math import sin, cos, pi, sqrt

import numpy as np

from soar.gui.drawable import Drawable


class Point:
    """ Represents a point in the x, y plane"""
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
        return self.x, self.y

    def scale(self, value, other=(0, 0)):  # Scale the vector from other to self by value, and make self the endpoint
        d_x, d_y = self.x-other[0], self.y-other[1]
        self.x, self.y = d_x*value+other[0], d_y*value+other[1]

    def add(self, other):  # Vector addition; adds other to self
        self.x, self.y = self.x+other[0], self.y+other[1]

    def sub(self, other):  # Vector subtraction; subtracts other from self
        self.x, self.y = self.x-other[0], self.y-other[1]

    def rotate(self, other, theta):  # Rotate about other by theta radians
        x, y = self.x, self.y
        p_x, p_y = other[0], other[1]
        c, s = cos(theta), sin(theta)
        self.x, self.y = (x-p_x)*c+(y-p_y)*s+p_x, (y-p_y)*c-(x-p_x)*s+p_y

    def midpoint(self, other):
        return Point((self.x+other[0])/2.0, (self.y+other[1])/2.0)

    def distance(self, other):
        return sqrt(abs(self[0]-other[0])**2+abs(self[1]-other[1])**2)


class Pose(Point):
    """ Represents a point facing a direction in the xy plane """

    def __init__(self, x, y, t):
        """ Stored internally as an (x, y, theta) tuple """
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
        return self.x, self.y, self.t

    def transform(self, other):
        """ Returns a pose translated by other[0], other[1], and rotates by other[2] """
        return Pose(self.x+other[0], self.y+other[1], (self.t+other[2]) % (2.0*pi))

    def draw(self, canvas, length, **options):
        x1, y1 = length*cos(self.t)+self.x, length*sin(self.t)+self.y
        canvas.create_line(self.x, self.y, x1, y1, **options)


class PointCollection(Drawable):
    """ A collection of Points with Tkinter options """

    def __init__(self, points, center=None, **options):
        """ points may be a list of tuples or a list of Points; they will be converted to points """
        Drawable.__init__(self, **options)
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
        self.options = options

    def __getitem__(self, item):
        return self.points[item]

    def __str__(self):
        return str([str(p) for p in self.points])

    def scale(self, value, origin=(0, 0)):
        for p in self.points:
            p.scale(value, origin)
        self.center.scale(value, origin)

    def translate(self, delta):  # Translate by (delta[0], delta[1])
        for p in self.points:
            p.add(delta)
        self.center.add(delta)

    def rotate(self, pivot, theta):  # Rotate about (pivot[0], pivot[1]) by theta radians
        for p in self.points:
            p.rotate(pivot, theta)
        self.center.rotate(pivot, theta)

    def recenter(self, new_center):  # Recenters the collection about (new_center[0], new_center[1])
        diff = Point(new_center[0], new_center[1])
        diff.sub(self.center)
        self.translate(diff)

    def draw(self, canvas):
        flat_points = []
        for p in self.points:
            flat_points.extend([p.x, p.y])
        canvas.create_polygon(*flat_points, **self.options)


class Line(Drawable):
    def __init__(self, start, end, **options):
        Drawable.__init__(self, **options)
        self.start = start
        self.end = end
        if 'width' not in options:
            self.options.update({'width': 2.0})
        self.redraw = True
        x0, y0 = start
        x1, y1 = end
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
        canvas.create_line(self.start[0], self.start[1], self.end[0], self.end[1], **self.options)
        self.redraw = False

    def intersection(self, other):
        a = np.array([other.equ, self.equ])
        b = np.array([[other.c],
                      [self.c]])
        try:
            x = np.linalg.solve(a, b)
        except np.linalg.LinAlgError:
            return None  # TODO: Catch errors
        return x[0][0], x[1][0]

    def has_point(self, p):
        x, y = p.xy_tuple()
        a, b = self.equ[0], self.equ[1]
        c = self.c
        if abs(c-(a*x+b*y)) < 0.00000001:  # TODO: Epsilon
            min_x, min_y = min(self.start[0], self.end[0]), min(self.start[1], self.end[1])
            max_x, max_y = max(self.start[0], self.end[0]), max(self.start[1], self.end[1])
            return min_x <= x <= max_x and min_y <= y <= max_y
        return False
