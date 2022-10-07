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

#async def get_station(**kwargs):
#   """Get the station information"""
#
#    station_schema = vol.Schema(
#        vol.All(
#            {
#                vol.Required(
#                    vol.Any("station_id", "station_code"),
#                    msg="Must be either 'station_id' or 'station_code'",
#                ): object,
#            }
#        )
#    )
#    if "station_id" in kwargs and kwargs["station_id"] is not None:
#        print("station_id")
#    if "station_code" in kwargs and kwargs["station_code"] is not None:
#        print("station_code")

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
                    vol.Optional("language"): object,
                },
                {
                    vol.Optional("station_id"):validate_station_id,
                    vol.Optional("station_code"):validate_station_code,
                    vol.Optional("coordinates"): (
                        vol.All(vol.Or(int,float), vol.Range(-90,90)),
                        vol.All(vol.Or(int,float), vol.Range(-180,180)),
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
        self.station_information = {}

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
        """"Get the latest data from The Canadian Hydrographic Service (CHS)"""

        if self.station_id is None:
            if self.station_code is not None:
                self.station_information = await self.stations()
                self.station_id = self.station_information["id"]
            else:
                self.station_id = await closest_station(self.coordinates[0],self.coordinates[1])
        self.station_information = await self.station_metadata()
        await self.update_heights_metadata()
        self.station_code = self.station_information["code"]

        print(type(self.station_information))
        print(self.language)
        print(datetime.utcnow())

    async def update_heights_metadata(self):
        """ Return station height data """

        height_types = await self.height_types()
        heights_data = self.station_information["heights"]
        for height in heights_data:
            heightTypeId = height["heightTypeId"]
            for height_type in height_types:
                if height_type["id"] == heightTypeId:
                    height["code"] = height_type["code"]
                    height["nameEn"] = height_type["nameEn"]
                    height["nameFr"] = height_type["nameFr"]
                    #height.pop("heightTypeId")

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
            if self.language == 'english':
                height["name"] = h["nameEn"]
            else:
                height["name"] = h["nameFr"]
            height["value"] = h["value"]
            height_data.append(height.copy())
        height_data = sorted(height_data, key = lambda height: (height["value"]), reverse = True)

        return height_data

    """ Integrated Water Level System API Endpoints """

    async def station_data(self, **kwargs: str):
        """ /api/v1/stations/{stationId}/data """

        params = ['time-series-code','from','to']
        qparams = self.validate_query_parameters(params, **kwargs)
        await self.get_station_id()
        url = self.construct_url(
            ENDPOINT_STATION_DATA,
            stationId = self._station_id,
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