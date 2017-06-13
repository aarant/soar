from tkinter import *

from soar.geometry import *

class SoarCanvas(Canvas):
    def __init__(self, parent, **options):  # Will add additional options later TODO
        self.pixels_per_meter = options.pop('pixels_per_meter', 100)
        Canvas.__init__(self, parent, **options)

    def create_polygon(self, *args, **kw):
        args = list(map(lambda x: x*self.pixels_per_meter, args))
        Canvas.create_polygon(self, *args, **kw)

    def create_line(self, *args, **kw):
        args = list(map(lambda x: x * self.pixels_per_meter, args))
        Canvas.create_line(self, *args, **kw)
