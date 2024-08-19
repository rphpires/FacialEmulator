import requests



get_status = requests.get(f'http://172.16.17.47:8010/emulator/get-status', timeout=2)
print(get_status.status_code)
