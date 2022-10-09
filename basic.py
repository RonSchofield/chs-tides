import asyncio

from pychs import CHSTides

async def main():

    #tides = CHSTides(station_id='5cebf1df3d0f4a073c4bbcb5')
    #tides = CHSTides(station_code='00482')
    #tides = CHSTides(coordinates=(44.65,-63.98)) # Home
    tides = CHSTides(coordinates=(44.67,-63.60), measurement="ft") # Work
    await tides.set()
    #print(tides.station_id)
    #print(tides.station_code)
    print(tides.station_information)
    #print(tides.measurement)
    #print(tides.language)
    #print("** heights **")
    #print(tides.heights)
    print("** Update **")
    await tides.update()
    print("** Conditions **")
    print(tides.conditions)

    print("ran")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_until_complete(asyncio.sleep(1))
loop.close()