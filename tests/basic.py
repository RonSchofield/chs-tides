import asyncio

from aiohttp import ClientSession
from geopy import distance

ENDPOINT = "https://api-iwls.dfo-mpo.gc.ca/api/v1/"

ENDPOINT_STATION_DATA: str = "station_data"
ENDPOINT_STATION: str = "station"
ENDPOINT_STATIONS: str = "stations"

async def get_stations():
    """Get list of all sites from The Canadian Hydrographic Service (CHS), for auto-config."""
    async with ClientSession() as session:
        response = await session.get(
            ENDPOINT + ENDPOINT_STATIONS, timeout=10
        )
        station_json = await response.json()
        await session.close()

    return station_json

async def closest_station(lat, lon):
    """Return the id of the closest station to our lat/lon."""
    station_data = dict()
    station_list = await get_stations()

    def station_distance(station):
        return distance.distance((lat,lon), (station["latitude"], station["longitude"]))

    closest = min(station_list, key=station_distance)

    station_data["id"] = closest["id"]
    station_data["code"] = closest["code"]
    station_data["officialName"] = closest["officialName"]
    station_data["operating"] = closest["operating"]
    station_data["latitude"] = closest["latitude"]
    station_data["longitude"] = closest["longitude"]

    return station_data

async def main():
    #station_list = await get_stations()
    
    id = await closest_station(44.65,-63.98)
    print(id)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_until_complete(asyncio.sleep(1))
loop.close()