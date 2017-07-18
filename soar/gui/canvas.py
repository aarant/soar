""" Soar v0.1.0 Canvas classes and methods.

Defines ``SoarCanvas`` and ``SoarCanvasFrame`` classes, as well as a method of creating them from an instance of
:class:`soar.sim.world.World`.
"""
from tkinter import *


def canvas_from_world(world, toplevel=Toplevel, close_cmd=None):
    """ Return a :class:`soar.gui.canvas.SoarCanvas` in a new window from a World. Optionally, call a different
    ``toplevel()`` method to create the window, and set its behavior on close.

    Additionally, if an object in the world defines ``on_press``, ``on_release``, and ``on_motion`` methods, bind those
    to the associated mouse events for that tag, making it draggable.

    Args:
        world: An instance of :class:`soar.sim.world.World` or a subclass.
        toplevel (optional): The function or method to call to create the window itself.
        close_cmd (optional): The function or method to call when the window is destroyed.

    Returns:
        The new `SoarCanvas`.
    """
    dim_x, dim_y = world.dimensions
    max_dim = max(dim_x, dim_y)
    width = int(dim_x / max_dim * 500)
    height = int(dim_y / max_dim * 500)
    options = {'width': width, 'height': height, 'pixels_per_meter': 500 / max_dim, 'bg': 'white'}
    t = toplevel()
    t.title('SoaR v0.11.0 Simulation')
    if close_cmd:
        t.protocol('WM_DELETE_WINDOW', close_cmd)
    t.aspect(width, height, width, height)
    f = SoarCanvasFrame(t)
    f.pack(fill=BOTH, expand=YES)
    c = SoarCanvas(f, **options)
    c.pack(fill=BOTH, expand=YES)
    world.canvas = c
    for obj in world:  # Bind mouse events to any object in the world which defines them
        if all([hasattr(obj, attr) for attr in ['on_press', 'on_release', 'on_motion']]):
            c.tag_bind(obj.tags, '<ButtonPress-1>', obj.on_press)
            c.tag_bind(obj.tags, '<ButtonRelease-1>', obj.on_release)
            c.tag_bind(obj.tags, '<B1-Motion>', obj.on_motion)
    return c


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