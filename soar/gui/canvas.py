from tkinter import *

class SoarCanvas(Canvas):
    def __init__(self, parent, **options):  # Will add additional options later TODO
        self.pixels_per_meter = options.pop('pixels_per_meter', 100)
        Canvas.__init__(self, parent, highlightthickness=0, **options)
        self.bind("<Configure>", self.on_resize)
        self.width = options['width']
        self.height = options['height']

    def on_resize(self, event):
        wscale = event.width / float(self.width)
        hscale = event.height / float(self.height)
        scale = min(wscale, hscale)
        self.width *= scale
        self.height *= scale
        self.config(width=self.width, height=self.height)
        self.pixels_per_meter *= scale
        self.scale('all', 0, 0, scale, scale)

    def create_polygon(self, *args, **kw):
        args = self.remap_coords(args)
        Canvas.create_polygon(self, *args, **kw)

    def create_line(self, *args, **kw):
        args = self.remap_coords(args)
        Canvas.create_line(self, *args, **kw)

    def remap_coords(self, coords):
        remapped = []
        for i in range(len(coords)):
            c = coords[i]*self.pixels_per_meter
            if i % 2 == 1:  # Every other coordinate is a y coordinate, and so must be remapped
                c = self.height-c
            remapped.append(c)
        return remapped


class SoarCanvasFrame(Frame):
    def __init__(self, parent, **options):
        Frame.__init__(self, parent, **options)
        self.bind("<Configure>", self.on_resize)
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()

    def on_resize(self, event):
        # determine the ratio of old width/height to new width/height
        wscale = event.width / float(self.width)
        hscale = event.height / float(self.height)
        self.width = event.width
        self.height = event.height
        for child in self.children.values():
            if isinstance(child, SoarCanvas):
                child.config(width=event.width, height=event.height)
