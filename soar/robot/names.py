import random
from math import sqrt, ceil


def is_prime(n):
    if n < 4:
        return False if n == 1 else True
    for i in range(2, ceil(sqrt(n))):
        if n % i == 0:
            return False
    return True

names = ['Ariel', 'Bailey', 'Casey', 'Dallas', 'Eli', 'Frankie', 'Gabriel', 'Harley', 'Jayden', 'Kai', 'Lee', 'Mickey',
         'Neo', 'Ocean', 'Parris', 'Quinn', 'Reagan', 'Shiloh', 'Taylor', 'Udo', 'Val', 'Winter', 'Xue', 'Yoshi',
         'Zephyr']
m = len(names)
p = 1
while not is_prime(p):
    p = random.randint(m+1, 2*m)
a = random.randint(2, p)
b = random.randint(2, p)


def name_from_sernum(sernum):
    # Pull out only the digits from the serial number
    x = 0
    for y in map(lambda c: int(c), filter(lambda c: c.isdigit(), sernum)):
        x = x*10+y
    # Has them
    return names[((a*x+b) % p) % m]
