from fastapi import APIRouter
from repository import LinkRepository
from fastapi.responses import RedirectResponse
from schemas import Link, FullLink, AddLink

    
router = APIRouter(
    tags=['Короткие ссылки']
    )

    
@router.post("/add_short_link")
async def add_short_link(url: str) -> AddLink:
    """Создание коротких ссылок для юзера.
    Принимает полную ссылку и заносит в базу данных. 
    Возвращает полученную короткую ссылку."""
    url_and_param = url.partition('?')
    link, param = url_and_param[0], url_and_param[2]
    answer = await LinkRepository.add_link(link, param)
    if answer['error']:
        return {"error": answer['error'], 'text': answer['error_text'], 'data': ''}
    else:
        # return Link.model_validate(answer['data'])
        return  {"error": answer['error'], 'text': answer['error_text'], 'data': Link.model_validate({'id': answer['data'].id, 'url': answer['data'].url, 'param': answer['data'].param,
                                    'short_url': answer['data'].short_url, 'create_time': answer['data'].create_time})}
    
@router.get("/get_links")
async def get_links():
    """Функция возвращает все доступные короткие ссылки. Для теста"""
    links = await LinkRepository.get_link()
    return links

@router.get("/get_full_link")
async def get_full_link(short_link: str) -> FullLink:
    """Функция возвращает одну полную ссылку на основе краткой.
    Если в БД отсутствует данная ссылка, то функция вернет соответствующую ошибку.
    Если у короткой ссылки истекло время жизни - будет получена соответствующая ошибка."""
    answer = await LinkRepository.get_full_link(short_link)
    status = answer['error']
    status_text = answer['error_text']
    return {"error": status, 'text': status_text, 'data': Link.model_validate(answer['data'])}

@router.get("/{short_link}")
async def redirect_link(short_link: str):
    """Функция осуществляет переход по короткой ссылке.
    Если такой ссылки нет или у неё истекло время жизни - то будет получена соответствующая ошибка."""
    answer = await LinkRepository.get_full_link(short_link)
    status = answer['error']
    status_text = answer['error_text']
    if status:
        return {"error": status, 'text': status_text, 'data': ''}
    else:
        return RedirectResponse(answer['data'])