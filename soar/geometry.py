""" SoaR v0.3.0 geometry classes """

from math import sin, cos


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
        c, s= cos(theta), sin(theta)
        self.x, self.y = (x-p_x)*c+(y-p_y)*s+p_x, (y-p_y)*c-(x-p_x)*s+p_y


class PointCollection:
    """ A collection of Points with Tkinter options """

    def __init__(self, points, **options):
        """ points may be a list of tuples or a list of Points; they will be converted to points """
        self.points = []
        for p in points:
            if isinstance(p, Point):
                self.points.append(p)
            else:
                self.points.append(Point(p[0], p[1]))
        l = len(self.points)
        self.center = Point(sum([t[0] for t in self.points])/l, sum([t[1] for t in self.points])/l)
        self.options = options

    def __getitem__(self, item):
        return self.points[item]

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
        for p in self.points:
            p.sub(self.center)
            p.add(new_center)
        l = len(self.points)
        self.center = Point(sum([t[0] for t in self.points]) / l, sum([t[1] for t in self.points]) / l)

    def draw(self, canvas):
        flat_points = []
        for p in self.points:
            flat_points.extend([p.x, p.y])
        canvas.create_polygon(*flat_points, **self.options)

    def delete(self, canvas):
        if 'tags' not in self.options:
            canvas.delete('all')
        else:
            canvas.delete(self.options['tags'])
