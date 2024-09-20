import base64, requests
from WxsDbConnection import DatabaseReader
import os
from bs4 import BeautifulSoup
import urllib.parse
from PIL import Image
from io import BytesIO


url = "http://localhost/W-AccessAPI/v1/"
h = { 'WAccessAuthentication': 'usr:pwd', 'WAccessUtcOffset': '-180' }

base_url = 'https://this-person-does-not-exist.com/'
page_url = 'https://this-person-does-not-exist.com/en'

dev_url = 'http://172.16.19.63/'
h = {"Content-Type": "application/json"}

image_path = 'C:\\Program Files (x86)\\Invenzi\\Invenzi W-Access\\Web Application\\PhotoID\\Photo_1\\'

data = {
    'login': 'admin',
    'password': 'admin'
}


get_session = requests.post(dev_url + 'login.fcgi', json=data)
if get_session.status_code in [200]:
    session = get_session.json()['session']
else:
    print('Erro ao requisitar o session do terminal.')
    # sys.exit()

def valid_photo():
    success = False
    while not success:
        test_data = import_photo()
        upd_photo = requests.post(
            dev_url + 'user_test_image.fcgi',
            params={'session': session},
            headers= {"Content-Type": "application/octet-stream"},
            data = test_data
        )
        if (success := upd_photo.json()['success']):
            #data = test_data
            scores = upd_photo.json()['scores']
            print(f'Usuário CHID= {chid} | Foto valida. Center= {scores["center_pose_quality"]}, Sharpness= {scores["sharpness_quality"]} ')
                
    # print(type(data), len(data))
    return test_data

def import_photo():
    try:
        response = requests.get(page_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        img_element = soup.find('img', id='avatar')
        if img_element:
            img_src = img_element.get('src')
            image_url = urllib.parse.urljoin(base_url, img_src)
            response = requests.get(image_url)
            if response.status_code == 200:
                return response.content
            else:
                print(f"Falha ao baixar a imagem. Status code: {response.status_code}")
        else:
            print('Elemento <img> com id "avatar" não encontrado.') 
    except:
        return None


def put_photo(chid):
    reply = requests.put(url + 'cardholders/%d/photos/1'%(chid), files=(('photoJpegData', valid_photo()), ), headers=h)
    if reply.status_code in [ requests.codes.ok, requests.codes.no_content ]:
        print("Cardholder photo 1 update OK")
    else:
        print("Error: " + str(reply))


def save_img(img_name):
    try:
        data = valid_photo()

        target_size_kb = 50  # Tamanho desejado em KB
        compressed_image_bytes = compress_image(data, target_size_kb)

        with open(img_name, 'wb') as file:
            file.write(compressed_image_bytes)
        return True
    
    except Exception as ex:
        print('**Erro ao salvar foto')
        print(f'** Exception: {ex}')
        return False


def compress_image(image_bytes, target_size_kb, quality_step=5):
    # Abrir a imagem a partir dos bytes
    img = Image.open(BytesIO(image_bytes))
    
    # Definir a qualidade inicial
    quality = 95
    
    # Reduzir a qualidade iterativamente até atingir o tamanho desejado
    while quality > 0:
        # Criar um buffer para salvar a imagem comprimida
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        size_kb = buffer.tell() / 1024  # Tamanho em KB
        
        if size_kb <= target_size_kb:
            return buffer.getvalue()
        
        quality -= quality_step
    
    return buffer.getvalue()  # Retorna a imagem com a melhor compressão possível


sql = DatabaseReader()

# Caminho da pasta onde estão os arquivos
pasta = 'C:\\Program Files (x86)\\Invenzi\\Invenzi W-Access\\Web Application\\PhotoID\\Photo_1'

# Lista para armazenar os IDs
ids = []


# Loop para ler todos os arquivos da pasta
for nome_arquivo in os.listdir(pasta):
    # Verificar se o arquivo está no formato esperado
    if nome_arquivo.endswith('_1.jpg'):
        # Extrair o ID do nome do arquivo
        id_str = nome_arquivo.split('_')[0]
        try:
            # Converter o ID para inteiro e adicionar à lista
            id_int = int(id_str)
            ids.append(id_int)
        except ValueError:
            # Se não for possível converter para inteiro, ignorar o arquivo
            print(f'ID inválido no arquivo: {nome_arquivo}')

# Exibir a lista de IDs
print(len(ids))

tamanho_bloco = 5000
n = 0
for i in range(0, len(ids), tamanho_bloco):
    # Obter o bloco de itens
    bloco = ids[i:i + tamanho_bloco]
    n += 1

    script = f"""
    SELECT a.CHID, FirstName 
    FROM CHAUX a
    JOIN CHMain m ON m.CHID = a.CHID
    WHERE a.CHID IN ({', '.join(str(x) for x in bloco)})
    AND AuxChk03 <> 1
    """
    ## AuxChk03 é usado para verificar se a foto do usuários é valida.

    result = sql.read_data(script)
    total = len(result)
    for chid, name in result:
        print(f'Bloco: {n} | Qnt restante: {total}')
        total -= 1
        try:
            img_name = f'{image_path}{chid}_1.jpg'
            if os.path.isfile(img_name):
                print(f'Usuário CHID= {chid}, {name} já possui foto.')
                with open(img_name, 'rb') as image_file:
                    img_base64 = image_file.read()
                    upd_photo = requests.post(
                        dev_url + 'user_test_image.fcgi',
                        params= {'session': session},
                        headers= {"Content-Type": "application/octet-stream"},
                        data = img_base64
                    )
                    scores = upd_photo.json()["scores"]
                    if (success := upd_photo.json()['success']):
                        print(f'Usuário CHID= {chid} | Foto valida. Center= {scores["center_pose_quality"]}, Sharpness= {scores["sharpness_quality"]} ')
                        
                    else:
                        print(f'Usuário CHID= {chid} | Foto invalida, criando nova foto.')
                        if not save_img(img_name):
                            continue
                        
            else:
                print(f'Usuário CHID= {chid} não possui foto, importando nova foto.')
                if not save_img(img_name):
                    continue
        
        except:
            print('*** Error ')
        
        finally:
            sql.execute_update(f"update CHAux set AuxChk03 = 1 where CHID = {chid}")