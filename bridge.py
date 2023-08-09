import sys
if "idlelib" in sys.modules:
    print("run in a terminal...")
    sys.exit(1)

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils.multiranger import Multiranger
from cflib.utils import uri_helper

import serial
import asyncio
import os


URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')

DEFAULT_HEIGHT = 0.5

def is_close(reading):
    return reading is None or reading < 0.3  # 30 cm = about 1 foot

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
                queue.get_nowait()
                queue.task_done()
    finally:
        port.close()

async def fly(scf, mr, mc):
    vx, vy, vz = 0, 0, 0
    MAX_VEL = 0.5
    try:
        while True:
            await asyncio.sleep(0)
            try:
                what, where = queue.get_nowait()
            except asyncio.QueueEmpty:
                mc.stop()
                vx, vy, vz = 0, 0, 0
                continue
            queue.task_done()
            match what:
                case "x":
                    vx = where * MAX_VEL / 50
                case "y":
                    vy = where * MAX_VEL / 50
                case "a":
                    vz = where * MAX_VEL
            # Safety guards
            if is_close(mr.front) and vx > 0:
                vx = 0
            if is_close(mr.back) and vx < 0:
                vx = 0
            if is_close(mr.left) and vy > 0:
                vy = 0
            if is_close(mr.right) and vy < 0:
                vy = 0
            if is_close(mr.up) and vz > 0:
                vz = 0
            if is_close(mr.down) and vz < 0:
                vz = 0
            print(f"moving {vx=} {vy=} {vz=}")
            mc.start_linear_motion(vx, vy, vz)
    finally:
        mc.stop()

async def main(scf, mr, mc, port):
    await asyncio.gather(fly(scf, mr, mc), readserial(port))

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    # hack to allow me access to serial
    os.system("sudo chown $USER /dev/serial0")
    port = serial.Serial("/dev/serial0", 115200, timeout=0.1, exclusive=True)
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        print("SyncCrazyflie ok")
        with Multiranger(scf) as multiranger:
            print("Multiranger ok")
            with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as motion_commander:
                print("MotionCommander ok")
                asyncio.run(main(scf, multiranger, motion_commander, port))
