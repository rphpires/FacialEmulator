import subprocess

# Caminho para o arquivo .exe
caminho_arquivo_exe = r"C:\Invenzi Development\wxs-small-projects\IoFacialEmulator\Emulator\running\77\emulator_77.exe"

# Argumentos para passar para o arquivo .exe
ip = "localhost"
port = "77"
nome = "Dahua"

# Comando a ser executado
comando = [caminho_arquivo_exe, ip, port, nome]

processo = subprocess.Popen(comando)

# Finalizar o processo Python
exit()