import json
import os
import requests
import configparser
from datetime import datetime


class VKAPIClient:
    BASE_URL = 'https://api.vk.com/method'

    def __init__(self, token, user_id):
        self.token = token
        self.user_id = user_id

    def __get_params(self):
        return {
            'access_token': self.token,
            'v': '5.199'
        }

    def __get_photos(self, album_id):
        params = self.__get_params()
        params.update({
            'owner_id': self.user_id,
            'album_id': album_id,
            'extended': 1,
            'photo_sizes': 1
        })
        response = requests.get(f'{self.BASE_URL}/photos.get',
                                params=params)
        return response

    def __download_file(self, response_json):
        file_path = os.path.join(os.getcwd(), 'storage')
        if not os.path.isdir(file_path):
            os.mkdir(file_path)
            print(f' > Был создан локальный каталог "storage"'
                  ' в текущей рабочей директории')
        number_likes = set()
        all_photo_files = []
        for item in response_json.get('response', {}).get('items', {}):
            likes = item.get("likes", {}).get("count", 0)
            file_name = str(likes)
            if likes in number_likes:
                dt = datetime.utcfromtimestamp(item.get("date", 0))
                file_name += dt.strftime(' (%Y-%m-%d %H_%M)')
            else:
                number_likes.add(likes)
            file_name += '.jpg'
            file_size = ''
            file_url = ''
            for size_item in item.get('sizes', []):
                if size_item.get('type', '') == 'w':
                    file_size = size_item.get('type', '')
                    file_url = size_item.get('url', '')
                elif size_item.get('type', '') == 'z':
                    file_size = size_item.get('type', '')
                    file_url = size_item.get('url', '')
            if file_size != '':
                all_photo_files.append({
                    'file_name': file_name,
                    'size': file_size
                })
                response = requests.get(file_url)
                with open(os.path.join(file_path, file_name), 'wb') as file:
                    file.write(response.content)
                print(f' > Файл "{file_name}" был успешно сохранён')
        with open(os.path.join(file_path, 'photo_info.json'), 'w') as file:
            json.dump(all_photo_files, file, ensure_ascii=False, indent=2)
        return f'Загрузка завершена, '\
               f'было загружено {len(all_photo_files)} фотография(ии,ий)!'

    def photos_download(self, album_id='profile'):
        response = self.__get_photos(album_id)
        if 200 <= response.status_code < 300:
            error_code = response.json().get('error', {}).get('error_code', 0)
            if error_code == 0:
                result = self.__download_file(response.json())
            else:
                result = f'Ошибка ответа (error_code = {error_code})'
        else:
            result = f'Ошибка запроса (status_code = {response.status_code})'
        return result


class YandexDiskAPIClient:
    BASE_URL = 'https://cloud-api.yandex.net'

    def __init__(self, token):
        self.token = token

    def __get_headers(self):
        return {
            'Authorization': f'OAuth {self.token}'
        }

    def __directory_exists(self):
        params = {'path': 'storage'}
        response = requests.get(f'{self.BASE_URL}/v1/disk/resources',
                                headers=self.__get_headers(),
                                params=params)
        return response.status_code

    def __create_folder(self):
        status_code = 0
        if 400 <= self.__directory_exists() < 500:
            params = {'path': 'storage'}
            response = requests.put(f'{self.BASE_URL}/v1/disk/resources',
                                    headers=self.__get_headers(),
                                    params=params)
            status_code = response.status_code
        return status_code

    def __create_file(self, file_name):
        params = {
            'path': f'storage/{file_name}',
            'overwrite': 'true'
        }
        response = requests.get(f'{self.BASE_URL}/v1/disk/resources/upload',
                                headers=self.__get_headers(), params=params)
        return response

    def __uploading_files(self, url_upload, file_name):
        file_path = os.path.join(os.getcwd(), 'storage')
        with open(os.path.join(file_path, file_name), 'rb') as file:
            response = requests.put(url_upload, files={'file': file})
        return response

    def uploading_photos(self, number_photos):
        if 200 <= self.__create_folder() < 300:
            print(f' > Был создан каталог "storage" на Yandex Disk'
                  ' в корневом каталоге')
        file_path = os.path.join(os.getcwd(), 'storage')
        with open(os.path.join(file_path, 'photo_info.json')) as file:
            all_photo_files = json.load(file)
        numerator_files = 0
        for photo in all_photo_files:
            if number_photos == numerator_files:
                break
            file_name = photo.get('file_name', '_.jpg')
            response = self.__create_file(file_name)
            if 200 <= response.status_code < 300:
                response = self.__uploading_files(response.json().get('href'),
                                                  file_name)
                if 200 <= response.status_code < 300:
                    numerator_files +=1
                    print(f' > Файл "{file_name}" был успешно выгружен'
                          ' на Yandex Disk')
        return f'Выгрузка завершена, ' \
               f'было выгружено {numerator_files} фотография(ии,ий)!'


def backup_photos():
    config = configparser.ConfigParser()
    config.read('settings.ini')
    try:
        token_vk = config['VK']['token']
        user_id_vk = config['VK']['user_id']
        token_yandex_disk = config['YandexDisk']['token']
    except KeyError:
        token_vk = ''
        user_id_vk = ''
        token_yandex_disk = ''
    print('Эта программа предназначена для сохранения фотографий из ВКонтакт')
    print('   · На локальный компьютер')
    print('   · На Яндекс Диск')
    if token_vk == '' or user_id_vk == '' or token_yandex_disk == '':
        print()
        print('  !!! Обратите внимание !!!')
        print(' !!! Для работы программы надо вписать вфайле"settings.ini'
              ' !!!\n   [VK]\n   token=<СВОЙ ТОКЕН ПРИЛОЖЕНИЯ ОТ ВКОНТАКТ>\n'
              '   user_id=<ID ПОЛЬЗОВАТЕЛЯ В ВКОНТАКТЕ>\n\n'
              '   [YandexDisk]\n   token=<СВОЙ ТОКЕН ЯНДЕКС ДИСК>')
    else:
        print()
        print('---Отчёт---')
        vk_client = VKAPIClient(token_vk, user_id_vk)
        print(vk_client.photos_download())

        print()
        print('Сколько фотографий вы хотите выгрузить на Yandex Disk?'
              '(По умолчанию: 5)')
        str_answer = input('Введите чило: ')
        try:
            number_photos = int(str_answer)
        except ValueError:
            number_photos = 5
            print(f'!!! Формат значения переменой не определён ({str_answer})'
                  '\n!!! Будет взято по умолчанию: 5')
        print()
        print('---Отчёт---')
        ydisk_client = YandexDiskAPIClient(token_yandex_disk)
        print(ydisk_client.uploading_photos(number_photos))


if __name__ == '__main__':
    backup_photos()