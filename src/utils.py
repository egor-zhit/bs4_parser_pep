import logging
from bs4 import BeautifulSoup

from requests import RequestException
from exceptions import ParserFindTagException


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def get_soup(session, url):
    response = get_response(session, url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    return soup


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def find_tag_str(soup, tag, string):
    searched_tag = soup.find(tag, string=string)
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {string}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def counting_statuses(status_on_url, statuses):
    if status_on_url in statuses:
        statuses[status_on_url] += 1
    if status_on_url not in statuses:
        statuses[status_on_url] = 1


def mismatch(status_on_url, status_in_tabl, pep_url):
    error_message = (f'Несовпадающие статусы:\n'
                     f'{pep_url}\n'
                     f'Статус в карточке: {status_on_url}\n'
                     f'Ожидаемый статус: '
                     f'{status_in_tabl}')
    logging.warning(error_message)
