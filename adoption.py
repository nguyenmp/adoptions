import datetime
import json
import logging
import os
import shlex
import subprocess
import sys
import time
from urllib import parse

import requests
from bs4 import BeautifulSoup


LOGGER = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)


class Pet(object):
    def __init__(self, image, name, pet_id, body_func):
        self.image = image
        self.name = name
        self.id = pet_id
        self.body_func = body_func
        self.file_name = '{}_{}'.format(name, pet_id)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return 'Pet(name={}, id={})'.format(self.name, self.id)

    @property
    def body(self):
        return self.body_func(self.id)


def main():
    token = sys.argv[1]
    while True:
        LOGGER.info('Looping at %s', datetime.datetime.now())
        for pet in get_pets() + get_pets2() + get_pets3():
            if has_seen(pet):
                LOGGER.info('Already seen %s', pet)
            else:
                pager_duty(pet, token)
            mark_seen(pet)
        time.sleep(60)


DIRECTORY = os.path.expanduser('~/Desktop/adoptions/')


def has_seen(pet):
    return subprocess.call(['test', '-f', pet.file_name], cwd=DIRECTORY) == 0


def mark_seen(pet):
    subprocess.check_call(['touch', pet.file_name], cwd=DIRECTORY)

def get_pets():
    LOGGER.info('Querying for all pets')
    response = requests.get('https://toolkit.rescuegroups.org/j/3/grid3_layout.php?&toolkitIndex=0&toolkitKey=LQbZuUMn')
    soup = BeautifulSoup(response.text, features="html.parser")
    td_results_cell = soup('td', 'rgtkSearchResultsCell')
    return [
        Pet(
            image=result_cell.div.a.img['src'],
            name=result_cell.text.strip(),
            pet_id=result_cell.div.a.img['src'].split('/')[-2],
            body_func=get_pet,
        )
        for result_cell in td_results_cell
    ]


def get_pet(pet_id):
    response = requests.get('https://toolkit.rescuegroups.org/j/3/pet2_layout.php?toolkitIndex=0&toolkitKey=LQbZuUMn&petfocus_0=&resultSort_0=animalUpdatedDate&resultOrder_0=desc&page_0=1&age_0=&sex_0=&searchString_0=&petIndex=6&animalID={}&recentPets=15937621'.format(pet_id))
    return response.text


def get_pets2(page=1):
    LOGGER.info('Querying for all other pets')
    # 'Accept: application/json, text/javascript, */*; q=0.01' \
    data = {
        'gender': '-',
        'age': '-',
        'name': '-',
        'breed': '-',
        'primary_breed': '-',
        'secondary_breed': '-',
        'color_details': '-',
        'energy_level': '-',
        'special_needs': '-',
        'action': 'api_call',
        'page': page,
        'foster': 0,
    }
    response = requests.post('https://www.ilovefamilydog.org/wp-admin/admin-ajax.php', data=data)
    response.raise_for_status()
    result = json.loads(response.text)
    data = result['data']
    rest = []

    if len(data) > 0:
        rest = get_pets2(page + 1)

    result = [
        Pet(
            image=pet['animalPictures'][0]['large']['url'],
            name=pet['animalName'],
            pet_id=pet['animalID'],
            body_func=get_pet2)
        for pet in data
    ]
    result.extend(rest)
    return result


def get_pet2(pet_id):
    response = requests.get('https://www.ilovefamilydog.org/dog-details/?id={}'.format(pet_id))
    soup = BeautifulSoup(response.text, features="html.parser")
    return soup('p')[-1].text


def get_pets3():
    response = requests.get('https://www.shelterluv.com/available_pets/11413?saved_query=7503&embedded=1&iframeId=shelterluv_embed_114131597715231779&columns=2#https%3A%2F%2Fwww.milofoundation.org%2Fdogs-for-adoption%2F%23sl_embed%26page%3Dshelterluv_embed_114131597715231779%25252Favailable_pets%25252F11413%25253Fsaved_query%25253D7503')
    response.raise_for_status()
    soup = BeautifulSoup(response.text, features="html.parser")
    rows = soup('a')
    return [
        Pet(
            image=row('img')[0]['src'],
            name=row.text.strip(),
            pet_id=os.path.split(parse.urlparse(row['href']).path)[1],
            body_func=get_pet3,
        )
        for row in rows
    ]


def get_pet3(pet_id):
    response = requests.get('https://www.shelterluv.com/publish_animal/{}'.format(pet_id))
    response.raise_for_status()
    soup = BeautifulSoup(response.text, features="html.parser")
    return soup('p')[0].text


def pager_duty(pet, token):
    LOGGER.info('Paging for %s', pet)
    headers = {
        'Authorization': 'Token token={}'.format(token),
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'From': 'nguyenmp605@gmail.com',
    }
    body = {
        "incident": {
            "type": "incident",
            "title": "New dog alert! {} is now available".format(pet.name),
            "service": {
                "id": "P1DEO09",
                "type": "service_reference",
            },
            "body": {
                "details": pet.body,
                "type": "incident_body",
            }
        }
    }
    requests.post('https://api.pagerduty.com/incidents', headers=headers, data=json.dumps(body))


if __name__ == "__main__":
    main()
