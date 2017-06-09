class SignalError(Exception):
    def __init__(self, message):
        self.message = message


class GenericRobot:
    """ A generic robot class """

    def __init__(self, io=None, pos=None, rot=0):
        self.io = io
        self.pos = pos
        self.rot = rot
        self.signals = {'connect': self.connect}

    def signal(self, name, value=None):
        if name not in self.signals:
            raise NotImplementedError
        else:
            return self.signals[name](value)

    def connect(self):
        if self.io is None:
            return

    def draw(self, canvas):
        raise NotImplementedError

    def delete(self, canvas):
        raise NotImplementedError
