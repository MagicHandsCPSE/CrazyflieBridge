import sys
if "idlelib" in sys.modules:
    print("run in a terminal...")
    sys.exit(1)

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper

import serial
import asyncio
import os

import RPi.GPIO as gpio

URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

DEFAULT_HEIGHT = 0.2

STATUS_PIN = 21
SWITCH_PIN = 20

queue = asyncio.Queue(16)


async def readserial(port):
    try:
        while True:
            await asyncio.sleep(0)
            try:
                what, where = port.readline().decode("ascii").strip().split("=")
            except ValueError:
                # raised on empty line
                continue
            try:
                queue.put_nowait((what, int(where)))
            except asyncio.QueueFull:
                pass
    finally:
        port.close()

async def fly(scf, mc):
    vx, vy, vz = 0, 0, 0
    MAX_VEL = 0.5
    try:
        while True:
            await asyncio.sleep(0)
            gpio.output(STATUS_PIN, True)
            while gpio.input(SWITCH_PIN) == True:
                await asyncio.sleep(0)
                try:
                    what, where = queue.get_nowait()
                except asyncio.QueueEmpty:
                    mc.stop()
                    continue
                queue.task_done()
                match what:
                    case "x":
                        vx = where * MAX_VEL / 50
                    case "y":
                        vy = where * MAX_VEL / -50  # Y coordinate is backwards
                    case "a":
                        if where != 0:
                            vz = where * -MAX_VEL  # Positive Z is down?!?
                        else:
                            vz *= 0.85  # Decay slowly so it moves easy
                            if abs(vz) < 0.05:
                                vz = 0
                print(f"moving {vx=} {vy=} {vz=}")
                mc.start_linear_motion(vx, vy, vz)
            print("kill switch")
            mc.stop()
            mc.land()
            gpio.output(STATUS_PIN, False)
            while gpio.input(SWITCH_PIN) == False:
                await asyncio.sleep(0.01)
            print("taking off again")
            mc.take_off(DEFAULT_HEIGHT)
    finally:
        gpio.output(STATUS_PIN, False)


async def main(scf, mc, port):
    try:
        gpio.setmode(gpio.BCM)
        gpio.setup(STATUS_PIN, gpio.OUT)
        gpio.setup(SWITCH_PIN, gpio.IN)
        await asyncio.gather(fly(scf, mc), readserial(port))
    finally:
        gpio.cleanup()


if __name__ == '__main__':
    cflib.crtp.init_drivers()
    # hack to allow me access to serial
    os.system("sudo chown $USER /dev/serial0")
    port = serial.Serial("/dev/serial0", 115200, timeout=0.1, exclusive=True)
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        print("SyncCrazyflie ok")
        with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as motion_commander:
            print("MotionCommander ok")
            asyncio.run(main(scf, motion_commander, port))
