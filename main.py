import pyvisa
import time
import logging
import sys
import os
import math
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
# Needed for GPIB interface
import psutil
import pyvisa_py
import zeroconf

cmd_error = {
    100 : "Command error",
    101 : "Invalid character",
    102 : "Syntax error",
    103 : "Invalid separator",
    104 : "Data type error",
    105 : "GET not allowed",
    106 : "Invalid program data separator",
    108 : "Parameter not allowed",
    109 : "Missing parameter",
    110 : "Command header error",
    111 : "Header separator error",
    112 : "Program mnemonic too long",
    113 : "Undefined header",
    118 : "Query not allowed",
    120 : "Numeric data error",
    121 : "Invalid character in number",
    123 : "Exponent too large",
    124 : "Too many digits",
    128 : "Numeric data not allowed",
    130 : "Suffix error",
    131 : "Invalid suffix",
    134 : "Suffix too long",
    138 : "Suffix not allowed",
    140 : "Character data error",
    141 : "Invalid character data",
    144 : "Character data too long",
    148 : "Character data not allowed",
    150 : "String data error",
    151 : "Invalid string data",
    152 : "String data too long",
    158 : "String data not allowed",
    160 : "Block data error",
    161 : "Invalid block data",
    168 : "Block data not allowed",
    170 : "Expression error",
    171 : "Invalid expression",
    178 : "Expression data not allowed",
    180 : "Alias error",
    181 : "Invalid outside alias definition",
    183 : "Invalid inside alias definition",
    184 : "Command in alias requires more/fewer parameters",
    200 : "Execution error",
    201 : "Invalid while in local",
    202 : "Settings lost due to rtl",
    210 : "Trigger error",
    211 : "Trigger ignored",
    212 : "Arm ignored",
    220 : "Parameter error",
    221 : "Settings conflict",
    222 : "Data out of range",
    223 : "Too much data",
    224 : "Illegal parameter value",
    230 : "Data corrupt or stale",
    240 : "Hardware error",
    241 : "Hardware missing",
    242 : "Hardware configuration error",
    243 : "Hardware I/O device error",
    250 : "Mass storage error",
    251 : "Missing mass storage",
    252 : "Missing media",
    253 : "Corrupt media",
    254 : "Media full",
    255 : "Directory full",
    256 : "File name not found",
    257 : "File name error",
    258 : "Media protected",
    260 : "Expression error",
    261 : "Math error in expression",
    270 : "Hard copy error",
    271 : "Hard copy device not responding",
    272 : "Hard copy is busy",
    273 : "Hard copy is aborted",
    274 : "Hard copy configuration error",
    280 : "Network printer name not found",
    281 : "Network printer list full",
    282 : "Insufficient network printer information",
    283 : "Network printer not responding",
    284 : "Network printer server not responding",
    285 : "Network printer domain name server not responding",
    286 : "No network printers exist",
    287 : "Print server not found",
    2200 : "Measurement error, Measurement system error",
    2201 : "Measurement error, Zero period",
    2202 : "Measurement error, No period found",
    2203 : "Measurement error, No period, second waveform",
    2204 : "Measurement error, Low signal amplitude",
    2205 : "Measurement error, Low amplitude, second waveform",
    2206 : "Measurement error, Invalid gate",
    2207 : "Measurement error, Measurement overflow",
    2208 : "Measurement error, Waveform does not cross Mid Ref",
    2209 : "Measurement error, No second Mid Ref crossing",
    2210 : "Measurement error, No Mid Ref crossing, second waveform",
    2211 : "Measurement error, No backwards Mid Ref crossing",
    2212 : "Measurement error, No negative crossing",
    2213 : "Measurement error, No positive crossing",
    2214 : "Measurement error, No crossing",
    2215 : "Measurement error, No crossing, second waveform",
    2216 : "Measurement error, No crossing, target waveform",
    2217 : "Measurement error, Constant waveform",
    2218 : "Measurement error, Unused",
    2219 : "Measurement error, No valid edge -- No arm sample",
    2220 : "Measurement error, No valid edge -- No arm cross",
    2221 : "Measurement error, No valid edge -- No trigger cross",
    2222 : "Measurement error, No valid edge -- No second cross",
    2223 : "Measurement error, Waveform mismatch",
    2224 : "Measurement error, WAIT calculating",
    2225 : "Measurement error, No waveform to measure",
    2226 : "Null Waveform",
    2227 : "Positive and Negative Clipping",
    2228 : "Measurement error, Positive Clipping",
    2229 : "Measurement error, Negative Clipping",
    2230 : "Measurement error, High Ref < Low Ref",
    2231 : "Measurement error, Measurement is not turned on",
    2232 : "Measurement error, Frequency out of range",
    2235 : "Math error, Invalid math description",
    2240 : "Invalid password",
    2241 : "Waveform requested is invalid",
    2242 : "Data start and stop > record length",
    2243 : "Waveform requested is not a data source",
    2244 : "Waveform requested is not turned on",
    2245 : "Saveref error, Selected channel is turned off",
    2246 : "Saveref error, Selected channel data invalid",
    2248 : "Saveref error, Source reference data invalid",
    2260 : "Calibration error",
    2270 : "Alias error",
    2271 : "Alias syntax error",
    2272 : "Alias execution error",
    2273 : "Illegal alias label",
    2274 : "Alias parameter error",
    2275 : "Alias definition too long",
    2276 : "Alias expansion error",
    2277 : "Alias redefinition not allowed",
    2278 : "Alias header not found",
    2279 : "Alias label too long",
    2280 : "Alias table full",
    2285 : "TekSecure Pass",
    2286 : "TekSecure Fail",
    2301 : "Cursor error, Off-screen",
    2302 : "Cursor error, cursors are off",
    2303 : "Cursor error, Cursor source waveform is off"
}

class Device:
    def __init__(self):
        # Init Device
        self.rm = pyvisa.ResourceManager('@py')
        self.device = None
        self.data = {}
        self.graph = None
        self.time_init = time.time()
        self.timestamp = 0
        self.value = 0
        while self.device is None:
            try:
                self.device = self.rm.open_resource('TCPIP::192.168.178.3::INSTR')
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
            self.value, state = self.device.query('MEASUrement:IMMed:DATa?').split(',')
            self.timestamp = math.trunc((time.time() - self.time_init) * 1000)
            if int(state) not in cmd_error.keys():
                self.data[self.timestamp] = float(self.value)

            # Update plot
            self.graph: plt.Subplot
            self.graph.cla()
            self.graph.set_xlabel("ms")
            self.graph.set_ylabel("V")
            self.graph.set_ylim(-10, 10)
            lists = sorted(self.data.items())
            x,y = zip(*lists)
            self.graph.plot(x,y)

        except:
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
            dev.write('CH1:SCALE 10.0')
            # set termination string
            dev.read_termination = '\n'
            # Return all parameters for Meas
            logging.info(dev.query('MEASUrement:IMMed?'))

        except pyvisa.errors.VisaIOError:
            logging.error(f'{sys.exc_info()[1]}')
            logging.error(f'Error on line {sys.exc_info()[-1].tb_lineno}')
            dev.close()



def init_logging():
  log_format = f"%(asctime)s [%(processName)s] [%(name)s] [%(levelname)s] %(message)s"
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
    dev = Device()

    # Init figure
    fig = plt.figure(figsize=(12, 6), facecolor='#DEDEDE')
    ax = plt.subplot(111)
    ax.set_facecolor('#DEDEDE')
    dev.set_plot(ax)

    ani = FuncAnimation(fig, dev.measurement, interval=10)
    plt.show()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

