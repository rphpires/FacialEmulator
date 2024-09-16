import os
import sys
import threading
import time

import scripts.GlobalFunctions as GlobalFunctions

TRACE_FILE_NAME = 'TraceEmulator/trace.html'

ERROR_FILE_MAX_SIZE = 1 * 1024 * 1024  # in bytes
ERROR_FILE_NAME = 'TraceEmulator/ErrorLog.txt'

# for colors reference, see https://www.rapidtables.com/web/color/html-color-codes.html
color_table = {
    '_MainThread':              "lavenderblush",
    'SocketsAccepter':          "floralwhite",

    # Messages from server: gray
    "ServerMessageProcessor":   "gray",
    "ServerMessageProcessor_Polling":   "dimgray",

    # Readers threads: Brown
    "AccessRequestProcessor":   "chocolate",

    # Key general threads: blue
    'EventsHandler':            "royalblue",
    'DatabaseHandler':          "lightsteelblue",
    'ScheduledCommandsRunner':  "deepskyblue",

    # Site Controller communication: red
    'ControllersCommunication': "crimson",
    'ControllerMessageReader':  "indianred",
    'ControllersPoller':        "lightcoral",
    'DistributedLock':          "darksalmon",

    # Unused
    'BatteryStatusPoller':      "darkred",
    'CpuLedBlinker':            "darkred",
    'ResetListener':            "darkred",
    'PowerSourcePoller':        "darkred",

    # LocalControllers aux threads: yellow
    "IoPoller":                 "yellow",
    "IoIpSettingsUpdate":		"khaki",
    'IoTcpCommunicationServer': "lightgoldenrodyellow",

    # LocalControllers Communication: green  / cyan
    "IoCanSender":              "green",
    "IoCanReceiver":            "darkgreen",
    'IoUdpMessageReceiver':     "green",
    'IoSiritReceiver':          "green",
    # 'IoIpFilesSender':          "lime",
    'IoTcpCommunication':       "seagreen",
    'IoTcpCommunication_IPTerminal':       "lightseagreen",
    'IoBacnetCommunication':    "olive",
    'IoControlIDCommunication': "olivedrab",
    'IoVertxFiles':             "lightgreen",
    'IoVertxCommunication':     "mediumseagreen",
    'IoMorphoCommunication':    "lime",
    'IoAxisCommunication':      "mediumseagreen",
    'IoZKTecoCommunication':      "mediumseagreen",

    'IoUpdatesSenderUsers': "lawngreen",
    'IoUpdatesSender': "springgreen",
    'IoUpdatesSenderUsersFastQueue': "palegreen",

    'TcpReaderListenerHandler': "lime",
    'TcpReaderListener':        "lawngreen",

}

shell_colors = {
    "gray":     "1;30",
    "darkred":  "31",
    "red":      "1;31",
    "green":    "32",
    "darkgreen": "1;32",
    "brown":    "33",
    "yellow":   "1;33",
    "blue_dark": "34",
    "blue":     "1;34",
    "purple":   "35",
    "magenta":  "1;35",
    "cyan":     "36",
    "lightcyan": "1;36",
    "white":    "37",
    "normal":   "0",
}

html_to_shell_colors = {
    "lightskyblue": "purple",
    "darkorchid": "purple",
    "orchid": "magenta",
    "chocolate": "brown",
    "mediumseagreen": "green",
    "seagreen": "green",
    "lightseagreen": "green",
    "olive": "green",
    "olivedrab": "green",
    "lightgreen": "green",
    "springgreen": "green",
    "lime": "green",
    "lawngreen": "green",
}


