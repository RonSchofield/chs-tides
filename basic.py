import asyncio

from pychs import CHSTides

async def main():

    tides = CHSTides(coordinates=(44.67,-63.60), measurement="ft") # Work
    await tides.set()
    print(tides.station_information)

    print(tides.heights)

    print("** Update **")
    await tides.update()
    print(tides.conditions)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_until_complete(asyncio.sleep(1))
loop.close()