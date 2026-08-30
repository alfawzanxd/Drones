import asyncio
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan


async def connect(drone):
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected")
            break


async def create_mission(lat, lon):
    return MissionItem(
        lat, lon, 5, 4, True,
        float("nan"), float("nan"),
        MissionItem.CameraAction.NONE,
        0, float("nan"), 1, 0,
        float("nan"),
        MissionItem.VehicleAction.NONE
    )


async def battery(drone):
    async for b in drone.telemetry.battery():
        print(f"Battery: {b.remaining_percent * 100:.0f}%")

        if b.remaining_percent < 0.20:
            print("Low battery")
            await drone.action.return_to_launch()
            break


async def main():
    drone = System()

    await drone.connect(system_address="udp://:14540")
    await connect(drone)

    home = await anext(drone.telemetry.home())

    lat = home.latitude_deg
    lon = home.longitude_deg

    size = 10 * 1e-5

    points = [
        (lat + size, lon),
        (lat + size, lon + size),
        (lat, lon + size),
        (lat - size, lon + size),
        (lat - size, lon),
        (lat - size, lon - size),
        (lat, lon)
    ]

    mission = []

    for a, b in points:
        mission.append(await create_mission(a, b))

    await drone.mission.upload_mission(MissionPlan(mission))

    print("Arming")
    await drone.action.arm()

    print("Taking off")
    await drone.action.takeoff()
    await asyncio.sleep(5)

    asyncio.create_task(battery(drone))

    print("Starting mission")
    await drone.mission.start_mission()

    async for progress in drone.mission.mission_progress():
        print(f"Mission: {progress.current}/{progress.total}")

        if progress.current == progress.total:
            break

    print("Returning home")
    await drone.action.set_return_to_launch_altitude(5)
    await drone.action.return_to_launch()

    async for state in drone.telemetry.landed_state():
        if state == state.ON_GROUND:
            print("Landed")
            break


asyncio.run(main())