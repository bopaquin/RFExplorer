import serial
import threading


class RFEAnalyser(object):
    def __init__(self, port=None, baudrate=500000):
        self.hello = None
        self.mainboard_sn = None
        self.expansion_sn = None

        self._port_lock = threading.Lock()

        with self._port_lock:
            self._serial = serial.Serial()
            self._serial.port = port
            self._serial.baudrate = baudrate
            self._serial.bytesize = serial.EIGHTBITS
            self._serial.stopbits = serial.STOPBITS_ONE
            self._serial.Parity = serial.PARITY_NONE
            self._serial.timeout = 10

            self._serial.open()

        self.get_current_config()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        with self._port_lock:
            self._send_command('CH')
            self._serial.close()

    def __str__(self):
        return '\n'.join((
            self.hello,
            f'Mainboard S/N: {self.mainboard_sn}',
            f'Expansion S/N: {self.expansion_sn}'))

    def _send_command(self, command):
        self._serial.write(f'#{chr(len(command)+2)}{command}'.encode('utf8'))

    # @property
    # def serial_number(self):
    #     self._send_command('Cn')
    #     print(self._serial.readlines(16))
    #     return

    def get_current_config(self):
        with self._port_lock:
            self._send_command('C0')

            line = b''
            while line[0:2] != '#a'.encode('utf-8'):
                line = self._serial.readline()
                self._parse_line(line)

            self._send_command('CH')

    def _parse_line(self, line):
        # print(line)
        if b'\xff\xfe\xff\xfe\x00' in line:
            print('Last transmission was ended early')
            line = line[line.find(b'\xff\xfe\xff\xfe\x00') + 5:]
        # print('Parsing line')
        if chr(line[0]) == 'R':
            self.hello = line.decode('utf-8').strip()
            return
        if chr(line[0]) == 'D':
            print('DSP')
            return
        if chr(line[0]) == '#':
            self._parse_meta_data(line)
            return
        if chr(line[0]) == '$':
            print('Data')
            return

    def _parse_meta_data(self, line):
        # print('Parsing meta data')
        if line[:2].decode('utf-8') == '#a':
            self.input_stage = int(line[2:].decode('utf-8').strip())
            return
        if line[:3].decode('utf-8') == '#Sn':
            self.mainboard_sn = line[3:].decode('utf-8').strip()
            return
        if line[:3].decode('utf-8') == '#Se':
            self.expansion_sn = line[3:].decode('utf-8').strip()
            return
        if line[:4].decode('utf-8') == '#QA:':
            # I don't know
            return
        if line[:5].decode('utf-8') == '#CAL:':
            self.is_mainboard_calibration_available = bool(chr(line[4]))
            self.is_expansion_calibration_available = bool(chr(line[5]))
            return
        if line[:5].decode('utf-8') == '#BAT:':
            # Battery ???
            return
        if line[:6].decode('utf-8') == '#C2-M:':
            self.main_model, self.expansion_model, self.firmware = (
                line[6:].decode('utf-8').strip().split(','))
            self.main_model = int(self.main_model)
            self.expansion_model = int(self.expansion_model)
            return
        if line[:6].decode('utf-8') == '#C2-F:':
            (
                self.start_frequency,  # <Start_Freq>
                self.frequency_step,  # <Freq_Step>
                self.display_max,  # <Amp_Top>
                self.display_min,  # <Amp_Bottom>
                self.number_points,  # <Sweep_points>
                self.is_expansion_active,  # <ExpModuleActive>
                self.current_mode,  # <CurrentMode>
                self.min_frequency,  # <Min_Freq>
                self.max_frequency,  # <Max_Freq>
                self.max_span,  # <Max_Span>
                self.resolution_bandwidth,  # <RBW>
                self.manual_offset,  # <AmpOffset>
                self.calculator_mode,  # <CalculatorMode>
            ) = tuple(map(int, line[6:].decode('utf-8').strip().split(',')))
            self.is_expansion_active = bool(self.is_expansion_active)
            return
        if line[:6].decode('utf-8') == '#LFLO5':
            # I don't know
            return
        print(f'{line} not programmed (Meta Data Parser)')
