""" Soar v0.11.0 Pioneer Robot Model

Class for representing a Pioneer 3 robot, real or simulated.
"""
from math import pi, sin, cos

from soar.errors import SoarIOError
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
        type (str): Always 'Pioneer3'; used to identify this robot type.
        simulated (bool): If `True`, the robot is being simulated. Otherwise it should be assumed to be real.
        pos: An instance of :class:`soar.sim.geometry.Pose` representing the robot's ``(x, y, theta)`` position.
             In simulation, this is the actual position; on a real robot this is based on information from the encoders.
        world: An instance of :class:`soar.sim.world.World` or a subclass of it, or ``None``, if the robot is real.
        FV_CAP (float): The maximum translational velocity at which the robot can move, in meters/second.
        RV_CAP (float): The maximum rotational velocity at which the robot can move, in radians/second.
        SONAR_MAX (float): The maximum distance that the sonars can sense, in meters.
        arcos: An instance of :class:`soar.robot.arcos.ARCOSClient` if the robot is real and has been loaded, otherwise
               ``None``.
    """
    def __init__(self):
        BaseRobot.__init__(self)
        self.type = 'Pioneer3'
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
        self._fv = 0.0
        self._rv = 0.0
        self.collided = False
        self.arcos = None
        self._sonars = None  # Super secret calculated sonars (shh)
        self._drag_data = {'x': 0, 'y': 0, 'item': None}

    def to_dict(self):
        """ Return a dictionary representation of the robot, usable for serialization.

        This contains the robot type, position, sonar data, and forward and rotational velocities.
        """
        d = BaseRobot.to_dict(self)
        d.update({'sonars': self.sonars})
        return d

    @property
    def fv(self):
        """ Get or set the robot's current translational velocity, in meters/second. Positive values indicate movement
        towards the front of the robot, and negative values indicate movement towards the back.

        Setting the robot's forward velocity is always subject to :attr:`soar.robot.pioneer.PioneerRobot.FV_CAP`.
        """
        return self._fv

    @fv.setter
    def fv(self, value):
        self._fv = clip(value, -self.FV_CAP, self.FV_CAP)
        if not self.simulated:  # For real robots, must send an ARCOS command
            self.arcos.send_command(VEL, int(self._fv*1000))  # Convert m/s to mm/s

    @property
    def rv(self):
        """ Get or set the robot's current rotational velocity, in radians/second. Positive values indicate
        counterclockwise rotation (when viewed from above) and negative values indicate clockwise rotation.

        Setting the robot's forward velocity is always subject to :attr:`soar.robot.pioneer.PioneerRobot.RV_CAP`.
        """
        return self._rv

    @rv.setter
    def rv(self, value):
        self._rv = clip(value, -self.RV_CAP, self.RV_CAP)
        if not self.simulated:
            self.arcos.send_command(RVEL, int(self._rv * 180 / pi))  # Convert radians/sec to degrees/sec

    @property
    def sonars(self):
        """ Return the latest sonar readings as an array.

        The array contains the latest distance sensed by each sonar, in order, clockwise from the robot's far left to
        its far right. Readings are given in meters and are accurate to the millimeter. If no distance was sensed by a
        sonar, its entry in the array will be ``None``.
        """
        if self.simulated:  # If simulating, grab the data from the latest calculated sonars
            if not self._sonars:  # If somehow this has been called before sonars are calculated, calculate them
                self.calc_sonars()
            return [s if s < self.SONAR_MAX else None for s in self._sonars]
        else:  # Otherwise grab the sonar data from the ARCOS Client
            return [s/1000.0 if s != 5000 else None for s in self.arcos.sonars[:8]]  # Convert mm to meters

    @property
    def analogs(self):
        """ Get the robot's 4 analog inputs, so long as it is real and not simulated, as a 4 tuple. """
        if self.simulated:
            raise SoarIOError('Cannot access the inputs of a simulated robot (yet)')  # TODO: CMax integration
        else:
            # Assume that the io information is relatively current
            return tuple([a*10.0/1023.0 for a in self.arcos.io['ANALOGS']])

    def calc_sonars(self):  # Calculate the actual sonar ranges. Called once per simulated timestep
        self._sonars = [5.0]*len(self.sonar_poses)
        for i in range(len(self.sonar_poses)):
            # We take each sonar and build a line as long as the world's max dimension, and check for collisions
            temp = Pose(*self.sonar_poses[i])
            temp = temp.transform(self.pos)
            temp.rotate(self.polygon.center, self.pos[2])
            x0, y0 = temp[0], temp[1]
            x1, y1 = x0 + max(self.world.dimensions) * cos(temp[2]), y0 + max(self.world.dimensions) * sin(temp[2])
            ray = Line((x0, y0), (x1, y1))
            intersects = []
            for obj in self.world:
                if obj is not self:
                    p = ray.collision(obj)
                    if p:
                        if type(p) == list:
                            print('LIST')
                            for q in p:
                                q = Point(*q)
                                intersects.append((q, q.distance(temp)))
                        else:
                            p = Point(*p)
                            intersects.append((p, p.distance(temp)))
            intersects.sort(key=lambda t: t[1])  # Find the nearest collision
            if len(intersects) > 0:
                p, distance = intersects[0]
                self._sonars[i] = distance

    def move(self, pose):
        x, y, t = pose
        current_theta = self.pos[2]
        self.polygon.rotate(self.polygon.center, t-current_theta)
        self.pos = Pose(x, y, t)
        self.polygon.recenter(self.pos)

    def draw(self, canvas):  # Draw the robot's central polygon
        self.polygon.draw(canvas)
        self.draw_sonars(canvas)

    def draw_sonars(self, canvas):  # Draw the sonars
        if not self._sonars:
            self.calc_sonars()
        for dist, pose in zip(self._sonars, self.sonar_poses):
            temp = Pose(*pose)
            temp = temp.transform((self.polygon.center[0], self.polygon.center[1], self.pos[2]))
            temp.rotate(self.polygon.center, self.pos[2])
            if dist > self.SONAR_MAX:
                temp.draw(canvas, dist, tags=self.tags + 'sonars', fill='red')
            else:
                temp.draw(canvas, dist, tags=self.tags + 'sonars', fill='gray')

    def collision(self, obj):   # Determine whether the robot collides with an object
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

    def check_if_collided(self):  # Check if the robot has collided, and set its collision flag
        if self.simulated:
            for obj in self.world:  # Check for collisions
                if obj is not self:
                    if self.collision(obj):
                        self.collided = True
                        self.polygon.options['fill'] = 'red'
                        return True
            self.collided = False
            self.polygon.options['fill'] = 'black'
            return False
        else:
            return False

    def delete(self, canvas):
        canvas.delete(self.tags, self.tags + 'sonars')

    def on_load(self):
        if self.simulated:
            self.arcos = None
            print('Connected to Pioneer p3dx-sh MIT_0042 \'Denny\' (12.0V) [Simulated]')  # Denny Easter egg
        else:
            try:
                self.arcos = ARCOSClient()
                self.arcos.connect()
                self.arcos.send_command(ENABLE, 0)  # We disable the motors so that the robot is easily movable
                self.arcos.send_command(IOREQUEST, 2)  # Continuously request IOpacs
                self.arcos.wait_for(self.arcos.io_event, 1.0, 'Could not access robot IO information')
                self.arcos.send_command(CONFIG)
                self.arcos.wait_for(self.arcos.config_event, 1.0, 'Could not access robot configuration')
                config = self.arcos.config
                serial_num = config['SERNUM']
                battery_volts = self.arcos.standard['BATTERY'] / 10.0
                print('Connected to ' + ' '.join([config[field] for field in ['ROBOT_TYPE', 'SUBTYPE', 'NAME']])
                      + ' \'' + name_from_sernum(serial_num) + '\' (' + str(battery_volts) + ')')
                if battery_volts < self.arcos.config['LOWBATTERY']/10.0:  # TODO: LOWBATTERY's value, around 11.5V?
                    printerr('WARNING: The robot\'s battery is low. Consider recharging or finding a new one.')
            except ARCOSError as e:  # If anything goes wrong, raise a SoarIOError
                raise SoarIOError(str(e)) from e

    def on_start(self):
        if not self.simulated:
            self.arcos.send_command(ENABLE, 1)  # Re-enable the motors on start

    def on_step(self, step_duration):
        if self.simulated:  # Do the move update and sonar calculation
            if not self.collided:
                d_t = self.rv * step_duration
                BaseRobot.on_step(self, step_duration)  # Change self.pos
                self.polygon.rotate(self.polygon.center, d_t)  # Rotate the polygon
                self.polygon.recenter(self.pos)  # Recenter the polygon
            self.check_if_collided()
            self.calc_sonars()  # Always calculate the internal sonars
        else:  # If working with a real robot, update the encoder information
            # Assume that io.standard is relatively current, which is likely
            # TODO: Encoders can roll over
            x, y, t = self.arcos.standard['XPOS'], self.arcos.standard['YPOS'], self.arcos.standard['THPOS']
            self.pos = Pose(x/1000.0, y/1000.0, t*0.001534)

    def on_stop(self):
        if not self.simulated:
            self.arcos.send_command(STOP)
            self.arcos.send_command(ENABLE, 0)  # Disable the motors after we've stopped

    def on_shutdown(self):
        if self.arcos:
            self.arcos.disconnect()

    def on_press(self, event):
        self._drag_data['x'] = event.x
        self._drag_data['y'] = event.y

    def on_release(self, event):
        self._drag_data['x'] = 0
        self._drag_data['y'] = 0

    def on_motion(self, event):
        delta_x = event.x - self._drag_data["x"]
        delta_y = event.y - self._drag_data["y"]
        self.world.canvas.delete(self.tags + 'sonars')
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        real_d_x = delta_x / self.world.canvas.pixels_per_meter
        real_d_y = -delta_y / self.world.canvas.pixels_per_meter
        self.pos = self.pos.transform((real_d_x, real_d_y, 0))
        self.polygon.recenter(self.pos)
        if self.check_if_collided():
            self.world.canvas.itemconfigure(self.tags, fill='red')
        else:
            self.world.canvas.itemconfigure(self.tags, fill='black')
        self.calc_sonars()
        items = self.world.canvas.find_withtag(self.tags)
        for item in items:
            self.world.canvas.move(item, delta_x, delta_y)
        self.world.canvas.delete(self.tags + 'sonars')
        self.draw_sonars(self.world.canvas)
