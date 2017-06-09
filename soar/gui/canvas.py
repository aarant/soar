from tkinter import *

from soar.geometry import *

class RobotGraphics(PointCollection):
    """ A manipulable robot sprite """

    def __init__(self, scale=1.0, center=None, rot=0):
        PointCollection.__init__(self, [(-0.205, 0.09525), (-0.0889, 0.20975), (0.0, 0.200025), (0.0889, 0.20975),
                                        (0.205, 0.09525), (0.205, -0.0635), (0.1651, -0.0635), (0.1651, -0.1651),
                                        (0.0889, -0.23495), (-0.0889, -0.23495), (-0.1651, -0.1651), (-0.1651, -0.0635),
                                        (-0.205, -0.0635)], fill='black', tags='robot')
        if scale != 1.0: self.scale(scale)
        if center is not None: self.recenter(center)
        if rot != 0: self.rotate(self.center, rot)

class SoarCanvas(Canvas):
    def __init__(self, parent, **options):  # Will add additional options later TODO
        self.pixels_per_meter = options.pop('pixels_per_meter', 100)
        Canvas.__init__(self, parent, **options)

    def create_polygon(self, *args, **kw):
        args = list(map(lambda x: x*self.pixels_per_meter, args))
        Canvas.create_polygon(self, *args, **kw)
