#!/usr/bin/env python3

from datetime import datetime
from zoneinfo import ZoneInfo
from functools import reduce
import requests
import operator
import os
from pprint import pprint

def lookup(container, keys, default=None):
    try:
        return reduce(operator.getitem, keys, container)
    except Exception as e:
        return default

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

def get_predictions(included):
    filtered = {}
    for option in included:
        if option['type'] == "prediction":
            filtered[option['id']] = {
                "expected_arrival": option['attributes']['arrival_time'],
                "expected_departure": option['attributes']['departure_time'],
            }
    return filtered

# FILTERS -
# filter[stop]=WML-0214-01,WML-0214-02 -> Framingham inbound and outbound
# filter[route_type]=2 -> only looks at schedules for commuter rails
# include=stop,route,prediction -> to get information from the related stops, routes, prediction needed to the board
url = 'https://api-v3.mbta.com/schedules?filter[stop]=WML-0214-01,WML-0214-02&filter[route_type]=2&include=stop,route,prediction'

try:
    r = requests.get(url).json()
    # pprint(r)
    trains = list()

    data = r['data']
    if len(data):
        included = r['included']

        routes = get_routes(included)
        stops = get_stops(included)
        predictions = get_predictions(included)

        for schedule in data:
            # print('Schedule')
            # pprint(schedule) 
            schedule_id = schedule['id']         
            relationship_route_id = schedule['relationships']['route']['data']['id']
            relationship_stop_id = schedule['relationships']['stop']['data']['id']

            # start with train time based on schedule
            time = lookup(schedule, ('attributes', 'departure_time'))
            # If a train is terminating, departure_time is None and arrival_time is set
            if not time:
                time = lookup(schedule, ('attributes', 'arrival_time'), time)

            # Now, if a prediction is available, use that instead
            relationship_prediction_id = lookup(schedule, ('relationships', 'prediction', 'data', 'id')) 
            if relationship_prediction_id:
                time = lookup(predictions, (relationship_prediction_id, 'expected_departure'), time) # fall back to original if error
                time = lookup(predictions, (relationship_prediction_id, 'expected_arrival'), time)           

            time = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S%z')

            train = {
                'id': schedule_id,
                # 'status': schedule['attributes']['status'],
                'time': time,
                'origin': stops[relationship_stop_id]['station'],
                'final_destination': routes[relationship_route_id]['direction_desinations'][schedule['attributes']['direction_id']],
                'platform_code': stops[relationship_stop_id].get('platform_code', 'TBD'),
            }
            trains.append(train)

        # pprint(trains)
    
except Exception as e:
    print(f"An error occurred: {e}")
    msg = ['Error occurred', 'while fetching data']

# Get _next_ 5 trains
now = datetime.now(ZoneInfo("America/New_York"))
if len(trains):
    trains.sort(key=lambda train: train['time'])
    
    # Filter out the next 5 trains based on the current time
    next_trains = [train for train in trains if train['time'] > now][:5]
    msg = [f"{t['time']:%H:%M} {t['final_destination']}" for t in next_trains]
else:
    msg = ['No trains']

msg.append(f'As of {now:%H:%M:%S}')
message = '\n'.join(msg)
print(message)

def send_to_board(message):
    url = 'https://rw.vestaboard.com/'
    headers = {'X-Vestaboard-Read-Write-Key': os.getenv('VESTABOARD_API_KEY')}
    payload = {"text": message}
    r = requests.post(url, headers=headers, json=payload)
    print(r.json())

def format(message):
    url = 'https://vbml.vestaboard.com/format'
    payload = {"message": message}
    r = requests.post(url, json=payload)
    pprint(r.json())

# format(message)
# send_to_board(message)
