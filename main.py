import matplotlib.backend_bases
import pyvisa
import time
import logging
import sys
import os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from collections import OrderedDict
import threading
import pandas as pd

# Needed for GPIB interface -> only for requirements.txt
import psutil
import pyvisa_py
import zeroconf


# ToDO: Export Timeframe of values
# dev.write("DATA:ENCdg ASCII")
#a = dev.query_ascii_values('CURV?')
# b = [i/5.0 for i in a]
'''
dev.query("DATA:START?")
'1'
dev.query("DATA:STOP?")
'10000'
Anzahl return points

dev.write('DATa:ENCdg RIBINARY') #--32768 to 32767
dev.write('DATa:WIDth 2')
dev.query_binary_values('CURVE?', datatype='h', is_big_endian=True)

dev.query("WFMPre:XINcr?")
'4.0E-7'
Abtastrate
'''


class Storage:
    def __init__(self):
        self.col = ('time','values')
        self.values = pd.DataFrame(columns=self.col)
        self.limit = 100000
        self.init_time = time.time()
        self.limit = True
        self._ch1_scale = None
        self._incr = None
        self._graph_scale = None

    @property
    def ch1_scale(self):
        return self._ch1_scale

    @ch1_scale.setter
    def ch1_scale(self, value):
        self._ch1_scale = value

    @property
    def incr(self):
        return self._incr

    @incr.setter
    def incr(self, value):
        self._incr = value

    @property
    def graph_scale(self):
        return self._graph_scale

    @graph_scale.setter
    def graph_scale(self, value):
        self._graph_scale = value


    def read(self):
        return self.values

    def write(self, tme: time.time, v:list):
        try:
            v = [((val * 10) / 65535) * self.ch1_scale for val in v]
            t = [round(tme - (ts * self.incr) - self.init_time, 7) for ts in reversed(range(len(v)))]
            df = pd.DataFrame(data={self.col[0]:t, self.col[1]:v})
            df = df.query(f'{-self.graph_scale} < {self.col[1]} < {self.graph_scale}')
            self.values = pd.concat([self.values, df], ignore_index=True)
            self.values.reset_index(drop=True)
            if self.limit:
                self.values = self.values[-self.limit:]

        except:
            logging.error(f'{sys.exc_info()[1]}')
            logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')


    def limited(self,event):
        self.limit = not self.limit

    def reset(self, event):
        self.values = self.values.iloc[0:0]
        self.init_time = time.time()


class Device:
    def __init__(self, ip: str, ch1_scale: int):
        # Init Device
        self.ch1_scale = ch1_scale
        self.incr = None
        self.rm = pyvisa.ResourceManager('@py') #'@py'
        self.device = None
        self.graph = None
        self.limit = True
        assert len(ip) > 0
        self.ip = ip
        while self.device is None:
            try:
                self.device = self.rm.open_resource(f'TCPIP::{self.ip}::INSTR')
                self.set_device(self.device)

            except:
                time.sleep(1)
                self.device = None
                logging.error(f'{sys.exc_info()[1]}')
                logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')



    def set_device(self, dev: pyvisa.resources.resource):
        try:
            # Reset instrument
            dev.write("*rst; status:preset; *cls")
            # Set Immed Measurements source CH1
            dev.write('MEASUREMENT:IMMED:SOURCE CH1')
            # Turn off Gating
            dev.write('MEASUREMENT:IMMED:GATING OFF')
            # set measurement as mean over one cycle
            dev.write('MEASUREMENT:IMMED:TYPE CME')
            # Scale Meas Channel
            dev.write(f'CH1:SCALE {self.ch1_scale}')
            # set termination string
            dev.read_termination = '\n'
            dev.write("HORIZONTAL:MAIN:SCALE 1.0E-1")
            # get increments
            self.incr = float(dev.query("WFMPre:XINcr?"))
            # set Mode to RIBinary (Width 2 = signed int)
            dev.write('DATa:ENCdg RIBINARY')
            dev.write('DATa:WIDth 2')

        except pyvisa.errors.VisaIOError:
            logging.error(f'{sys.exc_info()[1]}')
            logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')
            dev.close()
            raise pyvisa.errors.VisaIOError




def animate(frame:int, graph_max:int, ax:matplotlib.pyplot.Axes, storage: Storage):
    try:
        # Get Data from Storage
        values = storage.read()

        # Update plot
        ax.cla()
        ax.set_xlabel("s")
        ax.set_ylabel("V", rotation=0)
        ax.set_ylim(-graph_max, graph_max)
        ax.grid()

        if len(values) > 0:
            ax.plot(values['time'], values['values'])


    except:
        logging.error(f'{sys.exc_info()[1]}')
        logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')


def pull_data(device:pyvisa.resources.resource, storage: Storage):
    while True:
        try:
            # Get Data
            values = device.query_binary_values('CURVE?','h', True)
            timestamp = time.time()
            storage.write(timestamp, values)

        except:
            logging.error(f'{sys.exc_info()[1]}')
            logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')


def init_logging():
  log_format = f"%(asctime)s [%(processName)s] [%(name)s] [%(levelname)s] %(message)s"
  logging.getLogger('pyvisa').disabled = True
  logging.getLogger('matplotlib.font_manager').disabled = True
  logging.getLogger('matplotlib.pyplot').disabled = True
  log_level = logging.DEBUG
  if getattr(sys, 'frozen', False):
    folder = os.path.dirname(sys.executable)
  else:
    folder = os.path.dirname(os.path.abspath(__file__))
  # noinspection PyArgumentList
  logging.basicConfig(
    format=log_format,
    level=log_level,
    force=True,
    handlers=[
      logging.FileHandler(filename=os.path.join(folder, 'debug.log'), mode='w', encoding='utf-8'),
      logging.StreamHandler(sys.stdout)
    ])




def main():
    init_logging()
    # Create Device
    ip = "192.168.178.3"
    graph_max = 11.0
    ch1_scale = 5
    interval = 100
    dev = Device(ip, ch1_scale)

    # Init figure
    fig = plt.figure(figsize=(12, 6), facecolor='#DEDEDE')
    ax = plt.subplot(111)
    ax.set_facecolor('#DEDEDE')


    # Data fetch Thread
    storage = Storage()
    storage.ch1_scale = ch1_scale
    storage.incr = dev.incr
    storage.graph_scale = graph_max
    thr_data = threading.Thread(target = pull_data, args = (dev.device,storage), daemon = True)
    thr_data.start()

    # Create Reset Button
    button_pos_reset = fig.add_axes([0.81, 0.9, 0.1, 0.075])
    button_reset = Button(button_pos_reset, 'Reset')
    button_reset.on_clicked(storage.reset)

    # Create Limit Button
    button_pos_limit = fig.add_axes([0.71, 0.9, 0.1, 0.075])
    button_limit = Button(button_pos_limit, 'Limit')
    button_limit.on_clicked(storage.limited)

    ani = FuncAnimation(fig, animate, interval=interval, fargs=(graph_max,ax,storage), cache_frame_data=False)
    plt.show()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

