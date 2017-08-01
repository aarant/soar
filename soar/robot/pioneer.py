""" Soar PioneerRobot class, for representing a real or simulated Pioneer 3 robot. """
from math import pi, sin, cos

from soar.errors import SoarIOError
from soar.sim.geometry import Point, Pose
from soar.sim.world import Polygon, Line, Ray
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
    """ An abstract, universal Pioneer 3 robot. Instances of this class can be fully simulated, or used to communicate
    with an actual Pioneer3 robot over a serial port.

    Attributes:
        type (str): Always `'Pioneer3'`; used to identify this robot type.
        simulated (bool): If `True`, the robot is being simulated. Otherwise it should be assumed to be real.
        pos: An instance of :class:`soar.sim.geometry.Pose` representing the robot's `(x, y, theta)` position.
             In simulation, this is the actual position; on a real robot this is based on information from the encoders.
        world: An instance of :class:`soar.sim.world.World` or a subclass, or `None`, if the robot is real.
        FV_CAP (float): The maximum translational velocity at which the robot can move, in meters/second.
        RV_CAP (float): The maximum rotational velocity at which the robot can move, in radians/second.
        SONAR_MAX (float): The maximum distance that the sonars can sense, in meters.
        arcos: An instance of :class:`soar.robot.arcos.ARCOSClient` if the robot is real and has been loaded, otherwise
               `None`.

    Args:
        **options: See `set_robot_options`.
    """
    def __init__(self, **options):
        BaseRobot.__init__(self, tags='pioneer')  # The only option we set is the tags keyword
        self.type = 'Pioneer3'
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
        self.arcos = None  # The ARCOS client, if connected
        self.__fv = 0.0  # Internal forward velocity storage
        self.__rv = 0.0  # Internal rotational velocity storage
        self.__collided = False  # Private flag to check if the robot has collided
        self.__sonars = None  # Super secret calculated sonars (shh)
        self.__drag_data = {'x': 0, 'y': 0, 'item': None}  # Drag data for the canvas
        self.__serial_ports = None
        self.set_robot_options(**options)

    def to_dict(self):
        """ Return a dictionary representation of the robot, usable for serialization.

        This contains the robot type, position, sonar data, and forward and rotational velocities.
        """
        d = BaseRobot.to_dict(self)
        d.update({'sonars': self.sonars})
        return d

    def set_robot_options(self, **options):
        """ Set Pioneer3 specific options. Any unsupported keywords are ignored.

        Args:
            serial_ports (list, optional): Sets the serial ports to try connecting to with the ARCOS client.
        """
        if 'serial_ports' in options:
            print('setting serial ports')  # TODO
            self.__serial_ports = options['serial_ports']

    @property
    def fv(self):
        """ `float` The robot's current translational velocity, in meters/second.

        Positive values indicate movement towards the front of the robot, and negative values indicate movement
        towards the back.

        Setting the robot's forward velocity is always subject to :attr:`soar.robot.pioneer.PioneerRobot.FV_CAP`.
        On a real robot, this is further limited by the hardware translational velocity cap.
        """
        return self.__fv

    @fv.setter
    def fv(self, value):
        self.__fv = clip(value, -self.FV_CAP, self.FV_CAP)
        if not self.simulated:  # For real robots, must send an ARCOS command
            self.arcos.send_command(VEL, int(self.__fv*1000))  # Convert m/s to mm/s

    @property
    def rv(self):
        """ `float` The robot's current rotational velocity, in radians/second.

        Positive values indicate counterclockwise rotation (when viewed from above) and negative values indicate
        clockwise rotation.

        Setting the robot's forward velocity is always subject to :attr:`soar.robot.pioneer.PioneerRobot.RV_CAP`.
        On a real robot, this is further limited by the hardware rotational velocity cap.
        """
        return self.__rv

    @rv.setter
    def rv(self, value):
        self.__rv = clip(value, -self.RV_CAP, self.RV_CAP)
        if not self.simulated:
            self.arcos.send_command(RVEL, int(self.__rv * 180 / pi))  # Convert radians/sec to degrees/sec

    @property
    def sonars(self):
        """ (`list` of `float`) The latest sonar readings as an array.

        The array contains the latest distance sensed by each sonar, in order, clockwise from the robot's far left to
        its far right. Readings are given in meters and are accurate to the millimeter. If no distance was sensed by a
        sonar, its entry in the array will be `None`.
        """
        if self.simulated:  # If simulating, grab the data from the latest calculated sonars
            if not self.__sonars:  # If somehow this has been called before sonars are calculated, calculate them
                self.calc_sonars()
            return [round(s, 3) if s < self.SONAR_MAX else None for s in self.__sonars]
        else:  # Otherwise grab the sonar data from the ARCOS Client
            return [s/1000.0 if s != 5000 else None for s in self.arcos.sonars[:8]]  # Convert mm to meters

    @property
    def analogs(self):
        """ Get the robot's 4 analog inputs, so long as it is real and not simulated, as a 4 tuple. """
        if self.simulated:
            raise SoarIOError('Cannot access the inputs of a simulated robot (yet)')  # TODO: CMax integration
        else:
            # Assume that the io information is relatively current
            return tuple([round(a*10.0/1023.0, 3) for a in self.arcos.io['ANALOGS'][4:]])

    def set_analog_voltage(self, v):
        """ Sets the robot's analog output voltage.

        Args:
            v (float): The output voltage to set. This is limited to the range of 0-10V.
        """
        if self.simulated:
            raise SoarIOError('Cannot set the analog output of a simulated robot (yet)')  # TODO: CMax integration
        else:  # Sent the analog-digital output required to read it later
            self.arcos.send_command(DIGOUT, int(clip(v, 0, 10)*25.5) | 0xff00)

    def calc_sonars(self):  # Calculate the actual sonar ranges. Called once per simulated timestep
        self.__sonars = [5.0]*len(self.sonar_poses)
        for i in range(len(self.sonar_poses)):
            # We take each sonar and build a ray as long as the world's max dimension
            origin = Pose(*self.sonar_poses[i])  # Make 3-tuple into a Pose
            origin = origin.transform(self.pos)  # Translate and change pose direction by the robot's pose
            origin.rotate(self.polygon.center, self.pos[2])  # Rotate about the polygon center
            sonar_ray = Ray(origin, max(self.world.dimensions), dummy=True)
            # Sonars only accurate to the millimeter, so let epsilon be 0.001 meters
            # Find all collisions with objects that aren't the robot itself
            collisions = self.world.find_all_collisions(sonar_ray, eps=1e-3, condition=lambda obj: obj is not self)
            if collisions:  # Should always be True since the world has boundaries
                # Sort the collisions by distance to origin
                distances = [origin.distance(p) for _, p in collisions]
                distances.sort()
                self.__sonars[i] = distances[0]  # Sonar reading is the distance to the nearest collision

    def move(self, pose):
        x, y, t = pose
        current_theta = self.pos[2]
        self.polygon.rotate(self.polygon.center, t-current_theta)
        self.pos = Pose(x, y, t)
        self.polygon.recenter(self.pos)

    def draw(self, canvas):  # Draw the robot
        self.polygon.draw(canvas)
        self.draw_sonars(canvas)

    def draw_sonars(self, canvas):  # Draw just the sonars
        if not self.__sonars:
            self.calc_sonars()
        for dist, pose in zip(self.__sonars, self.sonar_poses):
            origin = Pose(*pose)
            origin = origin.transform((self.polygon.center[0], self.polygon.center[1], self.pos[2]))
            origin.rotate(self.polygon.center, self.pos[2])
            fill = 'red' if dist > self.SONAR_MAX else 'gray'
            sonar_ray = Ray(origin, dist, tag=self.tags+'sonars', fill=fill, width=1)
            sonar_ray.draw(canvas)

    def collision(self, other, eps=1e-8):   # Determine whether the robot collides with an object
        if isinstance(other, PioneerRobot):
            return self.polygon.collision(other.polygon, eps=eps)
        elif isinstance(other, Polygon) or isinstance(other, Line):
            return self.polygon.collision(other, eps=eps)

    def check_if_collided(self):  # Check if the robot has collided, and set its collision flag accordingly
        if self.simulated:
            for obj in self.world:  # Check for collisions
                if obj is not self:
                    if self.collision(obj):  # If any collision occurs
                        self.__collided = True
                        self.polygon.options['fill'] = 'red'
                        return True
            self.__collided = False
            self.polygon.options['fill'] = 'black'
            return False
        else:
            return False

    def delete(self, canvas):
        canvas.delete(self.tags, self.tags + 'sonars')  # Delete both the robot and sonar tags

    def on_load(self):
        if self.simulated:
            self.arcos = None
            print('Connected to Pioneer p3dx-sh MIT_0042 \'Denny\' (12.0V) [Simulated]')  # Hi Denny Freeman!
        else:
            try:
                self.arcos = ARCOSClient()
                self.arcos.connect(forced_ports=self.__serial_ports)
                self.arcos.send_command(ENABLE, 0)  # We disable the motors so that the robot is easily movable
                # Continuously request IOpacs, and make sure we receive at least one
                self.arcos.send_command(IOREQUEST, 2)
                self.arcos.wait_or_timeout(self.arcos.io_event, 1.0, 'Could not access robot IO information')
                # Request a CONFIGpac and make sure we receive one
                self.arcos.send_command(CONFIG)
                self.arcos.wait_or_timeout(self.arcos.config_event, 1.0, 'Could not access robot configuration')
                config = self.arcos.config
                serial_num = config['SERNUM']
                battery_volts = self.arcos.standard['BATTERY'] / 10.0
                # Print the standard connection message and warn if the battery is low
                print('Connected to ' + ' '.join([config[field] for field in ['ROBOT_TYPE', 'SUBTYPE', 'NAME']])
                      + ' \'' + name_from_sernum(serial_num) + '\' (' + str(battery_volts) + ')')
                if battery_volts < self.arcos.config['LOWBATTERY']/10.0:
                    printerr('WARNING: The robot\'s battery is low. Consider recharging or finding a new one.')
            except ARCOSError as e:  # If anything goes wrong, raise a SoarIOError
                raise SoarIOError(str(e)) from e

    def on_start(self):
        if not self.simulated:
            self.arcos.send_command(ENABLE, 1)  # Re-enable the motors on start

    def on_step(self, duration):
        if self.simulated:  # Do the move update (with collision preemption) and sonar calculation
            if not self.__collided:  # The robot only moves if it hasn't collided
                # Try and make sure that the robot can actually move to its new location
                # Turn, then translate
                theta = self.pos[2]
                d_t = self.rv*duration
                new_theta = theta+d_t
                d_x, d_y = self.fv*cos(theta)*duration, self.fv*sin(theta)*duration
                new_pos = self.pos.transform((d_x, d_y, d_t))
                self.polygon.recenter(new_pos)
                # For now, build a line between the old and new position and check if it collides with anything
                l = Line((self.pos[0], self.pos[1]), (new_pos[0], new_pos[1]), dummy=True)
                collisions = self.world.find_all_collisions(l, condition=lambda obj: obj is not self)
                if collisions:  # If there was a collision, prevent the robot from overshooting it
                    collisions.sort(key=lambda tup: self.pos.distance(tup[1]))
                    safe_pos = Pose(*collisions[0][1], new_pos[2])
                    offset = Point(0.21, 0.0)  # Robot radius is 0.22 meters
                    offset.rotate((0, 0), new_pos[2])
                    safe_pos.sub(offset)
                    self.pos = safe_pos
                    self.polygon.recenter(safe_pos)
                else:  # Set the robot's position and move the polygon accordingly
                    self.pos = new_pos
                    self.polygon.rotate(self.polygon.center, d_t)
            self.check_if_collided()
            self.calc_sonars()  # Always calculate the internal sonars
        else:  # If working with a real robot, update the encoder information
            # Assume that io.standard is relatively current, which is likely
            # TODO: Encoders can roll over
            x, y, t = self.arcos.standard['XPOS'], self.arcos.standard['YPOS'], self.arcos.standard['THPOS']
            self.pos = Pose(x/1000.0, y/1000.0, t*0.001534)

    def on_stop(self):
        if not self.simulated:
            self.arcos.send_command(STOP)  # Stop the robot from moving
            self.arcos.send_command(ENABLE, 0)  # Disable the motors after we've stopped

    def on_shutdown(self):
        if self.arcos:
            self.arcos.disconnect()

    def on_press(self, event):  # Called when the robot is clicked (this method is bound by the canvas)
        self.__drag_data['x'] = event.x
        self.__drag_data['y'] = event.y

    def on_release(self, event):  # Called when the robot is released (this method is bound by the canvas)
        self.__drag_data['x'] = 0
        self.__drag_data['y'] = 0

    def on_motion(self, event):  # Called when the robot is dragged to a new location (bound by the canvas)
        delta_x = event.x - self.__drag_data["x"]
        delta_y = event.y - self.__drag_data["y"]
        self.world.canvas.delete(self.tags + 'sonars')
        self.__drag_data["x"] = event.x
        self.__drag_data["y"] = event.y
        real_d_x = delta_x / self.world.canvas.pixels_per_meter
        real_d_y = -delta_y / self.world.canvas.pixels_per_meter
        # Update the robot's real position, check for a collision, and redraw the sonars
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
