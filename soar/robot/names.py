# Soar (Snakes on a Robot): A Python robotics framework.
# Copyright (C) 2017 Andrew Antonitis. Licensed under the LGPLv3.
#
# soar/robot/names.py
""" Generate a neutral name from an arbitrary serial number string. """
import random
from math import sqrt, ceil


names = ['Ariel', 'Bailey', 'Casey', 'Dallas', 'Eli', 'Frankie', 'Gabriel', 'Harley', 'Jayden', 'Kai', 'Lee', 'Mickey',
         'Neo', 'Ocean', 'Parris', 'Quinn', 'Reagan', 'Shiloh', 'Taylor', 'Udo', 'Val', 'Winter', 'Xue', 'Yoshi',
         'Zephyr', 'Narin', 'Ollie', 'Dakota', 'Marlie', 'Brooke', 'Shannon', 'Nour', 'Reese', 'Storm', 'Sydney',
         'Omari', 'Ola', 'Ryley', 'Esmai', 'Leslie', 'Finley', 'Hildred', 'Lynn', 'Shelby', 'Sequoia', 'Tashi',
         'Dominique', 'Garnet', 'Gray', 'Cameron']


def is_prime(n):
    if n < 4:
        return False if n == 1 else True
    for i in range(2, ceil(sqrt(n))):
        if n % i == 0:
            return False
    return True


def name_from_sernum(sernum):
    # Pull out only the digits from the serial number
    x = 0
    for y in map(lambda c: int(c), filter(lambda c: c.isdigit(), sernum)):
        x = x*10+y
    # Hash them with a Linear congruential generator
    return names[((a*x+b) % p) % m]


def test_collisions():
    collisions = 0
    for r in [range(i, i + 50) for i in range(2600, 2650 + 1)]:
        chosen = set()
        for i in r:
            name = name_from_sernum(str(i))
            if name in chosen:
                collisions += 1
            else:
                chosen.add(name)
    return collisions


def has_all():  # Test whether a hash setting contains every name for the expected serial number range
    return all([name in [name_from_sernum(str(i)) for i in range(2600, 2700)] for name in names])


m = len(names)
a = 74
b = 98
p = 149
# while test_collisions() > 25 or not has_all():
#     p = 1
#     while not is_prime(p):
#         p = random.randint(m+1, 3*m)
#     a = random.randint(2, p)
#     b = random.randint(2, p)
# print(a, b, p, test_collisions())
# for i in range(2600, 2700):
#     print(name_from_sernum(str(i)))
