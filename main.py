import matplotlib.backend_bases
import pyvisa
import time
import logging
import sys
import os
import math
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from collections import OrderedDict

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

class Device:
    def __init__(self, ip: str, graph_scale: float, ch1_scale: int):
        # Init Device
        self.rm = pyvisa.ResourceManager() #'@py'
        self.device = None
        self.data = {}
        self.graph = None
        self.limit = True
        assert len(ip) > 0
        self.ip = ip
        self.ch1_scale = ch1_scale
        self.graph_scale = graph_scale
        self.time_init = time.time()
        self.timestamp = None
        self.incr = None
        self.values = None
        self.dictValues = OrderedDict()
        while self.device is None:
            try:
                self.device = self.rm.open_resource(f'TCPIP::{self.ip}::INSTR')
                self.set_device(self.device)

            except:
                time.sleep(1)
                self.device = None
                logging.error(f'{sys.exc_info()[1]}')
                logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')



    def set_plot(self, graph: plt.subplot):
        self.graph = graph

    def measurement(self, interval):
        try:
            # Get Data
            self.values = self.device.query_binary_values('CURVE?','h', True)
            timestamp = time.time()
            cnt = len(self.values)
            if self.limit and len(self.dictValues) + cnt > 100000:
                for i in range(10000):
                    self.dictValues.popitem(last=False)
            meas = {round(timestamp - ((cnt-enum)*self.incr) - self.time_init,7) : ((val*10)/65535) * self.ch1_scale for enum, val in enumerate(self.values) if -self.graph_scale <= ((val*10)/65535) * self.ch1_scale <= self.graph_scale}
            self.dictValues.update(meas)
            self.dictValues = OrderedDict(sorted(self.dictValues.items()))
            # Update plot
            self.graph: plt.Subplot
            self.graph.cla()
            self.graph.set_xlabel("s")
            self.graph.set_ylabel("V", rotation=0)
            self.graph.set_ylim(-self.graph_scale, self.graph_scale)
            if len(self.dictValues) > 0:
                self.graph.plot(self.dictValues.keys(),self.dictValues.values())
                self.graph.grid()

        except:
            logging.error(f'{sys.exc_info()[1]}')
            logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')

    def limited(self,event):
        self.limit = not self.limit

    def reset(self, event):
        self.dictValues.clear()
        self.time_init = time.time()


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
            # set Mode to RIBinary (Width 2 = signed int)
            dev.write('DATa:ENCdg RIBINARY')
            dev.write('DATa:WIDth 2')
            dev.write("HORIZONTAL:MAIN:SCALE 1.0E-1")
            # get increments
            self.incr = float(dev.query("WFMPre:XINcr?"))
            # Return all parameters for Meas
            logging.info(f'Starting with device settings: {dev.query("MEASUrement:IMMed?")}')

        except pyvisa.errors.VisaIOError:
            logging.error(f'{sys.exc_info()[1]}')
            logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')
            dev.close()



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
    dev = Device(ip, graph_max, ch1_scale)

    # Init figure
    fig = plt.figure(figsize=(12, 6), facecolor='#DEDEDE')
    ax = plt.subplot(111)
    ax.set_facecolor('#DEDEDE')
    dev.set_plot(ax)

    # Create Reset Button
    button_pos_reset = fig.add_axes([0.81, 0.9, 0.1, 0.075])
    button_reset = Button(button_pos_reset, 'Reset')
    button_reset.on_clicked(dev.reset)

    # Create Limit Button
    button_pos_limit = fig.add_axes([0.71, 0.9, 0.1, 0.075])
    button_limit = Button(button_pos_limit, 'Limit')
    button_limit.on_clicked(dev.limited)


    ani = FuncAnimation(fig, dev.measurement, interval=interval)
    plt.show()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

