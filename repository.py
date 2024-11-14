from database import new_session, LinkTable
from schemas import Link
import datetime
import random
import string
import re
import json
import datetime
from sqlalchemy import select, and_


def generate_short_link(len_link: int, links: list) -> dict:
    # Рандомно формируем ссылку. Длину можно задать. Далее проверям сгенерированную ссылку на соответствие условиям.
    # Если что-то не проходит - меняем. В конце смотрим есть ли такая ссылка в БД. Если есть - генерим ещё раз.
    try:
        short_url = [str(random.choice(string.digits)) if i else random.choice(string.ascii_lowercase + string.ascii_uppercase) for i in random.choices([True, False], k = len_link)]
        if not any(char.isdigit() for char in short_url):
            index = random.choice([i for i in range(len_link)])
            short_url[index] = random.choice(string.digits)
        chars = re.findall(r'\D', ''.join(short_url))
        num_index = [i for i in range(len_link) if short_url[i].isdigit()]
        if len(chars) == 0:
            index = random.choices(num_index, k = 2)
            short_url[index[0]] = random.choice(string.ascii_lowercase)
            short_url[index[1]] = random.choice(string.ascii_uppercase)
        elif len(chars) == 1:
            index = random.choice(num_index)
            short_url[index] = random.choice(string.ascii_lowercase) if chars[0].isupper() else random.choice(string.ascii_uppercase)
        if not any(char.islower() for char in short_url):
            index = random.choice([i for i in range(len_link) if not short_url[i].isdigit()])
            short_url[index] = random.choice(string.ascii_lowercase)
        if not any(char.isupper() for char in short_url):
            index = random.choice([i for i in range(len_link) if not short_url[i].isdigit()])
            short_url[index] = random.choice(string.ascii_uppercase)
        short_url = ''.join(short_url)
        # Если ссылка уже есть - генерим ещё раз
        if short_url in links:
            short_url = generate_short_link(len_link, links)       
            return {'error': True, 'text': short_url['text']} if short_url['error'] else {'error': False, 'text': short_url['text']}
        else:
            return {'error': False, 'text': short_url}
    except BaseException as exception:
        return {'error': True, 'text': str(exception)}
    
class LinkRepository:
    @classmethod
    async def add_link(cls, full_link: str, parametrs: str) -> Link:
        """Запись в базу короткой ссылки.
          Проверка генерации на наличие хотя бы двух букв в разном регистре, наличие хотя бы одной цифры.
          Если параметры есть, то они записываются в виде json в текстовое поле, если нет - пустой словарь.
          Длина короткой ссылки захардкожена. При желании можно получать от юзера или хранить в БД.
          Пока никакие ссылки не удаляются. По идее можно организовать ф-ю в бд, запускающуюся раз в минуту и чистящую ссылки, у которых вышло время жизни"""
        try:
            async with new_session() as session:
                full_url, parametr = full_link, parametrs
                # raise BaseException('захотелось')
                # Несколько проверок на корректность url. Сюда можно придумать ещё что-нибудь.
                error = []
                if full_url.startswith('http://') is False and full_url.startswith('https://') is False:
                    error.append('Некорректный протокол передачи. Необходим http или https')
                if not re.findall(r'//www\.', full_url):
                    error.append('Некорректный адрес сайта (отсутствует "www")')
                if not re.findall(r'//[a-z0-9.-_]+\.[a-z]{2,}/', full_url):
                    error.append('Некорректный домен')
                if error:
                    return {'error': True, 'error_text': '\n'.join(error), 'data': ''}
                dict_param = {}
                short_url = ''
                # Смотрим есть ли параметры
                if len(parametr) > 0:
                    dict_param = {param.split('=')[0]: param.split('=')[1] for param in parametr.split('&')}
                json_param = json.dumps(dict_param, indent=4)
                # Смотрим по времени жизни. Если такая ссылка уже была, то она не должна быть просрочена
                query = select(LinkTable).filter(and_(LinkTable.url == full_url, LinkTable.param == json_param, LinkTable.create_time > datetime.datetime.now().timestamp() - 600))
                result = await session.execute(query)
                link = result.one_or_none()
                # Если ссылка уже есть - возвращаем полученные данные из базы
                if link:
                    return {'error': False, 'error_text': '', 'data': link[0]}
                # С одной стороны подход не оптимальный - каждый раз искать все ссылки. Лучше бы запихнуть поиск в ф-ю
                # С другой - если время жизни ссылки 10 минут - то много ссылок всё равно не будет. 
                short_url_len = 6
                query = select(LinkTable.short_url).filter(LinkTable.create_time > (datetime.datetime.now().timestamp() - 600))
                result = await session.execute(query)
                links = result.scalars().all()
                generate_url = generate_short_link(short_url_len, links)
                if generate_url['error']:
                    return {'error': True, 'error_text': generate_url['text'], 'data': ''}
                else:
                    short_url = generate_url['text']
                link_dict = {'url': full_url, 'param': json_param, 'short_url': short_url, 'create_time': datetime.datetime.now().timestamp()}
                link = LinkTable(**link_dict)
                session.add(link)
                await session.flush()
                await session.commit()
                return {'error': False, 'error_text': '', 'data': link}
        except BaseException as exception:
            return {'error': True, 'error_text': str(exception), 'data': ''}

    @classmethod
    async def get_link(cls):
        """Получение всех ссылок для теста"""
        async with new_session() as session:
            query = select(LinkTable)
            result = await session.execute(query)
            links = result.scalars().all()
            print(links)
            return links
        
    @classmethod
    async def get_full_link(cls, short_link: str) -> dict:
        """Получение полной ссылки на основе краткой. Для редиректа или пользователя.
        Если ссылки нет или у неё истекло время жизни - то возвращаем ошибку"""
        try:
            async with new_session() as session:
                query = select(LinkTable).filter_by(short_url = short_link)
                result = await session.execute(query)
                link = result.one_or_none()
                if link:
                    # Если время жизни ссылки истекло - возвращаем соответствующую ошибку.
                    # Если ссылки будут чиститься раз в минуту, то ошибку нужно исправить.
                    if link[0].create_time < datetime.datetime.now().timestamp() - 600:
                        return {'error': True, 'error_text': 'Указанная короткая ссылка просрочена', 'data': ''}
                    parametrs = json.loads(link[0].param)
                    full_url = link[0].url
                    if parametrs:
                        full_url = full_url + '?' + '&'.join([f"{param}={parametrs[param]}" for param in parametrs])
                    return {'error': False, 'error_text': '', 'data': full_url}
                else:
                    return {'error': True, 'error_text': 'Указанная короткая ссылка не найдена в базе данных', 'data': ''}
        except BaseException as exception:
            return {'error': True, 'error_text': str(exception), 'data': ''}