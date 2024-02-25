"""Constants for The Canadian Hydrographic Service (CHS) Integrated Water Level System API."""
from typing import Dict

ENDPOINT = "https://api-iwls.dfo-mpo.gc.ca/api/v1/"

ENDPOINT_STATION_DATA: str = "station_data"
ENDPOINT_STATION: str = "station"
ENDPOINT_STATIONS: str = "stations"
ENDPOINT_STATION_METADATA: str = "station_metadata"
ENDPOINT_TIDE_TABLE: str = "tide-table"
ENDPOINT_TIDE_TABLES: str = "tide-tables"
ENDPOINT_PHENOMENON: str = "phenomenon"
ENDPOINT_PHENOMENA: str = "phenomena"
ENDPOINT_STATION_STATS_DAILY: str = "stations_stats_calculate-daily-means"
ENDPOINT_STATION_STATS_MONTHLY: str = "stations_stats_calculate-monthly-mean"
ENDPOINT_HEIGHT_TYPES: str = "height-types"
ENDPOINT_HEIGHT_TYPE: str = "height-type"

HTTP_OK = 200

URLS: Dict[str, str] = {
    ENDPOINT_STATION_DATA: "stations/{stationId}/data",
    ENDPOINT_STATION: "stations/{stationId}",
    ENDPOINT_STATION_METADATA: "stations/{stationId}/metadata",
    ENDPOINT_TIDE_TABLE: "tide-tables/{tideTableId}",
    ENDPOINT_PHENOMENON: "phenomena/{phenomenonId}",
    ENDPOINT_STATION_STATS_DAILY: "stations/{stationId}/stats/calculate-daily-means",
    ENDPOINT_STATION_STATS_MONTHLY: "stations/{stationId}/stats/calculate-monthly-mean",
    ENDPOINT_HEIGHT_TYPE: "height-types/{heightTypeId}",
}