import requests


# get_status = requests.get(f'http://172.20.112.122:1050/emulator/get-status', timeout=2)
# print(get_status.status_code)


import subprocess

def kill_processes_by_command(command):
    try:
        # Executa o comando pgrep para obter os PIDs dos processos
        pgrep_cmd = f"pgrep -f '{command}'"
        cmd = f"ps aux | grep '{command}' | grep -v grep | awk '{{print $2}}'"

        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, text=True)

        # Captura a saída (os PIDs)
        pids = result.stdout.strip().split('\n')

        if pids:
            print(f"Processos encontrados: {pids}")
            for pid in pids:
                print(pid)
                # Finaliza cada processo encontrado
                #kill_cmd = f"kill -9 {pid}"
                #subprocess.run(kill_cmd, shell=True, check=True)
                #print(f"Processo {pid} finalizado.")
        else:
            print("Nenhum processo encontrado.")

    except subprocess.CalledProcessError:
        print("Nenhum processo encontrado ou erro ao executar o comando.")

if __name__ == "__main__":
    kill_processes_by_command("facial_emulator_1050")
