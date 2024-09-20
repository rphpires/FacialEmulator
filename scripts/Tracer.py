
import threading
import queue
import os
import glob
import datetime
import traceback

LOG_MAX_SIZE = 5_000_000  # 5MB
MAX_FILES = 15
FOLDER_NAME = "Traces"

log_file = None


class LogFile:
    def __init__(self, filename, max_size=LOG_MAX_SIZE):
        self.filename = filename
        self.max_size = max_size
        self.current_size = os.path.getsize(filename) if os.path.exists(filename) else 0
        self.file = open(self.filename, 'a', encoding="utf-8")
        self.log_queue = queue.Queue()  # Fila para armazenar logs
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._process_queue)
        self.thread.start()

        self._rotate_file()
        create_html_log_file(log_filename)

    def _rotate_file(self):
        self.file.close()
        current_date = datetime.datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
        splited_name = self.filename.split('/')
        new_filename = f'{splited_name[0]}/{current_date}_{splited_name[1]}'
        os.rename(self.filename, new_filename)
        self.file = open(self.filename, 'a', encoding="utf-8")

    def write(self, data):
        self.log_queue.put(data)  # Adiciona o log na fila

    def _process_queue(self):
        while not self.stop_event.is_set():
            try:
                log_entry = self.log_queue.get(timeout=1)
                if self.current_size + len(log_entry) > self.max_size:
                    self._rotate_file()
                    self.current_size = 0
                self.file.write(log_entry)
                self.file.flush()
                self.current_size += len(log_entry)
                self.log_queue.task_done()
            except queue.Empty:
                continue

    def close(self):
        self.stop_event.set()
        self.thread.join()
        self.file.close()


# Funções auxiliares para criar logs HTML e remover arquivos antigos
def create_html_log_file(log_filename):
    htmlPageHeader = """<!DOCTYPE html>
<meta content="text/html;charset=utf-8" http-equiv="Content-Type">
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
        l = original_html.split("<br>");
        var pattern = new RegExp(".*" + filter.replace('"', '\\"') + ".*", "i");
        final_html = '';
        for(var i=0; i<l.length; i++){
            if (pattern.test(l[i]))
                final_html += l[i] + '<br>';
        }
        document.body.innerHTML = final_html;
    }
    document.body.style.cursor = 'default';
}

document.onkeydown = function(event) {
    if (event.keyCode == 76) {
        var ret = prompt("Enter the filter regular expression. Examples:\\n\\n\\
CheckFirmwareUpdate'\\n\\n'ID=1 |ID=2 \\n\\nID=2 .*Got message\\n\\n2012-08-31 16:.*(ID=1 |ID=2 )\\n\\n", filter);
        if (ret != null) {
            filter = ret;
            filter_log();
        }
        return false;
    }
}
</script>
<STYLE TYPE="text/css">
<!--
BODY
{
  color:white;
  background-color:black;
  font-family:monospace, sans-serif;
}
-->
</STYLE>
<body bgcolor="black" text="white">
<font color="white">"""

    with open(log_filename, "w", encoding="utf-8") as log_file:
        log_file.write(htmlPageHeader)


def get_log_files(folder_name):
    files = glob.glob(os.path.join(folder_name, '*.html'))
    files.sort(key=os.path.getctime)
    return files


def remove_oldest_log_file(folder_name):
    log_files = get_log_files(folder_name)
    if len(log_files) >= MAX_FILES:
        oldest_file = log_files[0]
        os.remove(oldest_file)


def trace(Message, userID='', color='white'):
    global log_file

    print(f"{userID} - {Message}")
    # executableName = 'Integra'
    # folderName = 'Trace ' + executableName

    enabled_trace = os.path.isfile('DisableTraceEnable.txt')
    enabled_trace_1 = os.path.isfile('DisableTraceIntegraEnable.txt')
    enabled_trace_2 = os.path.isfile('DisableTrace.txt')

    if any((enabled_trace, enabled_trace_1, enabled_trace_2)):
        return

    os.makedirs(FOLDER_NAME, exist_ok=True)
    log_filename = os.path.join(FOLDER_NAME, 'trace.html')

    # Inicializa o log_file uma vez, se ainda não foi instanciado
    if log_file is None:
        if not os.path.exists(log_filename):
            create_html_log_file(log_filename)

        remove_oldest_log_file(FOLDER_NAME)

        # Instancia o LogFile uma única vez
        log_file = LogFile(log_filename, max_size=LOG_MAX_SIZE)

    log_entry = f'<br></font><font color="{color}">{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} - {userID} - {Message}'
    log_file.write(log_entry)


def report_exception(e):
    try:
        t = "{}".format(type(threading.currentThread())).split("'")[1].split('.')[1]
    except IndexError:
        t = 'UNKNOWN'

    trace("", f"Bypassing exception at {t} ({e})", color="red")
    trace("", f"**** Exception: <code>{traceback.format_exc()}</code>", color="red")


def error(msg):
    trace(f'** {msg}', color='red')


def trace_elapsed(msg, reference_utc_time):
    delta = datetime.datetime.utcnow() - reference_utc_time
    if not 'total_seconds' in dir(delta):
        trace(msg)
        return
    elapsed_ms = int((delta).total_seconds() * 1000)
    msg += " (%d ms)" % (elapsed_ms)
    trace(msg)


def close_tracer():
    global log_file

    log_file.close()

os.makedirs(FOLDER_NAME, exist_ok=True)
log_filename = os.path.join(FOLDER_NAME, 'trace.html')
