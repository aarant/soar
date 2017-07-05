a = 42
b = 77
p = 93

names = ['Andy']*10

def name(s):
    x = ''
    for c in s:
        if c.isdigit():
            x += c
    x = int(x)
    h = ((a*x+b) % p) % 10
    return names[h]