class Tracer:
    def __init__(self):
        self.trace_file = None

        self.trace_files_limit_count = 100
        self.trace_files_limit_size = 3 * 1024 * 1024

        self.html_trace = True
        self.screen_trace = True
        self.trace_lock = threading.Condition()

        self.error_to_file = True
        self.last_flush = 0

        self.trace_lock.acquire()
        try:
            sys.stderr.tell()
            sys.stderr = open(ERROR_FILE_NAME, "a")
        except Exception:
            self.error_to_file = False
        self.trace_lock.release()
        self.__last_color = None

        os.makedirs('TraceEmulator', exist_ok=True)

        if os.getenv('ENABLE_TRACE'):
            self.screen_trace = True

    def set_screen_trace(self, value):
        self.screen_trace = value

    def set_html_trace(self, value):
        self.trace_lock.acquire()
        if value == self.html_trace:
            return

        self.html_trace = value
        if not self.html_trace:
            if self.trace_file:
                try:
                    self.trace_file.close()
                    self.trace_file = None
                except IOError:
                    pass
            if GlobalFunctions.is_windows():
                os.system("del TraceEmulator\\trace* 2> nul")
            else:
                os.system("rm TraceEmulator\\trace* 2> /dev/null")
        self.trace_lock.release()

    def remove_extra_files(self, pattern, limit):
        if GlobalFunctions.is_windows():
            # glob is not available in older C200 systems. So only use it on windows
            import glob
            files = glob.glob(pattern)
            if len(files) > limit:
                files.sort()
                for f in files[:-limit]:
                    os.remove(f)
        else:
            os.system("rm -f TraceEmulator/*.txt.gz.tmp 2> /dev/null")
            os.system("rm -f `ls -r " + pattern + " 2> /dev/null | tail -n +%s`" % (limit+1))

    def check_error_log_file(self):
        if not self.error_to_file:
            return

        try:
            size = sys.stderr.tell()
            if size > ERROR_FILE_MAX_SIZE:
                self.trace_lock.acquire()
                if GlobalFunctions.is_windows():
                    sys.stderr.close()
                x = GlobalFunctions.get_localtime()
                fd = "%04d_%02d_%02d_%02d_%02d_%02d" % (x.year, x.month, x.day, x.hour, x.minute, x.second)
                if GlobalFunctions.is_windows():
                    ERROR_FILE_PATTERN = 'TraceEmulator/ErrorLog_%s.txt'
                else:
                    ERROR_FILE_PATTERN = 'TraceEmulator/ErrorLog_%s.txt.gz'
                self.handle_new_log_file(ERROR_FILE_NAME, ERROR_FILE_PATTERN, fd)
                sys.stderr = open(ERROR_FILE_NAME, 'w')
                self.trace_lock.release()
        except IOError:
            pass

    def handle_new_log_file(self, file_name, file_pattern, fd):
        target = file_pattern % (fd)
        limit_count = self.trace_files_limit_count

        if not GlobalFunctions.is_windows():
            target += ".tmp"
            limit_count -= 1

        try:
            os.rename(file_name, target)
        except OSError:
            pass

        self.remove_extra_files(file_pattern % "*", limit_count)

        if not GlobalFunctions.is_windows():
            cmd = "{ "
            cmd += "/bin/gzip -c " + target + " > " + target[:-4] + " 2> /dev/null ; "
            cmd += "/bin/rm -f " + target + " 2> /dev/null; "
            cmd += "/bin/rm -f TraceEmulator/trace_*.dat.tmp 2> /dev/null; "  # Should not be needed, but there was one case of leftover .dat.tmp files
            cmd += "/bin/rm -f TraceEmulator/ErrorLog_*.txt.gz.tmp 2> /dev/null; "
            cmd += "} &"
            os.system(cmd)

    def trace_to_html(self, msg, color, fd):
        msg = msg.replace('=>', '&rArr;')
        msg = msg.replace('<', '&lt;')
        msg = msg.replace('>', '&gt;')
        msg = msg.replace('\r\n', '\n')

        for s in [ "code", "b" ]:
            msg = msg.replace(f'&lt;{s}&gt;', f'<{s}>')
            msg = msg.replace(f'&lt;/{s}&gt;', f'</{s}>')
        is_new_file = False
        if (not self.trace_file and os.access(TRACE_FILE_NAME, os.R_OK)) or (self.trace_file and self.trace_file.tell() > self.trace_files_limit_size):
            if self.trace_file:
                self.trace_file.write('</font><br>\n' + "</body>\n")
                self.trace_file.close()
                self.trace_file = None

            if GlobalFunctions.is_windows():
                TRACE_FILE_PATTERN = 'TraceEmulator/trace_%s.html'
            else:
                TRACE_FILE_PATTERN = 'TraceEmulator/trace_%s.dat'
            self.handle_new_log_file(TRACE_FILE_NAME, TRACE_FILE_PATTERN, fd)
            is_new_file = True
            self.__last_color = None

        if not self.trace_file:
            self.trace_file = open(TRACE_FILE_NAME, 'w')
            self.trace_file.write("""<!DOCTYPE html>\n""")# + "\n</body>\n")
            self.trace_file.write(r"""
<meta content="text/html;charset=utf-8" http-equiv="Content-Type">
<style>
font { white-space: pre; }
</style>
<script>
var original_html = null;
var filter = '';
function filter_log()
{
	document.body.style.cursor = 'wait';
	if (original_html == null) {
		original_html = document.body.innerHTML;
	}
	if (filter == '') {
		document.body.innerHTML = original_html;
	} else {
		l = original_html.split("\n");
		var pattern = new RegExp(".*" + filter.replace('"', '"') + ".*", "i");
		final_html = '<font>';
		for(var i=0; i<l.length; i++){ // skip fisrt line
			if (pattern.test(l[i]))
				final_html += l[i] + '\n';
		}
		final_html += '</font>';
		document.body.innerHTML = final_html;
	}
	document.body.style.cursor = 'default';
}

document.onkeydown = function(event) {
	if (event.keyCode == 76) {
		var ret = prompt("Enter the filter regular expression. Examples:\n\n\
CheckFirmwareUpdate\n\nID=1 |ID=2 \n\nID=2 .*Got message\n\n2012-08-31 16:.*(ID=1 |ID=2 )\n\n", filter);
		if (ret != null) {
			filter = ret;
			filter_log();
		}
		return false;
	}
}
</script>
""")
            self.trace_file.write("""<body bgcolor="black" text="white">\n""")

        if '***' in msg:
            color = "red"
            # msg = f"<b>{msg}</b>"

        msg = msg.strip('\n')
        # msg = msg.replace('\n', '<BR>\n ') #  + '&nbsp;'*26
        if self.__last_color != color:
            prefix = ""
            if not is_new_file:
                # prefix += '<br>\n</font>'
                prefix += '</font>'
            prefix += f'<font color="{color}">\n'
            s = prefix + msg
            self.__last_color = color
        else:
            #s = "<br>\n" + msg
            s = "\n" + msg
        # s = '<font color="%s">' % (color) + msg + '</font><br>\n'
        try:
            self.trace_file.write(s)
        except:
            pass

        try:
            t = time.monotonic()
            delta = t - self.last_flush
            if delta > 2:
                self.trace_file.flush()
                self.last_flush = t
        except Exception as ex:
            print(f"Trace exception {ex}")

    def trace_to_screen(self, msg, color_name):
        html_to_shell_colors.get(color_name, color_name)
        shell_color_escape_code = shell_colors.get(color_name, "0")
        color = "\033[{0}m".format(shell_color_escape_code)
        s = color + msg + "\033[0m"
        print(s)
        sys.stdout.flush()

    def trace_message(self, msg):
        self.check_error_log_file()
        if not self.html_trace and not self.screen_trace:
            return

        x = GlobalFunctions.get_localtime()
        date_str = GlobalFunctions.format_date(x)
        thread_name = threading.currentThread().getName()
        if thread_name.startswith("AdjustedTypeName_"):
            t = thread_name.replace("AdjustedTypeName_", "")
        else:
            if not 'Thread' in thread_name and not msg.startswith(thread_name):
                msg = thread_name + ' ' + msg

            try:
                t = str(type(threading.currentThread())).split("'")[1].split('.')[1]
            except IndexError:
                t = ''
        msg = date_str + ' - ' + msg

        color_name = color_table.get(t, "white")  # ('('+t+')', '#FFFFFF')
        msg = GlobalFunctions.remove_accents_from_string(msg)

        self.trace_lock.acquire()
        if self.screen_trace:
            self.trace_to_screen(msg, color_name)
        if self.html_trace:
            fd = "%04d_%02d_%02d_%02d_%02d_%02d" % (x.year, x.month, x.day, x.hour, x.minute, x.second)
            self.trace_to_html(msg, color_name, fd)
        self.trace_lock.release()
