#!/usr/bin/env python3

from datetime import datetime
from pprint import pprint
import requests

# url = 'https://api-v3.mbta.com/predictions?filter[stop]=place-sstat,place-north&filter[route_type]=2&filter[stop_sequence]=1&include=stop,route,schedule';

def get_routes(included):
    filtered = {}
    for option in included:
        if option['type'] == "route":
            filtered[option['id']] = {
                "direction_desinations": option['attributes']['direction_destinations']
            }
    return filtered

def get_stops(included):
    filtered = {}
    for option in included:
        if option['type'] == "stop":
            filtered[option['id']] = {
                "platform_code": option['attributes']['platform_code'],
                "station": option['attributes']['name'],
            }
    return filtered

def get_schedules(included):
    filtered = {}
    for option in included:
        if option['type'] == "schedule":
            filtered[option['id']] = {
                "expected_departure": option['attributes']['departure_time']
            }
    return filtered

def get_predictions(included):
    filtered = {}
    for option in included:
        if option['type'] == "prediction":
            filtered[option['id']] = {
                "expected_arrival": option['attributes']['arrival_time'],
                "expected_departure": option['attributes']['departure_time']
            }
    return filtered

# FILTERS -
# filter[stop]=WML-0214-01,WML-0214-02 -> Framingham inbound and outbound
# filter[route_type]=2 -> only looks at predictions for commuter rails
# include=stop,route,schedule -> to get information from the related stops, routes, schedules needed to the board
# url = 'https://api-v3.mbta.com/predictions?filter[stop]=WML-0214-01,WML-0214-02&filter[route_type]=2&include=stop,route,schedule';

url = 'https://api-v3.mbta.com/schedules?filter[stop]=WML-0214-01,WML-0214-02&filter[route_type]=2&include=stop,route,prediction'

try:
    r = requests.get(url).json()
    pprint(r)

    msg = list()

    data = r['data']
    if len(data):
        included = r['included']

        routes = get_routes(included)
        stops = get_stops(included)
        # schedules = get_schedules(included)
        predictions = get_predictions(included)

        # print('Routes')
        # pprint(routes)

        # print('Stops')
        # pprint(stops)

        # print('Schedules')
        # pprint(schedules)

        trains = []
        for schedule in data:
            print('Schedule')
            pprint(schedule)
            relationship_stop_id = schedule['relationships']['stop']['data']['id']
            train = {
                'id': schedule['id'],
                'status': schedule['attributes']['status'],
                'departure_time': datetime.strptime(schedule['attributes']['departure_time'] or schedule[predictions['relationships']['schedule']['data']['id']]['expected_departure'], '%Y-%m-%dT%H:%M:%S%z'),
                'origin': stops[relationship_stop_id]['station'],
                # 'final_destination': 'foo',
                'final_destination': routes[schedule['relationships']['route']['data']['id']]['direction_desinations'][schedule['attributes']['direction_id']],
                'platform_code': stops[relationship_stop_id].get('platform_code', 'TBD'),
            }
            trains.append(train)

        # Sort by combined predictions + schedule list by departureTime in ascending order
        trains.sort(key=lambda train: train['departure_time'])
        pprint(trains)

        msg = [f"{t['departure_time']:%H:%M} {t['final_destination']}" for t in trains]
    else:
        msg = ['No trains']
except Exception as e:
    print(f"An error occurred: {e}")
    msg = ['Error occurred', 'while fetching data']

msg.append(f'As of {datetime.now():%H:%M:%S}')
message = '\n'.join(msg)
print(message)

def send_to_board(message):
    url = 'https://rw.vestaboard.com/'
    headers = {'X-Vestaboard-Read-Write-Key': '4831f93e+138e+484c+9fec+894948aa20a0'}
    payload = {"text": message}
    r = requests.post(url, headers=headers, json=payload)
    print(r.json())

def format(message):
    url = 'https://vbml.vestaboard.com/format'
    payload = {"message": message}
    r = requests.post(url, json=payload)
    pprint(r.json())

# format(message)

