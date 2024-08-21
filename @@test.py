import requests



LISTA1 = [1, 2, 3]
LISTA2 = [5, 6, 7]

t = 1


if t not in LISTA1 + LISTA2:
    print('not')

else:
    print('IN')