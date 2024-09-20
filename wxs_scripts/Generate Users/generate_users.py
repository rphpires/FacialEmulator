
import requests
import random
from faker import Faker
import requests
from bs4 import BeautifulSoup
import urllib.parse
import schedule
import time
from WxsTracer import trace, report_exception
from function import assign_card


url = "http://localhost/W-AccessAPI/v1/"
h = { 'WAccessAuthentication': 'usr:pwd', 'WAccessUtcOffset': '-180' }

base_url = 'https://this-person-does-not-exist.com/'
page_url = 'https://this-person-does-not-exist.com/en'

device_url = 'http://172.16.19.63/'


QNT_USERS_TO_CREATE = 300000
CREATE_USER_WITH_PHOTO = False


def get_control_id_session():
    global session

    data = {
        'login': 'admin',
        'password': 'admin'
    }

    get_session = requests.post(device_url + 'login.fcgi', json=data)
    if get_session.status_code in [200]:
        session = get_session.json()['session']
    else:
        session = None


def main(qnt):
    counter = 0
    i = qnt

    while counter < qnt:
        schedule.run_pending()

        trace(f'{i} - Creating user..')
        create_cardholder()
        counter += 1
        i -= 1
        

def create_cardholder():
    gender = random.choice(["male", "female"])
    fake = Faker('pt_BR')
    
    f_name = fake.first_name_male() if gender == "male" else fake.first_name_female()
    l_name = fake.last_name()
    
    new_user = {
        "FirstName" : f"{f_name} {l_name}",
        "CHType" : 2,
        "PartitionID" : 1
    }
    
    photo_is_valid = False
    try:
        created_user = requests.post(url + 'cardholders', headers=h, json=new_user, params=(("CallAction", False),))
        if created_user.status_code == 201:
            cardholder = created_user.json()
            trace(f"usuário chid= {cardholder['CHID']}, {f_name} {l_name} criado com sucesso")
            
            if CREATE_USER_WITH_PHOTO: ## Check PHOTO quality
                reply = requests.put(url + 'cardholders/%d/photos/1'%(cardholder["CHID"]), files=(('photoJpegData', import_photo()), ), headers=h)
                if reply.status_code in [ requests.codes.ok, requests.codes.no_content ]:
                    print("Cardholder photo 1 update OK")
                    photo_is_valid = True
                else:
                    print("Error: " + str(reply))

            if photo_is_valid:
                cardholder['AuxChk03'] = True
            
            cardholder["AuxText15"] = cardholder["CHID"] ## Usado para facilitar a busca do usuário.
            requests.put(url + 'cardholders', headers=h, json=cardholder)

            # assign_card(cardholder)
        

        else:
            trace(f'Erro na criação do usuário: status_code= {created_user.status_code} | {created_user.reason}')                   
    except Exception as ex:
        report_exception(ex)


def download_image(image_url):
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Falha ao baixar a imagem. Status code: {response.status_code}")
    
    except Exception as ex:
        report_exception(ex)


def import_photo():
    try:
        response = requests.get(page_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        img_element = soup.find('img', id='avatar')
        if img_element:
            # Obtém o valor do atributo 'src'
            img_src = img_element.get('src')
            
            # Constrói a URL completa da imagem
            image_url = urllib.parse.urljoin(base_url, img_src)
            
            # Baixa a imagem
            return download_image(image_url)
        else:
            print('Elemento <img> com id "avatar" não encontrado.')
    except Exception as ex:
        report_exception(ex)


def valid_photo():
    i = 0
    while True:
        test_data = import_photo()
        upd_photo = requests.post(
            device_url + 'user_test_image.fcgi',
            params={'session': session},
            headers= {"Content-Type": "application/octet-stream"},
            data = test_data
        )
        if upd_photo.json()['success']:
            data = test_data
            break

        i += 1
        if i > 5:
            trace('** Error trying to get a valid image.')
            break

    return data
    
# schedule.every(10).minutes.do(get_control_id_session)


if __name__ == '__main__':
    # get_control_id_session()
    main(QNT_USERS_TO_CREATE)
  