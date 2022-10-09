import logging
import json
import re

from aiohttp import ClientSession
from datetime import datetime, timedelta
from geopy import distance
from typing import Any, Dict, Union
import voluptuous as vol

from .const import (
    ENDPOINT,
    ENDPOINT_STATION,
    ENDPOINT_STATIONS,
    ENDPOINT_STATION_DATA,
    ENDPOINT_STATION_METADATA,
    ENDPOINT_STATION_STATS_DAILY,
    ENDPOINT_STATION_STATS_MONTHLY,
    ENDPOINT_HEIGHT_TYPE,
    ENDPOINT_HEIGHT_TYPES,
    ENDPOINT_PHENOMENA,
    ENDPOINT_PHENOMENON,
    ENDPOINT_TIDE_TABLE,
    ENDPOINT_TIDE_TABLES,
    URLS,
)

M2FT : float = 3.28084

LOG = logging.getLogger(__name__)

__all__ = ["CHSTides"]


def validate_station_id(station_id):
    """Check that the station id is well-formed."""
    if station_id is None:
        return
    if not re.fullmatch(r"[0-9a-f]{24}", station_id):
        raise vol.Invalid('Station ID must be a 24 character hexidecimal')
    return station_id


def validate_station_code(station_code):
    """Check that the station code is well-formed."""
    if station_code is None:
        return
    if not re.fullmatch(r"\d{5}", station_code):
        raise vol.Invalid('Station Code must be of the form "#####"')
    return station_code

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
    
    station_list = await get_stations()

    def station_distance(station):
        return distance.distance((lat,lon), (station["latitude"], station["longitude"]))

    closest = min(station_list, key=station_distance)

    return closest["id"]

async def get_data(url):
    """ Retreive data from Integrated Water Level System API URL """

    async with ClientSession() as session:
        response = await session.get(url)
        headers = response.headers
        if headers.get('content-type') == 'application/json':
            data = await response.json()
        else:
            data = '0'   
        await session.close()

    return data

