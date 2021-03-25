import asyncio
import logging
import math
from asyncio import Task
import numpy as np

import serial_asyncio
import time

import RunSM
from BSP import Signal
from Payload import Payload

logger = logging.getLogger(__name__)

class PSerial(asyncio.Protocol):

    def __init__(self, qlog = None):
        super().__init__()
        self._transport = None
        self.runsm : RunSM

        self.beacon_task:Task = None
        self.beacon_tick = 0.25

        self.payload = Payload()

        # self.x1 = list(range(-20, 21))
        # self.y1 = [(xx**2)+200 for xx in self.x]

        x2 = np.arange(0, 1, 0.025)
        self.y2 = (np.sin(2*np.pi*x2)+2)*10000
        self.y3 = self.y2.astype(int)
        self.bflen = len(self.y3)-2

        self.configLogger(qlog)

    def connection_made(self, transport):
        self.transport = transport
        print('Port opened')
        transport.serial.rts = False  # You can manipulate Serial object via transport
        # transport.write(b'Hello, World!\r\n')  # Write serial data via transport


    def setRunSM(self, rsm):
        self.runsm = rsm

    def sendRawData(self, data):
        # print ('data to send : ', data)
        if isinstance(data, str):
            data = bytes(data, 'utf8')
        self.transport.write(data)


    def data_received(self, data):
        print('data received', repr(data))
        if b'\x1b' in data:
            self.transport.close()
            exit()
        else:
            pass
            # self.transport.write(data)


    def connection_lost(self, exc):
        print('port closed')
        self.transport.loop.stop()

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')


    def configLogger(self, qlog):

        logger.setLevel(logging.DEBUG)
        if qlog is None:
            ch = logging.StreamHandler()
        else:
            ch = logging.StreamHandler(qlog)

        formatter = logging.Formatter('%(msecs).2f - %(levelno)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)


    async def SLoop(self):

        counter = 0;
        while True:

            # s = 'Data from SLoop @ {}\n\r'.format(counter)
            # self.payload.setSensor(value=counter)

            # s = self.payload.getBytes()


            #  Github push commint & test

            if counter > self.bflen :
                counter = 0
            else:
                counter +=1

            s = self.payload.getBytes(None, self.y3[counter])
            # s = self.payload.getBytes(None, counter )
            self.sendRawData(s)

            await asyncio.sleep(self.beacon_tick)


    def sendCallback(self, payload):
        sig = Signal(self, verb='TCPCALLBACK', payload = payload)
        self.runsm.registerSignal(sig)


    # STATES ===========================================================================================================

    # SERIAL:SERIALINIT
    def sm_init(self, payload):
        pass
        logger.debug("Em Init State")

    # SERIAL:SERIALCONFIG
    def sm_config(self, payload):
        logger.debug("Serial config called")
        self.sendRawData(payload)

    # SERIAL:SERIALWRITE
    def sm_swrite(self, payload):
        logger.info("Serial write called")
        self.sendRawData(payload)

    # SERIAL:STARTBC
    def sm_enableBeacon(self, payload):
        if self.beacon_task is None :
            loop = self.runsm.getEventLoop()
            self.beacon_task = loop.create_task(self.SLoop())
            # logger.info("Beacon was enabled")
            self.sendCallback('Beacon was enabled.')


    # SERIAL:STOPBC
    def sm_disableBeacon(self, payload):
        if self.beacon_task is not None :
            self.beacon_task.cancel()
            self.beacon_task = None
            logger.info("Beacon stopped")
            self.sendCallback('Beacon was stopped.')

    # SERIAL:BCTICK
    def sm_setBeaconTick(self, payload):

        if self.beacon_task is not None :
            try :
                btick = float(payload[1])
            except Exception as e :
                self.sendCallback("Can't convert parameter due: {}".format(e.__repr__()))
                return
            self.beacon_tick = btick
            self.sendCallback('Beacon tick was set to {}'.format(btick))
        else:
            self.sendCallback("Can't do it -> Beacon is not enabled")

    # SERIAL:SENDBEACON
    def sm_sendBeacon(self, payload):

        s = self.payload.getBytes()
        self.sendRawData(s)
        # logger.info("Tick was sent...")
        self.sendCallback("Beacon was sent...")


    # SERIAL:SENDTICK
    def sm_sendTick(self, sm_payload : list):

        if len(sm_payload) == 1 :
            s = self.payload.getBytes(None, -1, '')
        else:
            sm_payload.pop(0)
            scmd = ':'.join(sm_payload)
            s = self.payload.getBytes(None, -2, scmd)

        self.sendRawData(s)
        self.sendCallback("TICK was sent...")

    # SERIAL:RUNT1
    def sm_runT1(self, sm_payload : list):

        if len(sm_payload) == 1 :
            s = self.payload.getBytes(None, -1, 'DUMMY1')
        else:
            sm_payload.pop(0)
            scmd = ':'.join(sm_payload)
            s = self.payload.getBytes(None, -2, scmd)

        self.sendRawData(s)
        self.sm_enableBeacon("")

        self.sendCallback("RunT1 was sent...")
