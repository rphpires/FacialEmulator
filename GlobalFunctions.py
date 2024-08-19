import random
import datetime
import platform
import socket

from Tracer import *
from WxsDbConnection import *

class GlobalInfo:
    gmt_timedelta = datetime.timedelta(hours=-3)
    gmt_offset = 0

def remove_accents_from_string(s):
    chars_table = {}

    if not s:
        return ''

    if not isinstance(s, str):
        trace(f'remove_special_characters_from_string: not string= {s}')
        return ''

    chars_table = {
        192: 'A', 193: 'A', 194: 'A', 195: 'A', 196: 'A', 197: 'A', 199: 'C', 200: 'E', 201: 'E', 202: 'E',
        203: 'E', 204: 'I', 205: 'I', 206: 'I', 207: 'I', 210: 'O', 211: 'O', 212: 'O', 213: 'O', 214: 'O',
        217: 'U', 218: 'U', 219: 'U', 220: 'U', 224: 'a', 225: 'a', 226: 'a', 227: 'a', 228: 'a', 229: 'a',
        231: 'c', 232: 'e', 233: 'e', 234: 'e', 235: 'e', 236: 'i', 237: 'i', 238: 'i', 239: 'i', 240: 'o',
        241: 'n', 242: 'o', 243: 'o', 244: 'o', 245: 'o', 246: 'o', 249: 'u', 250: 'u', 251: 'u', 252: 'u',
        253: 'y', 255: 'y', 160: ' ',
    }

    e = ''
    for c in s:
        if ord(c) <= 128:
            e += c
        else:
            e += chars_table.get(ord(c), '_')
    return e

def generate_mac_address():
    # O primeiro byte de um endereço MAC deve ser par e não pode ser 0 ou 255
    first_byte = random.randint(1, 127) * 2

    # Gera os próximos 5 bytes aleatórios
    mac_bytes = [first_byte] + [random.randint(0, 255) for _ in range(5)]

    # Formata o endereço MAC em um formato legível
    mac_address = ":".join(map(lambda x: "{:02x}".format(x), mac_bytes))
    return mac_address

def is_windows():
    return True
    global _is_windows_cache
    if _is_windows_cache == None:
        _is_windows_cache = not os.access('/proc/', os.R_OK)
    return _is_windows_cache

def get_localtime():
    if is_windows():
        return datetime.datetime.utcnow() + GlobalInfo.gmt_timedelta
    else:
        return datetime.datetime.today()
    
tracer = Tracer()
sql = DatabaseReader()

# def innitialize_tracer(port):
#     global tracer
#     tracer = Tracer(port)


import datetime, traceback

def trace(msg):
    tracer.trace_message(remove_accents_from_string(msg))


def trace_elapsed(msg, reference_utc_time):
    delta = datetime.datetime.utcnow() - reference_utc_time
    if not 'total_seconds' in dir(delta):
        tracer.trace_message(msg)
        return
    elapsed_ms = int((delta).total_seconds() * 1000)
    msg += " (%d ms)" % (elapsed_ms)
    tracer.trace_message(msg)


def info(msg):
    tracer.trace_message(msg)


def error(msg):
    tracer.trace_message("****" + msg)
    x = get_localtime()
    d = "%04d/%02d/%02d %02d:%02d:%02d.%06d " % (x.year, x.month, x.day, x.hour, x.minute, x.second, x.microsecond)
    sys.stderr.write("ERROR" + d + msg + '\n')
    sys.stdout.write("ERROR" + d + msg + '\n')

def format_date(x: datetime.datetime) -> str:
    if not x:
        return "-"
    return "%04d-%02d-%02d %02d:%02d:%02d.%03d" % (x.year, x.month, x.day, x.hour, x.minute, x.second, x.microsecond/1000)


ERROR_LOG_FILE = "TraceEmulator/ErrorLog.txt"

tracer.check_error_log_file()

def report_exception(e, do_sleep=True):
    x = get_localtime()
    header = "\n\n************************************************************************\n"
    header += "Exception date: %04d/%02d/%02d %02d:%02d:%02d.%06d \n" % (x.year, x.month, x.day, x.hour, x.minute, x.second, x.microsecond)
    # header += f"Version {CONTROLLER_VERSION}\n"
    header += "\n"

    sys.stdout.write(header)
    sys.stderr.write(header)
    traceback.print_exc(file=sys.stdout)
    if is_windows():
        f = open(ERROR_LOG_FILE, 'a')
        f.write(header)
        traceback.print_exc(file=f)
        f.close()
    else:
        traceback.print_exc(file=sys.stderr)

    try:
        t = "{}".format(type(threading.currentThread())).split("'")[1].split('.')[1]
    except IndexError:
        t = 'UNKNOWN'

    error("Bypassing exception at %s (%s)" % (t, e))
    error("**** Exception: <code>%s</code>" % (traceback.format_exc(), ))
    if do_sleep:
        error("Sleeping 2 seconds")
        time.sleep(2.0)


def generate_mac_address():
    octetos = [random.randint(0x00, 0xff) for _ in range(6)]
    mac = ':'.join(map(lambda x: '{:02x}'.format(x), octetos))
    
    return mac


def random_access_not_done():
    return random.randint(0, 99) < 20


def check_os():
    os_type = platform.system()
    if os_type == "Windows":
        return "Windows"
    elif os_type == "Linux":
        return "Linux"
    elif os_type == "Darwin":
        return "MacOS"
    else:
        return "Unknown"
    
def get_local_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip