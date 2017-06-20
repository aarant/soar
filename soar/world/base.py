from soar.geometry import Line


class WorldObject:
    def __init__(self, do_draw, do_tick):
        self.do_draw = do_draw
        self.do_tick = do_tick

    def draw(self, canvas):
        pass

    def tick(self, duration):
        pass


class World:
    """ A simulated world containing objects that can be ticked and drawn on a metric canvas

    Attributes:
        dimensions (tuple): An x, y tuple representing the worlds length and height in meters
        objects (list): A list containing every object in the world
    """
    def __init__(self, dimensions, initial_position, objects=None):
        """ Creates a new world

        Args:
            dimensions (tuple): An x, y tuple representing the worlds length and height in meters
            initial_position (tuple): An x, y, theta tuple representing the robot's starting position and rotation
            objects (list): A list containing initial objects to add
        """
        self.dimensions = dimensions
        self.initial_position = initial_position
        self.objects = []
        if objects is not None:
            self.objects.extend(objects)
        for obj in self.objects:
            obj.world = self  # Ensure that every object has a back reference to the world
        # Build boundary walls
        x, y = self.dimensions
        self.add(Line((0, 0), (x, 0)), Line((x, 0), (x, y)), Line((x, y), (0, y)), Line((0, y), (0, 0)))

    def __getitem__(self, item):
        return self.objects[item]

    def add(self, *objects):
        """ Add one or more objects to the world """
        for obj in objects:
            self.objects.append(obj)
            obj.world = self  # Ensure that every object has a back reference to the world

    def draw(self, canvas):
        """ Draws the world on a canvas

        Objects are only drawn if their do_draw attribute is True. Each must support a draw() method

        Args:
            canvas (Canvas): The canvas on which to draw the world. How each object is drawn is up to the object itself
        """
        for obj in self.objects:
            if obj.do_draw:
                obj.draw(canvas)

    def delete(self, canvas):
        for obj in self.objects:
            if obj.do_draw:
                obj.delete(canvas)

    def tick(self, duration):
        """ Performs an update of the world that lasts duration seconds """
        for obj in self.objects:
            if obj.do_tick:
                obj.tick(duration)
