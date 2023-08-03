import logging
import sys
import time
from threading import Event

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.utils import uri_helper


URI = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
flowdeck_attacked = Event()

DEFAULT_HEIGHT = 0.5


def flow_deck_callback(_, value_str):
    value = int(value_str)
    print(value, end=" => ")
    if value:
        flowdeck_attacked.set()
        print('Deck is attached!')
    else:
        print('Deck is NOT attached!')

def main(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        try:
            time.sleep(3)
        finally:
            mc.stop()

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        scf.cf.param.add_update_callback(group="deck", name="bcFlow2", cb=flow_deck_callback)
        if not flowdeck_attacked.wait(timeout=10):
            print('error: flow deck not detected')
            sys.exit(1)
        main(scf)