from soar.robot.pioneer import PioneerRobot

robot = PioneerRobot()

# this function is called when the brain is (re)loaded
def on_load():
    pass

# this function is called when the start button is pushed
def on_start():
    robot.readings = []

# this function is called 10 times per second
def on_step():
    #io.sonar_monitor(True)
    
    #read in the sonar readings from the robot.
    #s will be a list of 8 values, with the value at index
    #0 representing the left-most sonar
    s = robot.signal('sonars')

    #print the reading from the central sonar
    distance = s[3]
    print(distance)
    robot.readings.append(distance)

    #BANG BANG
    if distance > 0.6:
        velocity = 1.0
    else:
        velocity = -1.0

    #PROPORTIONAL
    k = 2.5
    velocity = k * (distance - 0.6)
    
    io.set_forward(velocity)
    io.set_rotational(0)

# called when the stop button is pushed
def on_stop():
    PlotWindow().plot(robot.readings) 
    pass

# called when brain or world is reloaded (before setup)
def on_shutdown():
    pass
