# URL: https://gtfsrt.api.translink.com.au/GTFS/SEQ_GTFS.zip

from pathlib import Path
import csv
import contextlib


class DataParser:
    """Class to load and parse GTFS dataset datasets

    Args:
        path (Path): path to folder containing GTFS files
        dataset_names (Tuple[str, str]): dataset name and key to use as index

    Attributes:
        agency (dict)
        routes (dict)
        stops (dict)
        trips (dict)
    """

    def __init__(
        self,
        path=Path("SEQ_GTFS"),
        dataset_names=(
            ("agency", "agency_name"),
            ("routes", "route_id"),
            ("stops", "stop_id"),
            ("trips", "trip_id"),
        ),
    ):
        self.agency = self.routes = self.stops = self.trips = None
        with contextlib.ExitStack() as stack:
            datasets = {
                dataset: {
                    row[key]: row
                    for row in csv.DictReader(
                        stack.enter_context(open(path / (dataset + ".txt")))
                    )
                }
                for dataset, key in dataset_names
            }
        self.__dict__.update(datasets)


if __name__ == "__main__":
    # DEBUG
    s = DataParser()
    print(*next(iter(s.agency.values())).values())
    try:
        while True:
            in_ = input("[dictname] [dictkey] >>> ").split()
            print(getattr(s, in_[0])["".join(in_[1:])])
    except (KeyboardInterrupt, EOFError):
        print("Exiting...")
