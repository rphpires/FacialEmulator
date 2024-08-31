import platform


os_type = platform.system()
if os_type == "Windows":
    print("Windows")
elif os_type == "Linux":
    print("Linux")
elif os_type == "Darwin":
    print("MacOS")
else:
    print("Unknown")