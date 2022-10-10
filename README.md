# Canadian Hydrographic Service (pychs)

This package provides for accessing official data on navigating modelled surface currents and water levels by the [Canadian Hydrographic Service](https://tides.gc.ca/en/web-services-offered-canadian-hydrographic-service).

## Rest-API Documentation
`pychs` uses the REST-API programming interface for the Integrated Water Level System to  access the water level database (observations, forecasts, predictions) for stations across Canada.

The public API documentation is available in English only on the following website: (https://api-iwls.dfo-mpo.gc.ca/swagger-ui.html).

## Station Information and Current Tide Conditions

`CHSTides` provides station information and current tide conditions. It automatically determines which station to use based on latitude/longitude provided. It is also possible to specify a specific station code of the form `00490` based on those displayed and  listed on [stations page](https://tides.gc.ca/en/stations). For example:

```python
import asyncio

from pychs import CHSTides

tides_en = CHSTides(coordinates=(44.67,-63.60))
tides_fr = CHSTides(station_code='03251', language='french')
tides_ft = CHSTides(station_code='00490', measurements=ft)

# set must be called before any other function
# only needs to be run once for each station
asyncio.run(tides_en.set())

# station information
print(tide_en.station_information)

# current conditions
asyncio.run(tides_en.update())
print(tides_en.conditions)
```

### Example Station Information
```json
{
    "id": "5cebf1df3d0f4a073c4bbcbb",
    "code": "00490",
    "officialName": "Halifax",
    "latitude": 44.666667,
    "longitude": -63.583333,
    "type": "DISCONTINUED",
    "operating": False,
    "owner": "CHS-SHC",
    "chsRegionCode": "ATL",
    "provinceCode": "NS",
    "classCode": "B",
    "isTidal": True,
    "timeZoneCode": "Canada/Atlantic",
    "isTideTableReferencePort": True,
    "tideTypeCode": "SD",
    "timeSeries": [
        {"code": "wlp", "name": "Water levels"},
        {"code": "wlp-hilo", "name": "Water levels"},
        {"code": "wlo", "name": "Water levels"},
    ],
    "datums": [
        {"code": "CGVD28", "offset": -0.778},
        {"code": "NAD83_CSRS", "offset": -21.664},
    ],
    "heights": [
        {"value": 6.88, "code": "HAT", "name": "Highest Astronomical Tide"},
        {"value": -0.31, "code": "LAT", "name": "Lowest Astronomical Tide"},
        {"value": 6.79, "code": "HHWLT", "name": "Higher High Water Large Tide"},
        {"value": -0.24, "code": "LLWLT", "name": "Lower Low Water Large Tide"},
        {"value": 5.77, "code": "HHWMT", "name": "Higher High Water Mean Tide"},
        {"value": 0.98, "code": "LLWMT", "name": "Lower Low Water Mean Tide"},
        {"value": 5.57, "code": "HWL", "name": "High Water Level"},
        {"value": 1.32, "code": "LWL", "name": "Low Water Level"},
        {"value": 3.39, "code": "MWL", "name": "Mean Water Level"},
    ],
    "measurement": "ft",
    "tideTable": "Atlantic Coast and Bay of Fundy",
}
'''