class CHSTides(object):
    """Main class for The Canadian Hydrographic Service (CHS) API requests."""

    def __init__(self, **kwargs):
        """Initialize the data object"""

        init_schema = vol.Schema(
            vol.All(
                {
                    vol.Required(
                        vol.Any("station_id", "station_code", "coordinates"),
                        msg="Must specify either 'station id', 'station code' or 'corrdinates'",
                    ): object,
                    vol.Optional("measurement"): object,
                    vol.Optional("language"): object,
                },
                {
                    vol.Optional("station_id"):validate_station_id,
                    vol.Optional("station_code"):validate_station_code,
                    vol.Optional("coordinates"): (
                        vol.All(vol.Or(int,float), vol.Range(-90,90)),
                        vol.All(vol.Or(int,float), vol.Range(-180,180)),
                    ),
                    vol.Optional("measurement", default="m"): vol.In(
                        ["m", "ft"]
                    ),
                    vol.Optional("language", default="english"): vol.In(
                        ["english", "french"]
                    ),
                },
            )
        )

        kwargs = init_schema(kwargs)

        self.station_id = None
        self.station_code = None
        self.coordinates = None
        self.language = kwargs["language"]
        self.measurement = kwargs["measurement"]
        self.station_information = {}
        self.conditions = {}

        if "station_id" in kwargs and kwargs["station_id"] is not None:
            self.station_id = kwargs["station_id"]
        elif "station_code" in kwargs and kwargs["station_code"] is not None:
            self.station_code = kwargs["station_code"]
        else:
            self.coordinates = kwargs["coordinates"]
  
    """ Static Methods """

    @staticmethod
    def construct_url(arg: str, **kwargs: str):
        """ Construct Integrated Water Level System API URL """

        url = ENDPOINT + URLS[arg].format(**kwargs)
        return url

    @staticmethod
    def validate_query_parameters(params, **kwargs: str):
        """ Validate query parameters """

        timeseriescodes = ['wlo','wlp','wlp-hilo','wlp-bores','wcp-slack','wlf','wlf-spine','dvcf-spine']
        qparams = {}
        for i in kwargs:
            if i in params:
                if (i == 'from' or i == 'to'):
                    qparams[i] = kwargs[i].isoformat()[:-7]+'Z'
                elif i == 'time-series-code':
                    if kwargs[i] in timeseriescodes:
                        qparams[i] = kwargs[i]
                else:
                    qparams[i] = kwargs[i]
        return qparams

    @staticmethod
    def construct_query_parameters(**kwargs: str):
        """ Construct Integrated Water Level System API Query Parameters """

        query = ''
        counter = 1
        for i in kwargs:
            if counter == 1:
                query = '?' + i + '=' + kwargs[i]
            else:
                query = query + '&' + i + '=' + kwargs[i]
            counter += 1
        return query

    """ Internal Methods """

    async def set(self):
        """" Set the station information """

        if self.station_id is None:
            if self.station_code is not None:
                self.station_information = await self.stations()
                self.station_id = self.station_information["id"]
            else:
                self.station_id = await closest_station(self.coordinates[0],self.coordinates[1])
        self.station_information = await self.station_metadata()
        await self.update_heights_metadata()
        await self.update_tidetable_metadata()
        await self.update_timeseries_metadata()
        self.station_code = self.station_information["code"]

    async def update(self):
        """" Get the latest data from The Canadian Hydrographic Service (CHS) """

        if self.station_id is None:
            await self.set()
        self.conditions["conditions"] = await self.current_conditions()
        self.conditions["hilo"] = await self.last_next_hilo()

    async def current_conditions(self):
        """" Get the current tide conditions """
        
        conditions = dict()
        currentDT = datetime.utcnow()
        parameters = {
            "time-series-code":"wlp",
            "from":currentDT - timedelta(hours=7),
            "to":currentDT + timedelta(hours=7)
        }
        tide_data = await self.station_data(**parameters)
        event_previous = None           # previous event value
        event_next = None               # next event value
        event_date = None               # date of event just before current
        low_value = 99                  # Set to high value that can never be reached
        high_value = -99                # Set to low value that can never be reached
        for event in tide_data:
            eventDate = datetime.strptime(event["eventDate"],"%Y-%m-%dT%H:%M:%SZ")
            eventValue = event["value"]
            if self.measurement == 'ft':
                eventValue = round(event["value"] * M2FT,2)
            # set high and low tide height values
            if eventValue < low_value:
                low_value = eventValue
            if eventValue > high_value:
                high_value = eventValue
            # check for time compared to current
            if eventDate < currentDT:
                event_previous = eventValue
                event_date = eventDate
            if eventDate > currentDT and event_next == None:
                event_next = eventValue
                break
        # Set conditions data       
        conditions["value"] = event_previous
        conditions["eventDate"] = event_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        # figure out if tide is rising or falling
        if event_previous < event_next:
            conditions["status"] = "rising"
        else:
            conditions["status"] = "falling"

        return conditions

    
    async def last_next_hilo(self):
        """ Get the last and next high and low times """

        lowtideLang = ["low tide","marée basse"]
        hightideLang = ["high tide","marée haute"]
        if self.language == "english":
            lang = 0
        else:
            lang = 1
        currentDT = datetime.utcnow()
        parameters = {
            "time-series-code":"wlp-hilo",
            "from":currentDT - timedelta(hours=7),
            "to":currentDT + timedelta(hours=7)
        }
        tide_data = await self.station_data(**parameters)
        for event in tide_data:
            event.pop("qcFlagCode")
            event.pop("timeSeriesId")
            if self.measurement == 'ft':
                event["value"] = round(event["value"] * M2FT,2)
        if tide_data[0]["value"] < tide_data[1]["value"]:
            tide_data[0]["event"] = lowtideLang[lang]
            tide_data[1]['event'] = hightideLang[lang]
        else:
            tide_data[0]["event"] = hightideLang[lang]
            tide_data[1]["event"] = lowtideLang[lang]

        return tide_data


    async def update_timeseries_metadata(self):
        """ Replace timeSeries phenomenonId with laquage name """

        timeSeries_Data = self.station_information["timeSeries"]
        for timeSeries in timeSeries_Data:
            timeSeries.pop("id")
            if self.language == 'english':
                timeSeries["name"] = timeSeries["nameEn"]
            else:
                timeSeries["name"] = timeSeries["nameFr"]
            timeSeries.pop("nameEn")
            timeSeries.pop("nameFr")
            phenomena = await self.phenomenon(timeSeries["phenomenonId"]) 
            if self.language == "english":
                timeSeries["name"] = phenomena["nameEn"]
            else:
                timeSeries["name"] = phenomena["nameFr"]
            timeSeries.pop("phenomenonId")

    async def update_tidetable_metadata(self):
        """ Replace tideTableId with langauge name """

        tidetable = await self.tide_table(self.station_information["tideTableId"])
        if self.language == "english":
           self.station_information["tideTable"] = tidetable["nameEn"]
        else:
           self.station_information["tideTable"] = tidetable["nameFr"] 
        self.station_information.pop("tideTableId")


    async def update_heights_metadata(self):
        """ Replace heightTypeId with langauge name """

        height_types = await self.height_types()
        heights_data = self.station_information["heights"]
        for height in heights_data:
            heightTypeId = height["heightTypeId"]
            for height_type in height_types:
                if height_type["id"] == heightTypeId:
                    height["code"] = height_type["code"]
                    if self.language == 'english':
                        height["name"] = height_type["nameEn"]
                    else:
                        height["name"] = height_type["nameFr"]
                    height.pop("heightTypeId")
            if self.measurement == 'ft':
                height["value"] = round(height["value"] * M2FT,2)
                    
    @property
    def timeSeries_codes(self):
        """ Return time station series codes """

        ts_codes = []
        for ts in self.station_information["timeSeries"]:
            ts_codes.append(ts["code"])

        return ts_codes

    @property
    def heights(self):
        """ Get the sorted heights in highest to lowest """

        height_data = []
        height = {}
        for h in self.station_information["heights"]:
            height["code"] = h["code"]
            height["name"] = h["name"]
            height["value"] = h["value"]
            height_data.append(height.copy())
        height_data = sorted(height_data, key = lambda height: (height["value"]), reverse = True)

        return height_data

    """ Integrated Water Level System API Endpoints """

    async def station_data(self, **kwargs: str):
        """ /api/v1/stations/{stationId}/data """

        params = ['time-series-code','from','to']
        qparams = self.validate_query_parameters(params, **kwargs)
        url = self.construct_url(
            ENDPOINT_STATION_DATA,
            stationId = self.station_id,
        ) + self.construct_query_parameters(**qparams)
        data = await get_data(url)

        return data

    async def stations(self, **kwargs: str):
        """ /api/v1/stations """

        params = ['code','chs-region-code','time-series-code']
        if self.station_code and kwargs.get('code') == None:
            kwargs['code'] = self.station_code
        qparams = self.validate_query_parameters(params, **kwargs)
        url = ENDPOINT + ENDPOINT_STATIONS + self.construct_query_parameters(**qparams)
        data = await get_data(url)

        return data

    async def station(self):
        """ /api/v1/stations/{stationId} """

        url = self.construct_url(
            ENDPOINT_STATION,
            stationId = self.station_id,
        )
        data = await get_data(url)

        return data

    async def station_metadata(self):
        """ /api/v1/stations/{stationId}/metadata """

        # Find station summery from ID
        if not self.station_id and self.coordinates:
            self.station_id = await self.closest_station(*self.coordinates)
        url = self.construct_url(
            ENDPOINT_STATION_METADATA,
            stationId = self.station_id,
        )
        data = await get_data(url)

        return data

    async def tide_tables(self, **kwargs: str):
        """ /api/v1/tide-tables """

        params = ['type','parent-tide-table-id']
        qparams = self.validate_query_parameters(params, **kwargs)
        url = ENDPOINT + ENDPOINT_TIDE_TABLES + self.construct_query_parameters(**qparams)
        data = await get_data(url)

        return data

    async def tide_table(self,tideTableId):
        """ /api/v1/tide-tables/{tideTableId} """

        url = self.construct_url(
            ENDPOINT_TIDE_TABLE,
            tideTableId = tideTableId,
        )
        data = await get_data(url)

        return data   

    async def phenomena(self):
        """ /api/v1/phenomena """

        url = ENDPOINT + ENDPOINT_PHENOMENA
        data = await get_data(url)

        return data

    async def phenomenon(self,phenomenonId):
        """ /api/v1/phenomena/{phwnomenonId} """

        url = self.construct_url(
            ENDPOINT_PHENOMENON,
            phenomenonId = phenomenonId,
        )
        data = await get_data(url)

        return data   

    async def station_monthly_mean(self, **kwargs: str):
        """ /api/v1/stations/{stationId}/stats/calculate-monthly-mean """

        params = ['year','month']
        qparams = self.validate_query_parameters(params, **kwargs)
        url = self.construct_url(
            ENDPOINT_STATION_STATS_MONTHLY,
            stationId = self._station_id,
        ) + self.construct_query_parameters(**qparams)
        data = await get_data(url)

        return data

    async def height_types(self):
        """ /api/v1/"height-types """

        url = ENDPOINT + ENDPOINT_HEIGHT_TYPES
        data = await get_data(url)

        return data

    async def height_type(self, heightTypeId):
        """ /api/v1/"height-types/{heightTypeId} """

        url = self.construct_url(
            ENDPOINT_HEIGHT_TYPE,
            heightTypeId = heightTypeId,
        )
        data = await get_data(url)

        return data

class InvalidCoordinatesError(Exception):
    def __init__(self, status: str):
        super().__init__(status)
        self.status = status