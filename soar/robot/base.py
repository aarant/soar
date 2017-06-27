from math import sin, cos
from soar.geometry import Pose

class SignalError(Exception):
    def __init__(self, message):
        self.message = message


class GenericRobot:
    """ A generic robot class """

    def __init__(self, io=None, pos=None):
        self.io = io
        if pos is None:
            self.pos = Pose(0, 0, 0)
        self.fv = 0
        self.rv = 0
        self.signals = {}

    def signal(self, name, value=None):
        if name not in self.signals:
            raise SignalError('Signal ' + name + ' is invalid')
        else:
            return self.signals[name](value)

    def tick(self, duration):
        theta = self.pos.xyt_tuple()[2]
        d_x, d_y, d_t = cos(-theta)*self.fv*duration, sin(-theta)*self.fv*duration, self.rv*duration  # TODO: Negative theta
        self.pos = self.pos.transform(Pose(d_x, d_y, d_t))

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def draw(self, canvas):
        raise NotImplementedError

    def delete(self, canvas):
        raise NotImplementedError

    def on_load(self):
        pass

    def on_start(self):
        pass

    def on_step(self):
        pass

    def on_stop(self):
        pass

    def on_shutdown(self):
        pass
