from math import pi, sin, cos

from soar.controller import SoarIOError
from soar.sim.geometry import Point, Pose
from soar.sim.world import Polygon, Line
from soar.robot.arcos import *
from soar.robot.base import BaseRobot
from soar.robot.names import name_from_sernum


def clip(value, m1, m2):  # Clips a value between a min and a max
    lower = min(m1, m2)
    upper = max(m1, m2)
    if value > upper:
        return upper
    elif value < lower:
        return lower
    else:
        return value


class PioneerRobot(BaseRobot):
    """ An abstract, universal Pioneer 3 robot--that is, instances of this class can be fully simulated or used to
    connect with an actual Pioneer 3 robot.

    Attributes:
        FV_CAP (float): The maximum translational velocity at which the robot can move, in meters/second.
        RV_CAP (float): The maximum rotational velocity at which the robot can move, in radians/second.
        SONAR_MAX (float): The maximum distance that the sonars can sense, in meters.
    """
    def __init__(self):
        BaseRobot.__init__(self)
        self.tags = 'pioneer'
        self.polygon = Polygon([(-0.034120395949525435, -0.21988658579769327),
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
                               None, fill='black', tags=self.tags)
        self.sonar_poses = [(0.013008094924083946, 0.20348830058744055, 1.57),
                            (0.09972419534513688, 0.18369591654177436, 1.21),
                            (0.16926510857462107, 0.12823888880268036, 0.6731984257692414),
                            (0.20785740388410556, 0.04810116184969754, 0.2243994752564138),
                            (0.20785740388410556, -0.040845004669412655, -0.2243994752564138),
                            (0.16926510857462096, -0.12098273162239542, -0.6731984257692414),
                            (0.09972419534513688, -0.18157953736419125, -1.21),
                            (0.013008094924083946, -0.20651169941255937, -1.57)]
        self.FV_CAP = 1.5  # meters/second
        self.RV_CAP = 2*pi  # radians/second
        self.SONAR_MAX = 1.5  # meters
        self.collided = False
        self.io = None

    def set_forward_velocity(self, fv):
        """ Sets the robot's forward velocity subject to `FV_CAP`.

        Args:
            fv (float): The new forward velocity, in meters/second. Positive values move forwards and negative values
                        move backwards.
        """
        if self.world:
            self.fv = clip(fv, -self.FV_CAP, self.FV_CAP)
        else:
            self.io.send_command(VEL, int(fv*1000))  # Convert m/s to mm/s

    def set_rotational_velocity(self, rv):
        """ Sets the robot's rotational velocity subject to `RV_CAP`.

        Args:
            rv (float): The new rotational velocity, in radians/second. Positive values move counterclockwise and
                        negative ones move clockwise.
        """
        if self.world:
            self.rv = clip(rv, -self.RV_CAP, self.RV_CAP)  # Clip velocities
        else:
            self.io.send_command(RVEL, int(rv*180/pi))  # Convert radians/sec to degrees/sec

    def get_sonars(self):
        """ Returns the latest sonar distances as an array.

        Returns:
            A list containing The latest distance sensed by each sonar, in order from the robot's left clockwise to its
            right, in meters, accurate to the millimeter. If no distance was sensed by a sonar, its value will be 5.0.
        """
        if self.world:  # If simulating, we need to build each sonar ray and check for collisions TODO: Sonar miss value
            sonars = [5.0]*8
            for i in range(len(self.sonar_poses)):
                # We take each sonar and build a line as long as the world's max dimension, and check for collisions
                temp = Pose(*self.sonar_poses[i])
                temp = temp.transform((self.polygon.center[0], self.polygon.center[1], self.pos[2]))
                temp.rotate(self.polygon.center, self.pos[2])
                x0, y0 = temp[0], temp[1]
                x1, y1 = x0 + max(self.world.dimensions) * cos(temp[2]), y0 + max(self.world.dimensions) * sin(temp[2])
                ray = Line((x0, y0), (x1, y1))
                intersects = []
                for obj in self.world:
                    if obj is not self:
                        p = ray.collision(obj)
                        if p:
                            p = Point(*p)
                            intersects.append((p, p.distance(temp)))
                intersects.sort(key=lambda t: t[1])  # Find the nearest collision
                if len(intersects) > 0:
                    p, distance = intersects[0]
                    if distance < self.SONAR_MAX:
                        sonars[i] = int(distance*1000)/1000
        else:  # Otherwise grab the sonar data from the ARCOS Client
            sonars = [s/1000.0 for s in self.io.sonars[:8]]  # Convert mm to meters
        return sonars

    def move(self, pose):
        x, y, t = pose
        current_theta = self.pos[2]
        self.polygon.rotate(self.polygon.center, t-current_theta)
        self.pos = Pose(x, y, t)

    def draw(self, canvas):
        self.polygon.recenter(self.pos)
        self.polygon.draw(canvas)
        sonars = self.get_sonars()
        for dist, pose in zip(sonars, self.sonar_poses):
            temp = Pose(*pose)
            temp = temp.transform((self.polygon.center[0], self.polygon.center[1], self.pos[2]))
            temp.rotate(self.polygon.center, self.pos[2])
            if dist > 1.5:
                temp.draw(canvas, max(self.world.dimensions), tags=self.tags, fill='red')  # TODO: Change max dimensions
            else:
                temp.draw(canvas, dist, tags=self.tags, fill='gray')

    def collision(self, obj):
        if isinstance(obj, Line):
            lines = []
            for i in range(len(self.polygon)-1):
                p1, p2 = self.polygon[i], self.polygon[i+1]
                lines.append(Line(p1, p2))
            lines.append(Line(self.polygon[len(self.polygon)-1], self.polygon[0]))
            for line in lines:
                intersect = line.collision(obj)
                if intersect and line.has_point(intersect):
                    return intersect
            return None

    def delete(self, canvas):
        canvas.delete(self.tags)

    def on_load(self):
        if self.world:
            self.io = None
            print('Connected to PLACEHOLDER \'Denny\'')
        else:
            try:
                self.io = ARCOSClient()
                self.io.connect()
                self.io.send_command(CONFIG)
                self.io.wait_for(self.io.config_event, 1.0, 'Error retrieving robot configuration')
                config = self.io.config_pac
                serial_num = config['SERNUM']
                print('Connected to ' + ' '.join([config[field] for field in ['ROBOT_TYPE', 'SUBTYPE', 'NAME']])
                      + ' \'' + name_from_sernum(serial_num) + '\'')
                self.io.send_command(ENABLE, 0)  # We disable the motors so that the robot is easily movable
            except ARCOSError as e:
                raise SoarIOError(str(e)) from e

    def on_start(self):
        if not self.world:
            self.io.send_command(ENABLE, 1)  # Re-enable the motors on start

    def on_step(self, step_duration):
        if self.world:  # Collision detection; TODO: Might need to do more
            if self.collided:
                return
            else:
                d_t = self.rv * step_duration
                self.polygon.rotate(self.polygon.center, d_t)
                for obj in self.world:
                    if obj is not self:
                        if self.collision(obj):
                            self.collided = True
                            self.polygon.options['fill'] = 'red'
        else:  # If working with a real robot, update the encoder information
            try:  # Wait for a standard SIP to come in, and update the wheel-encoder position
                self.io.wait_for(self.io.standard_event, 0.1)
            except Timeout:
                pass
            else:
                x, y, t = self.io.standard['XPOS'], self.io.standard['YPOS'], self.io.standard['THPOS']
                self.pos = Pose(x/1000.0, y/1000.0, t*0.001534)
        BaseRobot.on_step(self, step_duration)

    def on_stop(self):
        if not self.world:
            self.io.send_command(STOP)
            self.io.send_command(ENABLE, 0)  # Disable the motors after we've stopped

    def on_shutdown(self):
        if self.io:
            self.io.disconnect()
