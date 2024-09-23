## Create exe command: PyInstaller --onefile user_actions.py

import requests
import sys
import keyboard
import os

from time import sleep
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style

from wxs_db_connection import DatabaseReader, ApiConnection

colorama_init()


sql = DatabaseReader()
api = ApiConnection()

h = {'WAccessAuthentication': f'{api.user}:{api.password}', 'WAccessUtcOffset': '-180'}


def assign_access_levels(total_users, access_level_id):
    # print(f"Total: {total_users} | AccessLevelID: {access_level_id}")
    script = f"""
Select
    TOP {total_users}
    m.CHID,
    FirstName
FROM CHMain m
    JOIN CHAUX a ON a.CHID = m.CHID and AuxChk03 = 1
WHERE m.CHID not in (select CHID from CHAccessLevels)
AND m.CHID in (select CHID from CHCards where IPRdrUserID is not null)
"""
    if not (ret := sql.read_data(script)):
        print('Nenhum usuário disponível que possua cartão e foto válida.')

    i = len(ret)
    for chid, name in ret:
        try:
            reply = requests.post(api.url + f"cardholders/{chid}/accesslevels/{access_level_id}", headers=h, json={}, params=(("CallAction", False), ))
            print(f"{i} - Associando nível de acesso para o usuário: CHID={chid}, Nome={name} | StatusCode: [{reply.status_code}] {reply.reason}")
            i -= 1

        except Exception as ex:
            print(f'*** Exception: {ex}')


def remove_access_levels(total_users, access_level_id):
    script = f"""
With RemoveAC as (
SELECT top {total_users} CHID FROM CHAccessLevels
WHERE AccessLevelID = {access_level_id}
)
SELECT m.CHID, FirstName FROM RemoveAC r
JOIN CHMain m ON m.CHID = r.CHID
"""
    if not (ret := sql.read_data(script)):
        print('Nenhum usuário possui este nível de acesso.')

    i = len(ret)
    for chid, name in ret:
        reply = requests.delete(api.url + f"cardholders/{chid}/accesslevels/{access_level_id}", headers=h, params=(("CallAction", False), ))
        print(f"{i} - Desassociando nível de acesso do usuário: CHID={chid}, Nome={name} | StatusCode: [{reply.status_code}] {reply.reason}")
        i -= 1


def start_visits(total_users, access_level_id):
    script = f"""
SELECT TOP {total_users}
    m.CHID, FirstName from CHMain m
JOIN CHAUX a ON a.CHID = m.CHID and AuxChk03 = 1
Where CHType = 1
AND m.CHID not in (select CHID from CHActiveVisits)
"""
    if not (ret := sql.read_data(script)):
        print('Nenhum visitante disponível no banco de dados.')

    script_db_cards = f"""
select top {total_users} ClearCode 
from CHCards
Where CHID IS NULL
"""
    db_cards = [ card for card in sql.read_data(script_db_cards)]
    c_index = 0
    i = len(script_db_cards)
    for chid, name in ret:
        try:
            new_visit = {"ClearCode": db_cards[c_index][0]}
            reply = requests.post(api.url + f"cardholders/{chid}/activeVisit", headers=h, json=new_visit, params=(("CallAction", False),))
            if reply.status_code in [201]:
                reply_msg = reply.reason
            else:
                reply_msg = reply.content
            print(f"{i} - Iniciando visita do usuário: CHID={chid}, Nome={name} | StatusCode: [{reply.status_code}] {reply_msg}")

            assign_ac = requests.post(api.url + f"cardholders/{chid}/accesslevels/{access_level_id}", headers=h, json={}, params=(("CallAction", False),))
            print(f"{i} - Associando nível de acesso para o visitante: CHID={chid}, Nome={name} | StatusCode: [{assign_ac.status_code}] {assign_ac.reason}")

            i -= 1
            c_index += 1

        except Exception as ex:
            print(f'**** Exception: {ex}')


def end_visits(total_users):
    if not (ret := sql.read_data(f"select top {total_users} CHID, FirstName from CHActiveVisits")):
        print('Nenhuma visita ativa.')

    i = len(ret)
    for chid, name in ret:
        try:
            reply = requests.delete(api.url + f"cardholders/{chid}/activeVisit", headers=h, params=(("CallAction", False),))
            print(f"{i} - Encerrando a visita do usuário: CHID={chid}, Nome={name} | StatusCode: [{reply.status_code}] {reply.reason}")
            i -= 1
        except Exception as ex:
            print(ex)


