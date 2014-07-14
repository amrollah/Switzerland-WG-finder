# !/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import random
import gc
from time import sleep
import sqlite3

from bs4 import BeautifulSoup
import re
import requesocks as requests
from stem import Signal
from stem.control import Controller

from mailman import email_sender
from utils.credentials_sample import students_ch_username, students_ch_password
from utils.user_agent_list import user_agents
from funcs import get_database


session = requests.session()
# session.proxies = {'http': 'socks5://127.0.0.1:9050'}

requests_log = logging.getLogger("requesocks")
requests_log.setLevel(logging.ERROR)
handler = logging.FileHandler("run.log", "a", encoding="UTF-8")

formatter = logging.Formatter("%(levelname)s:%(message)s")
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
conn = None
con_ip = ['']
priceMax = 800
priceMin = 400
clean_db = False


def main_crawler():
    counter = 1
    db_name = 'emails'
    get_database(db_name, clean_db)
    global conn
    conn = sqlite3.connect(db_name)
    while True:
        print('Iteration: {0}'.format(counter))
        counter += 1
        header = {'user-agent': user_agents[random.randint(0, len(user_agents) - 1)]}
        check_ip()
        search_woko(header)
        search_wgzimmer(header, 'zurich-stadt')
        search_wgzimmer(header, 'zurich')
        search_students_ch(header)
        sleep(3 * 60 * 30)


def check_ip():
    try:
        header = {'user-agent': user_agents[random.randint(0, len(user_agents) - 1)]}
        r = session.get(r'http://jsonip.com', headers=header)
        ip = eval(r.text)['ip']
        if ip != con_ip[0]:
            con_ip[0] = ip
            logging.info(u'--- My IP is ---: {0}'.format(con_ip[0]))
    except:
        pass


def new_ip():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password="123456")
        controller.signal(Signal.NEWNYM)
        sleep(10)
        check_ip()


def handle_room(r_dict):
    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT * FROM room WHERE email = ? AND contact_name = ?',
            (r_dict.get('email', None), r_dict['contact_name']))
        data = cur.fetchone()
        if data is None or len(data) == 0 and r_dict.get('email', None) is not None:
            if 'Until' in r_dict['available'] and (
                        any(p in r_dict['available'].split('Until')[1] for p in ['2014', '.14', 'ugust']) or any(
                                p in r_dict['available'].split('Until')[0] for p in ['6.2014', '7.2014', '10.2014'])):
                return
            print(r_dict)
            email_sender(r_dict)
            cur.execute("INSERT INTO room(type, email, contact_name, link, rent, available) VALUES (?,?,?,?,?,?)",
                        (r_dict['type'],
                         r_dict['email'],
                         r_dict['contact_name'],
                         r_dict['link'], r_dict['rent'], r_dict['available'],
                        ))
            conn.commit()

    except Exception, e:
        print(repr(e))
        logging.exception(repr(e))
        if conn:
            conn.rollback()


def search_woko(header):
    all_rooms = []
    try:
        url = r'http://www.woko.ch/de/anschlagbrett_nachmieter.asp'
        r = session.get(
            url, headers=header)
        if r.status_code != 200:
            return 0
        soup = BeautifulSoup(r.text)
        all_rooms = soup.find_all('table', {'class': 'anschlag'})
    except:
        new_ip()
    r_dict = dict(type='WOKO')
    result_count = len(all_rooms or [])
    for room in all_rooms:
        lines = room.find_all('tr')
        try:
            r_dict['available'] = lines[1].find('td', {'class': 'anschlag2'}).get_text().strip() or None
        except:
            pass
        try:
            r_dict['link'] = lines[2].find('td', {'class': 'anschlag2'}).get_text().strip() or None
        except:
            pass
        try:
            r_dict['rent'] = lines[3].find('td', {'class': 'anschlag2'}).get_text().strip() or None
        except:
            pass
        try:
            r_dict['contact_name'] = lines[4].find('td', {'class': 'anschlag2'}).get_text().strip() or None
        except:
            pass
        try:
            r_dict['email'] = lines[6].find('td', {'class': 'anschlag2'}).get_text().strip() or None
        except:
            pass
        handle_room(r_dict)
    return result_count


