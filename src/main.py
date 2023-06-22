import logging
import re
from urllib.parse import urljoin
from collections import defaultdict as DD

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEP_DOC_URL
from outputs import control_output
from utils import counting_statuses, find_tag, find_tag_str, get_soup, mismatch


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = get_soup(session, whats_new_url)
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li',
                                              attrs={'class': 'toctree-l1'})
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        try:
            soup = get_soup(session, version_link)
            h1 = find_tag(soup, 'h1')
            dl = find_tag(soup, 'dl')
            dl_text = dl.text.replace('\n', ' ')
            results.append(
                (version_link, h1.text, dl_text)
            )
        except ConnectionError:
            continue
    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Не найден список c версиями Python')
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = get_soup(session, downloads_url)
    main_tag = find_tag(soup, 'div', {'role': 'main'})
    table_tag = find_tag(main_tag, 'table', {'class': 'docutils'})
    pdf_a4_tag = find_tag(table_tag, 'a',
                          {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    soup = get_soup(session, PEP_DOC_URL)
    num_indx_section = find_tag(soup, 'section',
                                attrs={'id': 'numerical-index'})
    tbody_tag = find_tag(num_indx_section, 'tbody')
    tr_tags = tbody_tag.find_all('tr')
    statuses = DD(counting_statuses)
    results = [('Статус', 'Количество')]
    for pep_ref in tqdm(tr_tags):
        status_tag = find_tag(pep_ref, 'abbr')
        status_list = status_tag['title'].split(', ')
        status_in_tabl = ''.join(status_list[1])
        tag_a = find_tag_str(pep_ref, 'a', re.compile(r'^\d+$'))
        pep_url = urljoin(PEP_DOC_URL, tag_a['href'])
        soup = get_soup(session, pep_url)
        pep_content = find_tag(soup, 'section', attrs={'id': 'pep-content'})
        pep_dl = find_tag(pep_content, 'dl')
        status_on_url = find_tag(pep_dl, 'abbr').text
        counting_statuses(status_on_url, statuses)
        if status_on_url != status_in_tabl:
            mismatch(status_on_url, status_in_tabl, pep_url)
    for status in statuses:
        results.append((status, statuses[status]))
    results.append(('Total', sum(statuses.values())))
    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
