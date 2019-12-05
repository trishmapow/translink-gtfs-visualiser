import pickle
import sys
import time
from pprint import pprint

import matplotlib.pyplot as plt
import requests
import smopy
from google.transit import gtfs_realtime_pb2
from protobuf_to_dict import protobuf_to_dict

from dataparser import DataParser

FEED_URL = "https://gtfsrt.api.translink.com.au/Feed/SEQ"
MAP_FILENAME = "bne.bin"
UPDATE_EVERY = 30
BBOX = (152.7, 153.3, -27.7, -27.2)
data = DataParser()


def get_feed(url):
    while True:
        response = requests.get(url)
        if response.status_code == 200:
            break
        print(f"Got status code {response.status_code}, retrying...")
        time.sleep(0.5)
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return protobuf_to_dict(feed)


def map_cache(path, bounding_box):
    try:
        with open(path, 'rb') as map_file:
            map_area = pickle.load(map_file)
    except FileNotFoundError:
        print(f"Map file doesn't exist, writing to {path}. May take a moment.")
        map_area = smopy.Map(bounding_box, maxtiles=512)
        with open(path, 'wb') as map_file:
            pickle.dump(map_area, map_file, protocol=pickle.HIGHEST_PROTOCOL)
    return map_area


def get_entity_type(routes_dict, route_id):
    # Get TransLink URL and extract portion of path with vehicle type
    return routes_dict[route_id]['route_url'].split('/')[5]


def plot_positions(feed, map_area, ax):
    entity_markers = {'buses': 'o', 'trains': 's', 'ferries': 'd', 'trams': '2', 'unknown': 'x'}
    plot_data = {}
    for entity_type in entity_markers:
        plot_data[entity_type] = {'pos': {'xs': [], 'ys': []}, 'colours': [], 'entities': []}

    for entity in feed["entity"]:
        try:
            pos = entity["vehicle"]["position"]
        except KeyError:  # position not available
            continue

        route_id = entity['vehicle']['trip']['route_id']
        if data.routes.get(route_id):
            entity_type = get_entity_type(data.routes, route_id)
        else:
            print(f"Missing route_id {route_id}")
            entity_type = 'unknown'

        plot_data[entity_type]['colours'].append(
            '#' + data.routes[route_id]['route_color'] if entity_type != 'unknown' else '#000000')
        x, y = map_area.to_pixels((pos["latitude"], pos["longitude"]))
        plot_data[entity_type]['pos']['xs'].append(x)
        plot_data[entity_type]['pos']['ys'].append(y)
        plot_data[entity_type]['entities'].append(entity)

    path_to_type = {}
    for entity_type in plot_data:
        path_collection = ax.scatter(*plot_data[entity_type]['pos'].values(), marker=entity_markers[entity_type],
                                     picker=10,
                                     c=plot_data[entity_type]['colours'])
        path_to_type[path_collection] = entity_type
    return path_to_type, plot_data


def main():
    map_area = map_cache(MAP_FILENAME, (BBOX[2], BBOX[0], BBOX[3], BBOX[1]))
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111)
    ax.imshow(map_area.img)
    textbox = plt.text(0.05, 0.95, "Click to view info", transform=ax.transAxes, fontsize=10,
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=1.0))
    statusbox = plt.text(0.65, 0.2, "Status", transform=ax.transAxes, fontsize=10,
                         verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=1.0))

    def onpick(event):
        ind = event.ind[0]
        artist = event.artist
        v_type = path_to_type[artist]

        print(pprint(plot_data[v_type]['entities'][ind]))  # DEBUG

        v_dict = plot_data[v_type]['entities'][ind]['vehicle']
        info = [v_dict['vehicle']['label'],
                data.routes[v_dict['trip']['route_id']]['route_long_name'],
                f"next: {data.stops[v_dict['stop_id']]['stop_name']}",
                f"{int(time.time()) - v_dict['timestamp']} seconds ago"]
        textbox.set_text('\n'.join(info))
        # plt.draw()

    fig.canvas.mpl_connect('pick_event', onpick)
    fig.canvas.mpl_connect('close_event', lambda _: sys.exit())  # fix not closing properly due to plt.pause()
    plt.title(f"{next(iter(data.agency))} current services")
    plt.axis('off')
    plt.ion()
    plt.show()

    path_to_type = []
    while True:
        feed = get_feed(FEED_URL)
        [path.remove() for path in path_to_type]
        path_to_type, plot_data = plot_positions(feed, map_area, ax)
        for i in range(UPDATE_EVERY, 0, -1):
            statusbox.set_text(
                f"{len(feed['entity'])} entities\n"
                f"{sum(len(e['entities']) for e in plot_data.values())} with positions\n"
                f"Updating in {i}s")
            plt.pause(1)


if __name__ == '__main__':
    main()
