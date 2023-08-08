import serial, os
os.system("sudo chown $USER /dev/serial0")

port = serial.Serial("/dev/serial0", 115200, timeout=0.1, exclusive=True)
import asyncio

this = {'x': 0, 'y': 0, 'a': 0}

async def readserial(port):
    global this
    try:
        while True:
            try:
                what, where = port.readline().decode("ascii").strip().split("=")
                where = int(where)
                this[what] = where
            except ValueError:
                # raised on empty line
                this = {'x': 0, 'y': 0, 'a': 0}
                continue
            print(f"{this=}")
            await asyncio.sleep(0)
    finally:
        port.close()

asyncio.run(readserial(port))