def search_students_ch(header):
    all_rooms = []
    all_room_counts = 0
    login_url = 'http://www.students.ch/adminpanel/user/login'
    try:
        r = session.post(login_url, data={'username': students_ch_username, 'password': students_ch_password},
                         headers=header)
        if r.status_code != 200:
            return
    except:
        return
    url = 'http://www.students.ch/wohnen/list/140/filter:__:{0}-{1}:1-10:0-100/order:date_created/direction:DESC/pager:{2}'
    for page_num in range(1, 10):
        try:
            r = session.get(url.format(priceMin, priceMax, page_num), headers=header)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text)
            all_rooms = soup.find_all('tr', {'class': ['list_row_0', 'list_row_1']})
        except:
            new_ip()

        result_count = len(all_rooms or [])
        for room in all_rooms:
            r_dict = dict(type='WG_s')
            try:
                r_dict['link'] = r'http://www.students.ch' + room.find_all('td')[1].find('a', href=True)['href'].strip()
                if not r_dict['link'].startswith('http://www.students.ch/wohnen/details/'):
                    result_count -= 1
                    continue
                r_dict['rent'] = room.find_all('td')[-1].get_text().strip() or None
                r2 = session.get(r_dict['link'], headers=header)
                if r2.status_code != 200:
                    continue
                room_page = BeautifulSoup(r2.text)
                r_dict['available'] = room_page.find('div', text=re.compile(r'Verfügbarkeit')).findNext(
                    'div').get_text().strip().replace('Frei ab:', '').replace('Frei bis:', ' Until') or None
                if not ('.08.2014' in r_dict['available'] or '.09.2014' in r_dict['available']) or r_dict[
                    'available'].count('2014') > 1:
                    continue
                r_dict['email'] = room_page.find('a', text=re.compile(r'E-Mail an Anbieter'))[
                                      'onclick'].strip().replace(
                    "javascript:location.href = ('mai'+'lto:'+'", '').replace("'+'?b'+'ody='+'');", '').replace("'",
                                                                                                                '').replace(
                    "+", '').replace(" ", '') or None
                r_dict['contact_name'] = \
                    room_page.find('div', text=re.compile(r'Anbieter')).findNext('a')['href'].split('/')[-1] or None
                print(r_dict)
                handle_room(r_dict)
            except Exception as e:
                try:
                    logging.exception(u'{0}'.format(repr(e)))
                except:
                    pass
        if result_count == 0:
            break
        all_room_counts += result_count
    print(all_room_counts)
    return all_room_counts


def search_wgzimmer(header, state):
    all_rooms = []
    try:
        url = r'http://www.wgzimmer.ch/en/wgzimmer/search/mate.html?'
        r = session.post(
            url, data={'country': 'ch',
                       'orderBy': 'MetaData/@mgnl:lastmodified',
                       'orderDir': 'descending',
                       'priceMax': priceMax,
                       'priceMin': priceMin,
                       'query': '',
                       'startSearchMate': 'true',
                       'state': state,
                       'student': 'none',
                       'wgStartSearch': 'true'},
            headers=header)
        if r.status_code != 200:
            return 0
        soup = BeautifulSoup(r.text)
        all_rooms = soup.find('ul', {'class': 'list'}).find_all('li')
    except:
        new_ip()

    r_dict = dict(type='WG')
    result_count = len(all_rooms or [])
    print(result_count)
    for room in all_rooms:
        room_id = room.find_all('a', href=True)[0]['id']
        room = room.find_all('a', href=True)[1]
        try:
            r_dict['link'] = r'http://www.wgzimmer.ch' + room['href']
            r_dict['available'] = room.find('span', {'class': 'from-date'}).get_text().strip().replace(
                '\n\n\t\t\t\t\t\t\t\t', ' ') or None
            r_dict['rent'] = room.find('span', {'class': 'cost'}).get_text().strip() or None

            r2 = session.get(r'http://www.wgzimmer.ch/show-contact/search-mate-contact?uuid={0}'.format(room_id),
                             headers=header)
            if r2.status_code != 200:
                return 0
            room_contact = BeautifulSoup(r2.text)
            contact_info = room_contact.find_all('p')
            [s.extract() for s in contact_info[0]('strong')]
            [s.extract() for s in contact_info[1]('strong')]
            r_dict['contact_name'] = contact_info[0].get_text().strip() or None
            r_dict['email'] = contact_info[1].get_text().strip() or None
            handle_room(r_dict)
        except Exception as e:
            try:
                logging.exception(u'{0}'.format(repr(e)))
            except:
                pass
    return result_count


if __name__ == "__main__":
    gc.enable()
    main_crawler()