f = open("photo1.jpg", "rb")
data = f.read()
f.close()
print(type(data), len(data))

