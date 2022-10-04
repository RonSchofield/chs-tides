import asyncio

from pychs import CHSTides

async def main():

    #tides = CHSTides(station_id='5cebf1df3d0f4a073c4bbcb5')
    #tides = CHSTides(station_code='00482')
    #tides = CHSTides(coordinates=(44.65,-63.98)) # Home
    tides = CHSTides(coordinates=(44.67,-63.60)) # Work
    await tides.update()
    print(tides.station_id)
    print(tides.station_code)
    print(tides.station_name)
    print(tides.coordinates)
    print(tides.timeSeries_codes)
    print(tides.heights)

    print("ran")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_until_complete(asyncio.sleep(1))
loop.close()