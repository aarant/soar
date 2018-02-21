# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/robot/pioneer.py
""" A PioneerRobot class, for representing a real or simulated Pioneer 3 robot.

See the `MobileRobots documentation`_ for more information.

.. _MobileRobots documentation: http://www.mobilerobots.com/ResearchRobots/PioneerP3DX.aspx
"""
import re
from time import sleep
from threading import Thread
from math import pi, sqrt, atan2
from uuid import getnode

from soar.errors import SoarIOError
from soar.sim.geometry import Line, Pose, clip
from soar.sim.world import Polygon, Ray
from soar.robot.base import BaseRobot
from soar.robot.names import name_from_sernum
from soar.robot.arcos import *


def gen_tone_pairs(note_string, bpm=120):
    """ Given a string of musical notes separated by spaces and a tempo, generate a corresponding list of
    (duration, tone) pairs corresponding to each note.

    Args:
        note_string (str): A space-delimited list of notes. Notes should all be in the form `n/m(name)[#|b][octave]`. 
            Ex: `'1/4C'` produces a quarter note middle C. `'1/8A#7'` produces an eighth note A# in the 7th MIDI octave.
            `'1/4-'` produces a quarter rest. All of the MIDI notes in the range 1-127 can be played.
        bpm (int): The beats per minute or tempo to use to calculate durations.

    Returns:
        A list of (duration, tone) tuples where duration is in seconds, and tone
        is the corresponding MIDI number. Musical rest has a tone of 0.
    """
    notes = re.findall('([0-9]+)\/([0-9]+)([A-G]|-)(b|#)?(10|[0-9])?', note_string)
    tone_pairs = []
    note_offsets = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    alt_offsets = {'#': 1, 'b': -1, '': 0}
    for num, denom, name, alt, octave in notes:
        print(num, denom, name, alt, octave)
        num, denom = int(num), int(denom)
        octave = int(octave) if octave != '' else 5
        dur = (num/denom)/bpm*60
        if name == '-':  # Musical rest
            tone = 0
        else:
            tone = octave*12+note_offsets[name]+alt_offsets[alt]
        tone_pairs.append((dur, tone))
    print(tone_pairs)
    return tone_pairs