def sql_update_user_loop(total_users):
    time_interval = float(input("\n> Defina o intervalo de tempo entre os updates (segundos): "))

    script = f"""
Select
    TOP {total_users}
    m.CHID,
    FirstName
FROM CHMain m
    JOIN CHAUX a ON a.CHID = m.CHID and AuxChk03 = 1
WHERE m.CHID in (select CHID from CHCards where IPRdrUserID is not null)
"""
    get_chids = sql.read_data(script)

    while True:
        print('> Novo loop de update de usuários.')
        for chid, name in get_chids:
            print(f'Desassociando nível de acesso do usuário, CHID= {chid}, Nome= {name}')
            sql.execute(f"delete from CHAccessLevels where chid = {chid}")
            sql.execute(f"update CHMain set CHDownloadRequired = 1 where chid = {chid}")
            sleep(time_interval)

        for chid, name in get_chids:
            print(f'Associando nível de acesso do usuário, CHID= {chid}, Nome= {name}')
            sql.execute(f"insert into CHAccessLevels values({chid}, 1, null, null)")
            sql.execute(f"update CHMain set CHDownloadRequired = 1 where chid = {chid}")
            sleep(time_interval)


def sql_assign_access_level(total_users, access_level_id):
    script = f"""
Select
    TOP {total_users}
    m.CHID,
    FirstName
FROM CHMain m
    JOIN CHAUX a ON a.CHID = m.CHID and AuxChk03 = 1
WHERE m.CHID in (select CHID from CHCards where IPRdrUserID is not null)
"""
    if not (get_chids := sql.read_data(script)):
        print("Nenhum usuário disponível")
        return
    
    insert_script = ""

    for chid, name in get_chids:
        try:
            insert_script += f"INSERT INTO CHAccessLevels values({chid}, {access_level_id}, null, null);\n"
            insert_script += f"UPDATE CHMain SET CHDownloadRequired = 1 WHERE CHID = {chid};\n"
        except Exception as ex:
            print(f"** Erro: {ex}")

    print(f'Inserting {total_users} lines.')
    sql.execute(insert_script)

## ---------------------------
## ---------------------------
def get_access_level_id():
    ret = sql.read_data("select AccessLevelID, AccessLevelName from CfgACAccessLevels")
    if not ret:
        print("Nenhuma nível de acesso disponível.")
        sys.exit()

    valid_ac = []
    print("------ Níveis de acesso disponíveis ------")
    for ac_id, ac_name in ret:
        valid_ac.append(ac_id)
        print(f"{ac_id} - {ac_name}")

    access_level_id = int(input("\n> Selecione o ID do nível de acesso que será associado: "))

    if access_level_id not in valid_ac:
        print("ID escolhido não é válido.")
        sys.exit()

    return access_level_id
    print(f'ID escolhido: {access_level_id}')


def get_total_users_to_assing():
    while True:
        user_input = input("\nDigite a quantidade de usuários (número inteiro maior que zero): ")
        try:
            value = int(user_input)

            if value > 0:
                # print(f"Você digitou: {value}")
                return value
            else:
                raise ValueError("O valor deve ser maior que zero.")

        except ValueError as e:
            print(f"Erro: {e}. Tente novamente.")


def select_operation():
    while True:
        user_input = input(f"""
{Fore.GREEN}Selecione a operação que deseja realizar:{Style.RESET_ALL}
    1 - [API] Associar nível de acesso em lote (apenas para residentes);
    2 - [API] Desassociar nível de acesso em lote (apenas para residentes);
    3 - [API] Liberar visitas em lote;
    4 - [API] Encerrar visitas em lote;
    5 - [SQL] Loop de update de usuários;
    6 - [SQL] Associar nível de acesso em lote

{Fore.BLUE}Digite o número da opção:{Style.RESET_ALL} """)
        try:
            value = int(user_input)

            if 0 < value <= 6:
                # print(f"Você digitou: {value}")
                return value
            else:
                raise ValueError(f"O valor deve ser maior que zero.")

        except ValueError as e:
            print(f"{Fore.RED}Erro: {e}. Tente novamente.{Style.RESET_ALL}")


while True:
    operation = select_operation()
    total_users = get_total_users_to_assing()

    match operation:
        case 1:
            access_level_id = get_access_level_id()
            assign_access_levels(total_users, access_level_id)
        case 2:
            access_level_id = get_access_level_id()
            remove_access_levels(total_users, access_level_id)
        case 3:
            access_level_id = get_access_level_id()
            start_visits(total_users, access_level_id)
        case 4:
            end_visits(total_users)

        case 5:
            sql_update_user_loop(total_users)

        case 6:
            access_level_id = get_access_level_id()
            sql_assign_access_level(total_users, access_level_id)

        case _:
            print(f'{Fore.RED}Operação inválida!{Style.RESET_ALL}')

    sleep(2)
    print("----------------------------------------------------------\n\n", end='')
