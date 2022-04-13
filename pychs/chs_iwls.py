import logging
import json

from aiohttp import ClientSession
from geopy import distance
from typing import Any, Dict, Union

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

_LOGGER = logging.getLogger(__name__)

class CHS_IWLS:
    """Main class for The Canadian Hydrographic Service (CHS) API requests."""

    def __init__(
        self,
        station_id = None,
        station_code = None,
        coordinates = None,
        language = "english",
    ):
        """Initialize the data object."""
        self._station_id = ''
        self._station_code = ''
        self._coordinates = None
        if station_id:
            # Validate Station Id
            self._station_id = station_id
        if station_code:
            # Validate Station Code
            self._station_code = station_code
        elif coordinates:
            # Validate Latitude and Longitude
            if not self._valid_coordinates(*coordinates):
                raise InvalidCoordinatesError(
                    "Your coordinates are invalid"
                )
            self._coordinates = coordinates
        self._language = language
        self._station_name = ''
        self._station_operating = False
        self._station_timeSeries = None
        self._url = None

    """ Static Methods """

    @staticmethod
    def _valid_station_id(station_id: str) -> bool:
        try:
            assert isinstance(station_id, str)
            assert len(station_id) == 24
        except AssertionError:
            return False
        return True

    @staticmethod
    def _valid_coordinates(latitude: Union[float, int, None], longitude: Union[float, int, None]) -> bool:
        """ Return True if coordinates are valid """
        try:
            assert isinstance(latitude, (int, float)) and isinstance(longitude, (int, float))
            assert abs(latitude) <= 90 and abs(longitude) <= 180
        except (AssertionError, TypeError):
            return False
        return True

    @staticmethod
    def _construct_url(arg: str, **kwargs: str):
        """ Construct Integrated Water Level System API URL """
        url = ENDPOINT + URLS[arg].format(**kwargs)
        return url

    @staticmethod
    def _validate_query_parameters(params, **kwargs: str):
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
    def _construct_query_parameters(**kwargs: str):
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

    async def _set_station_data(self, data):
        self._station_id = data['id']
        self._station_code = data['code']
        self._station_name = data['officialName']
        self._coordinates = str(data['latitude']) + ',' + str(data['longitude'])
        self._station_operating = data['operating']
        self._station_timeSeries = data['timeSeries']

    async def _get_stations(self):
        """Get list of all sites from The Canadian Hydrographic Service (CHS), for auto-config."""
        async with ClientSession() as session:
            response = await session.get(ENDPOINT + ENDPOINT_STATIONS, timeout=10)
            station_json = await response.json()
            await session.close()
            return station_json

    async def _closest_station(self, lat, lon):
        """Return the id of the closest station to our lat/lon."""
        station_list = await self._get_stations()

        def station_distance(station):
            return distance.distance((lat,lon), (station["latitude"], station["longitude"]))

        closest = min(station_list, key=station_distance)
        await self._set_station_data(closest)
        return closest["id"]

    async def _get_station_id(self):
        # Determine station ID if not provided
        if not self._station_id and self._coordinates:
            self._station_id = await self._closest_station(*self._coordinates)

    async def _async_get_data(self, url):
        """ Retreive data from Integrated Water Level System API URL """
        self._url = url
        async with ClientSession() as session:
            response = await session.get(url)
            headers = response.headers
            if headers.get('content-type') == 'application/json':
                data = await response.json()
            else:
                data = '0'   
            await session.close()
            return data

    """ Integrated Water Level System API Endpoints """

    async def station_data(self, **kwargs: str):
        """ /api/v1/stations/{stationId}/data """
        params = ['time-series-code','from','to']
        qparams = self._validate_query_parameters(params, **kwargs)
        await self._get_station_id()
        url = self._construct_url(
            ENDPOINT_STATION_DATA,
            stationId = self._station_id,
        ) + self._construct_query_parameters(**qparams)
        data = await self._async_get_data(url)
        return data

    async def stations(self, **kwargs: str):
        """ /api/v1/stations """
        params = ['code','chs-region-code','time-series-code']
        if self._station_code and kwargs.get('code') == None:
            kwargs['code'] = self._station_code
        qparams = self._validate_query_parameters(params, **kwargs)
        url = ENDPOINT + ENDPOINT_STATIONS + self._construct_query_parameters(**qparams)
        data = await self._async_get_data(url)
        if qparams.get('code') != None:
            await self._set_station_data(data[0])
        return data

    async def station(self):
        """ /api/v1/stations/{stationId} """
        await self._get_station_id()
        url = self._construct_url(
            ENDPOINT_STATION,
            stationId = self._station_id,
        )
        data = await self._async_get_data(url)
        await self._set_station_data(data)
        return data

    async def station_metadata(self):
        """ /api/v1/stations/{stationId}/metadata """
        # Find station summery from ID
        if not self._station_id and self._coordinates:
            self._station_id = await self._closest_station(*self._coordinates)
        url = self._construct_url(
            ENDPOINT_STATION_METADATA,
            stationId = self._station_id,
        )
        data = await self._async_get_data(url)
        await self._set_station_data(data)
        return data

    async def tide_tables(self, **kwargs: str):
        """ /api/v1/tide-tables """
        params = ['type','parent-tide-table-id']
        qparams = self._validate_query_parameters(params, **kwargs)
        url = ENDPOINT + ENDPOINT_TIDE_TABLES + self._construct_query_parameters(**qparams)
        data = await self._async_get_data(url)
        return data

    async def tide_table(self,tideTableId):
        """ /api/v1/tide-tables/{tideTableId} """
        url = self._construct_url(
            ENDPOINT_TIDE_TABLE,
            tideTableId = tideTableId,
        )
        data = await self._async_get_data(url)
        return data   

    async def phenomena(self):
        """ /api/v1/phenomena """
        url = ENDPOINT + ENDPOINT_PHENOMENA
        data = await self._async_get_data(url)
        return data

    async def phenomenon(self,phenomenonId):
        """ /api/v1/phenomena/{phwnomenonId} """
        url = self._construct_url(
            ENDPOINT_PHENOMENON,
            phenomenonId = phenomenonId,
        )
        data = await self._async_get_data(url)
        return data   

    async def station_monthly_mean(self, **kwargs: str):
        """ /api/v1/stations/{stationId}/stats/calculate-monthly-mean """
        params = ['year','month']
        qparams = self._validate_query_parameters(params, **kwargs)
        url = self._construct_url(
            ENDPOINT_STATION_STATS_MONTHLY,
            stationId = self._station_id,
        ) + self._construct_query_parameters(**qparams)
        data = await self._async_get_data(url)
        return data

    async def get_height_types(self):
        """ /api/v1/"height-types """
        url = ENDPOINT + ENDPOINT_HEIGHT_TYPES
        data = await self._async_get_data(url)
        return data

    async def get_height_type(self, heightTypeId):
        """ /api/v1/"height-types/{heightTypeId} """
        url = self._construct_url(
            ENDPOINT_HEIGHT_TYPE,
            heightTypeId = heightTypeId,
        )
        data = await self._async_get_data(url)
        return data

    @property
    def station_id(self):
        """ Return station id """
        return self._station_id

    @property
    def station_code(self):
        """ Return station code """
        return self._station_code

    @property
    def station_name(self):
        """ Return station name """
        return self._station_name
        
    @property
    def station_operating(self):
        """ Return station operation """
        return self._station_operating

    @property
    def coordinates(self):
        """ Return station operation """
        return self._coordinates

    @property
    def station_timeSeries(self):
        """ Return station operation """
        return self._station_timeSeries

    @property
    def url(self):
        """ Return last used url """
        return self._url

class InvalidCoordinatesError(Exception):
    def __init__(self, status: str):
        super().__init__(status)
        self.status = status