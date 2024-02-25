import asyncio

from pychs import CHSTides

async def main():

    tides = CHSTides(coordinates=(44.67,-63.60), measurement="ft") # Work
    await tides.set()
    print(tides.station_information)

    print("** Update **")
    await tides.update()
    print(tides.conditions)

    # Call REST API 
    print(await tides.height_type(heightTypeId="5cec2eba3d0f4a04cc64d5d7"))


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_until_complete(asyncio.sleep(1))
loop.close()