class PioneerRobot(BaseRobot):
    """ An abstract, universal Pioneer 3 robot. Instances of this class can be fully simulated, or used to communicate
    with an actual Pioneer3 robot over a serial port.

    Attributes:
        type (str): Always `'Pioneer3'`; used to identify this robot type.
        simulated (bool): If `True`, the robot is being simulated. Otherwise it should be assumed to be real.
        pose: An instance of :class:`soar.sim.geometry.Pose` representing the robot's `(x, y, theta)` position.
             In simulation, this is the actual position; on a real robot this is based on information from the encoders.
        world: An instance of :class:`soar.sim.world.World` or a subclass, or `None`, if the robot is real.
        FV_CAP (float): The maximum translational velocity at which the robot can move, in meters/second.
        RV_CAP (float): The maximum rotational velocity at which the robot can move, in radians/second.
        SONAR_MAX (float): The maximum distance that the sonars can sense, in meters.
        arcos: An instance of :class:`soar.robot.arcos.ARCOSClient` if the robot is real and has been loaded, otherwise
               `None`.
        serial_device (str): The device name of the serial port the robot is connected to, if it is real and has been
            been loaded, otherwise `None`.

    Args:
        **options: See `set_robot_options`.
    """
    def __init__(self, **options):
        self.FV_CAP = 1.5  # meters/second
        self.RV_CAP = 2 * pi  # radians/second
        BaseRobot.__init__(self, polygon=Polygon([(-0.034, -0.219), (0.057, -0.219), (0.139, -0.170), (0.196, -0.098),
                                                  (0.216, -0.009), (0.196, 0.079), (0.139, 0.150), (0.057, 0.190),
                                                  (-0.034, 0.190), (-0.051, 0.190), (-0.051, 0.150), (-0.153, 0.150),
                                                  (-0.223, 0.074), (-0.223, -0.103), (-0.153, -0.179), (-0.051, -0.179),
                                                  (-0.051, -0.219)], None, fill='black', dummy=True))
        self.type = 'Pioneer3'
        # Sonar poses relative to the robot's center
        self.sonar_poses = [Pose(0.08, 0.134, pi/2), Pose(0.122, 0.118, 5*pi/18),
                            Pose(0.156, 0.077, pi/6), Pose(0.174, 0.0266, pi/18),
                            Pose(0.174, -0.0266, -pi/18), Pose(0.156, -0.077, -pi/6),
                            Pose(0.122, -0.118, -5*pi/18), Pose(0.08, -0.134, -pi/2)]
        self.SONAR_MAX = 1.5  # meters
        self.arcos = None  # The ARCOS client, if connected
        self.serial_device = None  # The serial device, if connected
        self._fv = 0.0  # Internal forward velocity storage
        self._rv = 0.0  # Internal rotational velocity storage
        self._collided = False  # Private flag to check if the robot has collided
        self._sonars = None  # Super secret calculated sonars (shh)
        self._move_data = {'x': 0, 'y': 0, 'item': None}  # Drag data for the canvas
        self._turn_data = {'x': 0, 'y': 0, 'item': None}  # Drag data for the canvas
        self._serial_ports = None  # Serial ports to use when connecting with ARCOS; any if None
        self._last_x, self._last_y = 0, 0  # For dealing with encoder rollover
        self._x_sum, self._y_sum = 0, 0  # For dealing with encoder rollover
        self._ignore_brain_lag = False  # For making the step duration fixed
        self._raw_sonars = False  # Whether to cast out-of-range sonars to None
        self.set_robot_options(**options)  # Sets any options passed in on construction

    def to_dict(self):
        """ Return a dictionary representation of the robot, usable for serialization.

        This contains the robot type, position, sonar data, and forward and rotational velocities.
        """
        d = BaseRobot.to_dict(self)
        d.update({'sonars': self.sonars, 'collided': self._collided})
        return d

    def set_robot_options(self, **options):
        """ Set Pioneer3 specific options. Any unsupported keywords are ignored.

        Args:
            **options: Arbitrary robot options.
            serial_ports (list, optional): Sets the serial ports to try connecting to with the ARCOS client.
            ignore_brain_lag (bool): If `True`, a step will always be assumed to be 0.1 seconds long. Otherwise,
                whatever duration the controller tells the robot to step is how long a step lasts.
            raw_sonars (bool): If `True`, sonar values will not be recast to `None` when no distance was returned.
                `5.0` will be returned instead.
        """
        if 'serial_ports' in options:
            self._serial_ports = options['serial_ports']
        if 'ignore_brain_lag' in options:
            self._ignore_brain_lag = options['ignore_brain_lag']
        if 'raw_sonars' in options:
            self._raw_sonars = options['raw_sonars']

    @property
    def fv(self):
        """ `float` The robot's current translational velocity, in meters/second.

        Positive values indicate movement towards the front of the robot, and negative values indicate movement
        towards the back.

        Setting the robot's forward velocity is always subject to :attr:`soar.robot.pioneer.PioneerRobot.FV_CAP`.
        On a real robot, this is further limited by the hardware translational velocity cap.
        """
        return self._fv

    @fv.setter
    def fv(self, value):
        self._fv = clip(value, -self.FV_CAP, self.FV_CAP)
        if not self.simulated:  # For real robots, must send an ARCOS command
            try:
                self.arcos.send_command(VEL, int(self._fv*1000))  # Convert m/s to mm/s
            except Timeout as e:  # Recast arcos errors as Soar errors
                raise SoarIOError(str(e)) from e

    @property
    def rv(self):
        """ `float` The robot's current rotational velocity, in radians/second.

        Positive values indicate counterclockwise rotation (when viewed from above) and negative values indicate
        clockwise rotation.

        Setting the robot's rotational velocity is always subject to :attr:`soar.robot.pioneer.PioneerRobot.RV_CAP`.
        On a real robot, this is further limited by the hardware rotational velocity cap.
        """
        return self._rv

    @rv.setter
    def rv(self, value):
        self._rv = clip(value, -self.RV_CAP, self.RV_CAP)
        if not self.simulated:
            try:
                self.arcos.send_command(RVEL, int(self._rv * 180 / pi))  # Convert radians/sec to degrees/sec
            except Timeout as e:  # Recast arcos errors as Soar errors
                raise SoarIOError(str(e)) from e

    @property
    def sonars(self):
        """ (`list` of `float`) The latest sonar readings as an array.

        The array contains the latest distance sensed by each sonar, in order, clockwise from the robot's far left to
        its far right. Readings are given in meters and are accurate to the millimeter. If no distance was sensed by a
        sonar, its entry in the array will be `None`, unless the robot option `raw_sonars` has been set to `True`, in 
        which case its entry will be `5.0`.
        """
        if self.simulated:  # If simulating, grab the data from the latest calculated sonars
            if not self._sonars:  # If somehow this has been called before sonars are calculated, calculate them
                self.calc_sonars()
            return [round(s, 3) if s < self.SONAR_MAX else None for s in self._sonars]
        else:  # Otherwise grab the sonar data from the ARCOS Client
            if self._raw_sonars:  # Don't recast out-of-range values to None
                return [s/1000.0 for s in self.arcos.sonars[:8]]
            else:
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
            try:
                self.arcos.send_command(DIGOUT, int(clip(v, 0, 10)*25.5) | 0xff00)
            except Timeout as e:  # Recast arcos errors as Soar errors
                raise SoarIOError(str(e)) from e

    def get_distance_right(self):
        """ Get the perpendicular distance to the right of the robot.

        Returns:
            float: The perpendicular distance to the right of the robot, assuming there is a linear surface.
        """
        return self.get_distance_right_and_angle()[0]

    def get_distance_right_and_angle(self):
        """ Get the perpendicular distance and angle to a surface on the right.

        Returns:
            `(d, a)` where `d` is the perpendicular distance to a surface on the right, assuming it is linear, and `a`
            is the angle to that surface.
        """
        # Build a list of the points the sonars hit, or None if the distance was greater than the sonar max
        endpoints = [Ray(origin, d, dummy=True).p2 if d else None for (origin, d) in zip(self.sonar_poses, self.sonars)]
        return self.dist_and_angle(endpoints[6], endpoints[7])

    def get_distance_left(self):
        """ Get the perpendicular distance to the left of the robot.

        Returns:
            float: The perpendicular distance to the left of the robot, assuming there is a linear surface.
        """
        return self.get_distance_left_and_angle()[0]

    def get_distance_left_and_angle(self):
        """ Get the perpendicular distance and angle to a surface on the left.

        Returns:
            `(d, a)` where `d` is the perpendicular distance to a surface on the left, assuming it is linear, and `a`
            is the angle to that surface.
        """
        # Build a list of the points the sonars hit, or None if the distance was greater than the sonar max
        endpoints = [Ray(origin, d, dummy=True).p2 if d else None for (origin, d) in zip(self.sonar_poses, self.sonars)]
        return self.dist_and_angle(endpoints[0], endpoints[1])

    def dist_and_angle(self, h0, h1):  # Used to calculate perpendicular distance from surfaces
        if h0 and h1:
            l = Line(h0, h1, normalize=True)  # It is *essential* that the lines be normalized
            l_x, l_y, l_d = l.a, l.b, l.c
            return abs(l_d), pi / 2 - atan2(l_y, l_x)
        elif h0:
            (hx, hy) = h0
            return sqrt(hx * hx + hy * hy), None
        elif h1:
            (hx, hy) = h1
            return sqrt(hx * hx + hy * hy), None
        else:
            return self.SONAR_MAX, None

    def calc_sonars(self):  # Calculate the actual sonar ranges. Called once per simulated timestep
        self._sonars = [0]*len(self.sonar_poses)
        for i in range(len(self.sonar_poses)):
            # We take each sonar and build a ray longer than the world's max diagonal
            origin = self.sonar_poses[i]
            # Translate and turn by the robot's pose, then rotate about its center
            origin = origin.transform(self.pose).rotate(self.pose.point(), self.pose[2])
            sonar_ray = Ray(origin, 1.5*max(self.world.dimensions), dummy=True)

            # Find all collisions with objects that aren't the robot itself
            # Sonars only accurate to the millimeter, so let epsilon be 0.001 meters
            collisions = self.world.find_all_collisions(sonar_ray, condition=lambda obj: obj is not self, eps=1e-3)
            if collisions:  # Should always be True since the world has boundaries
                # Sort the collisions by distance to origin
                distances = [origin.distance(p) for _, p in collisions]
                distances.sort()
                self._sonars[i] = distances[0]  # Sonar reading is the distance to the nearest collision

    def draw(self, canvas):  # Draw the robot
        BaseRobot.draw(self, canvas)
        self.draw_sonars(canvas)

    def draw_sonars(self, canvas):  # Draw just the sonars
        canvas.delete(self.tags + 'sonars')  # Deleting a nonexistent tag is safe, so always delete the sonar lines
        if not self._sonars:
            self.calc_sonars()
        for dist, pose in zip(self._sonars, self.sonar_poses):
            origin = pose.transform(self.pose).rotate(self.pose.point(), self.pose[2])
            fill = 'firebrick2' if dist > self.SONAR_MAX else 'gray'
            sonar_ray = Ray(origin, dist, tags=self.tags+'sonars', fill=fill, width=1)
            sonar_ray.draw(canvas)

    def delete(self, canvas):  # TODO: Deprecate this in 2.0
        canvas.delete(self.tags, self.tags + 'sonars')  # Delete both the robot and sonar tags

    def check_if_collided(self):  # Check if the robot has collided, and set its collision flag accordingly
        if self.simulated:
            for obj in self.world:  # Check for collisions
                if obj is not self:
                    if self.collision(obj):  # If any collision occurs
                        self._collided = True
                        self.polygon.options['fill'] = 'red'
                        return True
            self._collided = False
            self.polygon.options['fill'] = 'black'
            return False
        else:
            return False

    def on_load(self):
        if self.simulated:
            self.arcos = None
            print('Connected to Pioneer p3dx-sh MIT_0042 (12.0 Volts) [Simulated]')
            print('Your robot\'s name is \'Denny\'')  # Hi Denny Freeman!
        else:
            try:
                self.arcos = ARCOSClient()
                self.arcos.connect(forced_ports=self._serial_ports)
                self.arcos.send_command(ENABLE, 0)  # We disable the motors so that the robot is easily movable
                # Continuously request IOpacs, and make sure we receive at least one
                self.arcos.send_command(IOREQUEST, 2)
                self.arcos.wait_or_timeout(self.arcos.io_event, 1.0, 'Could not access robot IO information')
                # Request a CONFIGpac and make sure we receive one
                self.arcos.send_command(CONFIG)
                self.arcos.wait_or_timeout(self.arcos.config_event, 1.0, 'Could not access robot configuration')
                config = self.arcos.config
                serial_num = str(getnode())
                battery_volts = self.arcos.standard['BATTERY'] / 10.0
                # Set the serial device for viewing
                self.serial_device = self.arcos.ser.name
                # Print the standard connection message and warn if the battery is low
                print('Connected to', ' '.join([config[field] for field in ['ROBOT_TYPE', 'SUBTYPE', 'NAME']]), 'on',
                      self.serial_device, '(%s Volts)' % battery_volts)
                print('Your robot\'s name is \'%s\'' % name_from_sernum(serial_num))
                if battery_volts < self.arcos.config['LOWBATTERY']/10.0:
                    printerr('WARNING: The robot\'s battery is low. Consider recharging or finding a new one.')
            except ARCOSError as e:  # If anything goes wrong, raise a SoarIOError
                raise SoarIOError(str(e)) from e

    def on_start(self):
        if not self.simulated:
            for _ in range(5):  # Try enabling motors a few times
                if self.arcos.standard['FLAGS'] & 0x1 != 0x1:  # If the motors have not been enabled
                    try:
                        self.arcos.send_command(ENABLE, 1)  # Re-enable them
                    except Timeout as e:  # Recast arcos errors as Soar errors
                        raise SoarIOError(str(e)) from e
                    sleep(1.0)
                else:  # If they have been, we're all set
                    break
            if self.arcos.standard['FLAGS'] & 0x1 != 0x1:  # If they still aren't enabled, raise an error
                raise SoarIOError('Unable to enable the robot\'s motors')
            try:
                self.arcos.send_command(SETO)
            except Timeout as e:  # Recast arcos errors as Soar errors
                raise SoarIOError(str(e)) from e

    def on_step(self, duration):
        if self._ignore_brain_lag:
            duration = 0.1  # If ignoring brain lag, fix the step duration
        if self.simulated:  # Move, check for collisions, and update the internal sonars
            if not self._collided:  # The robot only moves if it hasn't collided
                BaseRobot.on_step(self, duration)  # Do BaseRobot's simulated move and collision preemption
            self.check_if_collided()
            self.calc_sonars()
        else:  # Update the position information from the encoders
            # Assume that io.standard is relatively current, which is likely
            # Encoders can roll over, so keep track of the last x, y encoder reports and update accordingly
            x, y, t = self.arcos.standard['XPOS'], self.arcos.standard['YPOS'], self.arcos.standard['THPOS']
            d_x, d_y = x-self._last_x, y-self._last_y
            if d_x > 60000:  # A positive rollover occurred
                d_x -= 65536
            elif d_x < -60000:  # A negative rollover occurred
                d_x += 65536
            if d_y > 60000:  # A positive rollover occurred
                d_y -= 65536
            elif d_y < -60000:  # A negative rollover occurred
                d_y += 65536
            self._last_x, self._last_y = x, y
            self._x_sum += d_x
            self._y_sum += d_y
            self.pose = Pose(self._x_sum/1000.0, self._y_sum/1000.0, t*0.001534)

    def on_stop(self):
        if not self.simulated:
            try:
                self.arcos.send_command(STOP)  # Stop the robot from moving
                self.arcos.send_command(ENABLE, 0)  # Disable the motors after we've stopped
            except Timeout as e:  # Recast arcos errors as Soar errors
                raise SoarIOError(str(e)) from e

    def on_shutdown(self):
        if self.arcos:
            self.arcos.disconnect()

    # Mouse event bindings follow
    # Left-click-drag moves the robot, while right-click-drag rotates it

    def on_press_left(self, event):
        self._move_data['x'] = event.x
        self._move_data['y'] = event.y

    def on_release_left(self, event):
        self._move_data['x'] = 0
        self._move_data['y'] = 0

    def on_motion_left(self, event):
        delta_x = event.x - self._move_data["x"]
        delta_y = event.y - self._move_data["y"]
        self._move_data["x"] = event.x
        self._move_data["y"] = event.y
        real_d_x = delta_x / self.world.canvas.pixels_per_meter
        real_d_y = -delta_y / self.world.canvas.pixels_per_meter
        # Update the robot's real position, check for a collision, and redraw/recalcuate the robot and sonars
        self.pose = self.pose.transform((real_d_x, real_d_y, 0))
        self.polygon.recenter(self.pose)
        if self.check_if_collided():
            self.world.canvas.itemconfigure(self.tags, fill='red')
        else:
            self.world.canvas.itemconfigure(self.tags, fill='black')
        self.calc_sonars()
        self.draw(self.world.canvas)

    def on_press_right(self, event):
        self._turn_data['x'] = event.x
        self._turn_data['y'] = event.y

    def on_release_right(self, event):
        self._turn_data['x'] = 0
        self._turn_data['y'] = 0

    def on_motion_right(self, event):
        delta_x = event.x - self._turn_data["x"]
        delta_y = event.y - self._turn_data["y"]
        self._turn_data["x"] = event.x
        self._turn_data["y"] = event.y
        # Moving left or up rotates counterclockwise, right or down rotates clockwise
        theta = -delta_x*2*pi/150-delta_y*2*pi/150
        # Change the robot's position, rotate and redraw the polygon, and recalculate and redraw the sonars
        self.pose = self.pose.transform((0, 0, theta))
        self.polygon.rotate(self.polygon.center, theta)
        self.calc_sonars()
        self.draw(self.world.canvas)

    def play_notes(self, note_string, bpm=120, sync=False, _force_new_thread=True):
        """ Play a string of musical notes through the robot's piezoelectric speaker.

        Args:
            note_string (str): A space-delimited list of notes. Notes should all be in the form `n/m(name)[#|b][octave]`. 
                Ex: `'1/4C'` produces a quarter note middle C. `'1/8A#7'` produces an eighth note A# in the 7th MIDI octave.
                `'1/4-'` produces a quarter rest. All of the MIDI notes in the range 1-127 can be played.
            bpm (int): The beats per minute or tempo at which to play the notes.
            sync (bool): By default `False`, this determines whether notes are sent one by one, with synchronization
                performed by the function itself, or all at once.
            force_new_thread (bool): By default `True`, this determines whether to force the execution of this function
                to occur on a new thread.
        """
        if _force_new_thread:  # Force this function to run on a new thread
            Thread(target=lambda: self.play_notes(note_string, bpm, sync, False), daemon=True).start()
            return
        tone_pairs = gen_tone_pairs(note_string, bpm)
        b, total_duration = [], 0
        for dur, tone in tone_pairs:
            print(int(dur/0.02), min(127, tone))
            total_duration += dur
            b.extend([min(255, int(dur/0.02)), min(127, tone)])
            if len(b) == 19*2:  # If the buffer contains 19 notes
                b = [40] + b + [0, 0]  # Prepend the length byte and append the null terminator
                self.arcos.send_command(SAY, bytes(b), append_null=False)
                sleep(total_duration)
                b, total_duration = [], 0
        if b:  # If there are any more unsent notes
            b = [len(b)+2] + b + [0, 0] # Prepend the length byte and append the null terminator
            self.arcos.send_command(SAY, bytes(b), append_null=False)
            sleep(total_duration)

    def play_song(self, song_name):
        """ Play one of a number of songs through the robot's piezoelectric speaker.

        Args:
            song_name (str): The song to play. Must be one of `'reveille'`, `'daisy'`, or `'fanfare'`.
        """
        bpm, notes = {'reveille': (60, '1/8G. 1/8C6 1/16E6 1/16C6 1/8G 1/8E6.  1/8C6 1/16E6 1/16C6 1/8G 1/8E6. 1/8C6 1/16E6 1/16C6 1/8G 1/8C6. 1/4E6 1/8C6 1/8G. 1/8C6 1/16E6 1/16C6 1/8G 1/8E6. 1/8C6 1/16E6 1/16C6 1/8G 1/8E6. 1/8C6 1/16E6 1/16C6 1/8G 1/8G. 3/8C6 1/8E6. 1/8E6 1/8E6 1/8E6 1/8E6. 1/4G6 1/8E6 1/8C6. 1/8E6 1/8C6 1/8E6 1/8C6. 1/4E6 1/8C6 1/8E6. 1/8E6 1/8E6 1/8E6 1/8E6. 1/4G6 1/8E6 1/8C6. 1/8E6 1/8C6 1/8G 1/8G. 1/2C6.'),
                      'daisy': (60, '1/8F#6 1/8G6. 3/4A6. 3/4F#6. 3/4D6. 3/4A. 1/4B 1/4C#6 1/4D6. 1/2B 1/4D6. 1/1A 1/4D6. 3/4E6. 3/4A6. 3/4F#6. 3/4D6.'
                                '1/4B 1/4C#6 1/4D6. 1/2E6 1/4F#6. 1/1E6 1/4E6 1/4F#6. 1/4G6 1/4F#6 1/4E6. 1/2A6 1/4F#6. 1/4E6 3/4D6 1/4D6 1/4E6. 1/2F#6 1/4D6. 1/2B 1/4D6.'
                                '1/4B 3/4A 1/4C#6. 1/2D6 1/4F#6. 1/2E6 1/4A. 1/2D6 1/4F#6. 1/4E6 1/4F#6 1/4G6. 1/4A6 1/4F#6 1/4D6. 1/2E6 1/4F#6. 5/4D6.'),
                      'fanfare': (32, '1/24G 1/24C6 1/24E6. 1/16G6 1/16- 1/32G6 1/32- 1/32G6 1/32- 1/16G6 1/16-. 1/8E6 1/16E6 1/16E6 1/8E6. 1/8C6 1/8E6 1/8C6. 1/1G.')}[song_name]
        self.arcos.send_command(SOUNDTOG, 1)  # Enable the speaker
        sleep(1.0)
        self.play_notes(notes, bpm)

