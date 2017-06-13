from soar.geometry import *
from soar.robot.base import GenericRobot
from soar.geometry import Line

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
    def __init__(self, io=None, pos=None):
        GenericRobot.__init__(self, io, pos)
        self.signals.update({'set_forward_velocity': self.set_forward_velocity,
                             'set_rotational_velocity': self.set_rotational_velocity,
                             'sonars': self.get_sonars})
        self.polygon = PointCollection([(-0.034120395949525435, -0.21988658579769327),
                                        (0.057113186972574566, -0.21988658579769327),
                                        (0.13931180489258044, -0.17002226170095702),
                                        (0.1961950134315429, -0.09869297431410165),
                                        (0.21649639551154948, -0.009746807794991423),
                                        (0.19619501343154294, 0.07919935872411882),
                                        (0.1393118048925805, 0.15052864611097416),
                                        (0.05711318697257454, 0.1901134142023067),
                                        (-0.03412039594952546, 0.1901134142023067),
                                        (-0.05163681302742546, 0.1901134142023067),
                                        (-0.051636813027425454, 0.15021341420230672),
                                        (-0.15323681302742542, 0.15021341420230672),
                                        (-0.22308681302742545, 0.07401341420230673),
                                        (-0.22308681302742545, -0.10378658579769329),
                                        (-0.15323681302742542, -0.17998658579769328),
                                        (-0.05163681302742544, -0.17998658579769328),
                                        (-0.051636813027425434, -0.21988658579769327)],
                                       None, fill='black', tags='pioneer')
        self.sonar_poses = [(0.013008094924083946, -0.20651169941255937, -1.57),
                            (0.09972419534513688, -0.18157953736419125, -1.21),
                            (0.16926510857462096, -0.12098273162239542, -0.6731984257692414),
                            (0.20785740388410556, -0.040845004669412655, -0.2243994752564138),
                            (0.20785740388410556, 0.04810116184969754, 0.2243994752564138),
                            (0.16926510857462107, 0.12823888880268036, 0.6731984257692414),
                            (0.09972419534513688, 0.18369591654177436, 1.21),
                            (0.013008094924083946, 0.20348830058744055, 1.57)]
        self.tags = 'pioneer'
        self.FV_CAP = 2.0  # TODO: These are not correct
        self.RV_CAP = 0.5

    def set_forward_velocity(self, fv):
        if self.io is None:
            self.fv = clip(fv, -self.FV_CAP, self.FV_CAP)

    def set_rotational_velocity(self, rv):
        if self.io is None:
            self.rv = clip(rv, -self.RV_CAP, self.RV_CAP)

    def get_sonars(self):
        if self.io is None:
            i = 0
            sonars = [5.0]*8
            for pose in self.sonar_poses:
                temp = Pose(*pose)
                temp = temp.transform((self.polygon.center[0], self.polygon.center[1], -self.pos[2]))
                temp.rotate(self.polygon.center, self.pos[2])
                x0, y0 = temp[0], temp[1]
                x1, y1 = x0 + 5.0 * cos(temp[2]), y0 + 5.0 * sin(temp[2])
                l = Line((x0, y0), (x1, y1))
                intersects = []
                for obj in self.world.objects:
                    p = l.intersection(obj)
                    if p is not None:
                        p = Point(*p)
                        intersects.append((p, p.distance(temp)))
                intersects.sort(key=lambda t: t[1])
                for p, distance in intersects:
                    if l.has_point(p):
                        if distance > 1.5:  # TODO: Sonar max
                            sonars[i] = 5.0
                        else:
                            sonars[i] = distance
                        break
                i += 1
            return sonars

    def tick(self, duration):
        GenericRobot.tick(self, duration)
        d_t = self.rv*duration
        self.polygon.rotate(self.polygon.center, d_t)

    def draw(self, canvas):
        self.polygon.recenter(self.pos)
        self.polygon.draw(canvas)
        sonars = self.get_sonars()
        for dist, pose in zip(sonars, self.sonar_poses):
            temp = Pose(*pose)
            temp = temp.transform((self.polygon.center[0], self.polygon.center[1], -self.pos[2]))
            temp.rotate(self.polygon.center, self.pos[2])
            if dist > 1.5:
                temp.draw(canvas, 5.0, tags=self.tags, fill='red')
            else:
                temp.draw(canvas, dist, tags=self.tags, fill='gray')

    def delete(self, canvas):
        canvas.delete(self.tags)
