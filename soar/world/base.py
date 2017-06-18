from soar.geometry import Line

class World:
    def __init__(self, dimensions, initial_position=(0, 0), objects=None):
        self.dimensions = dimensions
        self.initial_position = initial_position
        if objects is None:
            objects = []
        self.objects = objects
        x, y = self.dimensions
        self.objects.extend([Line((0, 0), (x, 0)), Line((x, 0), (x, y)), Line((x, y), (0, y)), Line((0, y), (0, 0))])

    def draw(self, canvas):
        for obj in self.objects:
            if obj.redraw:
                obj.draw(canvas)

    def delete(self, canvas):
        for obj in self.objects:
            if obj.redraw:
                obj.delete(canvas)

    def tick(self, duration):
        for obj in self.objects:
            try:
                do_tick = obj.do_tick
                if do_tick:
                    obj.tick(self, duration)
            except AttributeError:
                foo = 0  # TODO
