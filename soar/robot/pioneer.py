from soar.geometry import *
from soar.robot.base import GenericRobot
from math import pi

def clip(value, m1, m2):
    lower = min(m1, m2)
    upper = max(m1, m2)
    if value > upper:
        return upper
    elif value < lower:
        return lower
    else:
        return value

class PioneerRobot(GenericRobot):
    def __init__(self, io=None, pos=None, rot=0):
        GenericRobot.__init__(self, io, pos, rot)
        self.signals.update({'set_forward_velocity': self.set_forward_velocity,
                             'set_rotational_velocity': self.set_rotational_velocity,
                             'sonars': self.get_sonars})
        # TODO: Keeping the old points just in case
        p = [(-0.205, 0.09525), (-0.0889, 0.20975), (0.0, 0.200025), (0.0889, 0.20975),
                                        (0.205, 0.09525), (0.205, -0.0635), (0.1651, -0.0635), (0.1651, -0.1651),
                                        (0.0889, -0.23495), (-0.0889, -0.23495), (-0.1651, -0.1651), (-0.1651, -0.0635),
                                        (-0.205, -0.0635)]
        for i in range(len(p)):
            p[i] = Point(*p[i])
        p[0].sub((0, 0.05))
        p[4].sub((0, 0.05))
        p[1].sub(p[1])
        p[1].add(p[0])
        p[1].add((0, 0.0912335829221))
        p[1].rotate(p[0], 2*pi/14)
        p[2].sub(p[2])
        p[2].add(p[1])
        p[2].scale(2.0, p[0])
        p[2].rotate(p[1], 2*pi/14)
        p[3] = Point(*p[2])
        p[3].scale(2.0, p[1])
        p[3].rotate(p[2], 2*pi/14)
        p.insert(4, Point(*p[3]))
        p[4].scale(2.0, p[2])
        p[4].rotate(p[3], 2*pi/14)
        p.insert(5, Point(*p[4]))
        p[5].scale(2.0, p[3])
        p[5].rotate(p[4], 2*pi/14)
        for i in range(len(p)):
            p[i] = p[i][0], p[i][1]
        self.polygon = PointCollection([(-0.205, 0.04525), (-0.16541523190866744, 0.12744861792000592),
                                        (-0.09408594452181207, 0.18433182645896837),
                                        (-0.005139778002701836, 0.2046332085389749),
                                        (0.0838063885164084, 0.18433182645896834),
                                        (0.15513567590326377, 0.12744861792000586),
                                        (0.205, 0.04525), (0.205, -0.0635), (0.1651, -0.0635),
                                        (0.1651, -0.1651), (0.0889, -0.23495), (-0.0889, -0.23495),
                                        (-0.1651, -0.1651), (-0.1651, -0.0635), (-0.205, -0.0635)],
                                       fill='black', tags='pioneer')
        self.tags = 'pioneer'
        self.fv = None
        self.rv = None
        self.FV_CAP = 2.0  # TODO: These are not correct
        self.RV_CAP = 0.5

    def get_sonars(self):
        if self.io is None:
            return

    def draw(self, canvas):
        self.polygon.recenter(self.pos)
        self.polygon.draw(canvas)

    def delete(self, canvas):
        self.polygon.delete(canvas)

    def set_forward_velocity(self, fv):
        if self.io is None:
            self.fv = clip(fv, -self.FV_CAP, self.FV_CAP)

    def set_rotational_velocity(self, rv):
        if self.io is None:
            self.rv = clip(rv, -self.RV_CAP, self.RV_CAP)