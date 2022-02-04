# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame
from collections import namedtuple
from typing import List

CommandMetadata = namedtuple('CommandMetadata', ['id', 'name', 'command_details_generator', 'data_details_generator'])

DIGITAL_BUTTONS = ['Select', 'L3', 'R3', 'Start', 'D-Up', 'D-Right', 'D-Down', 'D-Left', 'L2', 'R2', 'L1', 'R1', '🔺', '⚪', '✖', '⬛']

def command_empty_details(*args):
    return ''

def data_empty_details(*args):
    return '(...)'

def cmd42_command_details(command_bytes: List[int], data_bytes: List[int]):
    # Determine motor mapping status
    if command_bytes[3] or command_bytes[4]:
        small_motor_mapping = command_bytes[3]
        large_motor_mapping = command_bytes[4]
        return 'Small Motor %s, Large Motor %s' % (small_motor_mapping == 0xFF, large_motor_mapping >= 0x40)

    return ''

def cmd42_data_details(command_bytes: List[int], data_bytes: List[int]):
    # Determine digital buttons
    digital_buttons = []

    for bi, button_name in enumerate(DIGITAL_BUTTONS):
        if bi < 8:
            byte_number = 3
        else:
            byte_number = 4

        bit_number = bi % 8
        digital_byte = data_bytes[byte_number]
        
        if digital_byte & (1 << bit_number) == 0:
            digital_buttons.append(button_name)

    if len(digital_buttons):
        return ', '.join(digital_buttons)
    else:
        return '(no buttons)'

def cmd43_command_details(command_bytes: List[int], data_bytes: List[int]):
    return 'Enter' if command_bytes[3] == 0x01 else 'Exit'

def cmd43_data_details(command_bytes: List[int], data_bytes: List[int]):
    # In config mode, no button data is provided
    if data_bytes[1] == 0xF3:
        return '(no data)'

    return cmd42_data_details(command_bytes, data_bytes)

def cmd44_command_details(command_bytes: List[int], data_bytes: List[int]):
    is_analog = command_bytes[3] == 0x01
    is_locked = command_bytes[4] == 0x03
    
    mode_string = 'Analog' if is_analog else 'Digital'
    locked_string = ' (Locked)' if is_locked else ''
    return 'Set ' + mode_string + locked_string

def cmd46_command_details(command_bytes: List[int], data_bytes: List[int]):
    offset = command_bytes[3]

    if offset == 0:
        return 'First Byte'
    elif offset == 1:
        return 'Second Byte'
    else:
        return 'Unknown Byte'

def cmd4c_command_details(command_bytes: List[int], data_bytes: List[int]):
    return cmd46_command_details(command_bytes, data_bytes)

def cmd4d_command_details(command_bytes: List[int], data_bytes: List[int]):
    small_mapping = command_bytes[3]
    large_mapping = command_bytes[4]

    details = []
    details.append(('Map' if small_mapping == 0x00 else 'Unmap') + ' Small')
    details.append(('Map' if large_mapping == 0x01 else 'Unmap') + ' Large')
    return ', '.join(details)

COMMAND_METADATA = {
    0x40: CommandMetadata(0x40, 'Initialize Pressure Sensors', command_empty_details, data_empty_details),
    0x41: CommandMetadata(0x41, 'Button Inclusions',           command_empty_details, data_empty_details),
    0x42: CommandMetadata(0x42, 'Main Polling',                cmd42_command_details, cmd42_data_details),
    0x43: CommandMetadata(0x43, 'Enter/Exit Config Mode',      cmd43_command_details, cmd43_data_details),
    0x44: CommandMetadata(0x44, 'Switch Analog/Digital Mode',  cmd44_command_details, data_empty_details),
    0x45: CommandMetadata(0x45, 'Get Status Info',             command_empty_details, data_empty_details),
    0x46: CommandMetadata(0x46, 'Device Descriptor',           cmd46_command_details, data_empty_details),
    0x47: CommandMetadata(0x47, 'Device Descriptor',           command_empty_details, data_empty_details),
    0x4C: CommandMetadata(0x4C, 'Device Descriptor',           cmd4c_command_details, data_empty_details),
    0x4D: CommandMetadata(0x4D, 'Map Rumble Motors',           cmd4d_command_details, data_empty_details),
    0x4F: CommandMetadata(0x4F, 'Configure Analog Response',   command_empty_details, data_empty_details),
}

MODE_NAMES = {
    0x41: 'Digital',
    0x73: 'Analog',
    0x79: 'Analog with Pressure',
    0xF3: 'Configuration',
}

# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):
    result_types = {
        'valid-command': {
            'format': '🎮 Controller Mode: {{data.mode_string}} ({{data.mode_id}}) — ⬇ Command: {{data.command_name}} ({{data.command_id}}) {{data.command_details}} — ⬆ Data: {{data.data_details}}'
        }
    }

    def __init__(self):
        self.reset()

    def reset(self):
        self.current_frame_type = None
        self.current_frame_start_time = None
        self.current_frame_command_id = None
        self.current_controller_mode = None
        self.current_frame_command_bytes = []
        self.current_frame_data_bytes = []
        self.current_frame_index = 0

    def decode(self, frame: AnalyzerFrame):
        if frame.type == 'enable':
            self.reset()
            self.current_frame_start_time = frame.start_time
            self.current_frame_index = 0
        elif frame.type == 'result':
            command = int.from_bytes(frame.data['mosi'], 'big')
            data = int.from_bytes(frame.data['miso'], 'big')

            if self.current_frame_index == 0 and command != 0x01:
                self.current_frame_type = 'invalid-packet'
            elif self.current_frame_index == 1:
                self.current_frame_command_id = command
                self.current_controller_mode = data

                if command not in COMMAND_METADATA:
                    self.current_frame_type = 'invalid-command'
                else:
                    self.current_frame_type = 'valid-command'
            
            self.current_frame_command_bytes.append(command)
            self.current_frame_data_bytes.append(data)
            self.current_frame_index += 1
        elif frame.type == 'disable':
            if self.current_frame_start_time and self.current_frame_type == 'valid-command':
                command_metadata = COMMAND_METADATA[self.current_frame_command_id]

                try:
                    command_details = command_metadata.command_details_generator(self.current_frame_command_bytes, self.current_frame_data_bytes)
                except:
                    command_details = '(error)'

                try:
                    data_details = command_metadata.data_details_generator(self.current_frame_command_bytes, self.current_frame_data_bytes)
                except:
                    data_details = '(error)'

                return AnalyzerFrame(self.current_frame_type, self.current_frame_start_time, frame.end_time, {
                    'mode_string': MODE_NAMES.get(self.current_controller_mode, 'Unknown Mode'),
                    'mode_id': ('%02X' % self.current_controller_mode),
                    'command_name': command_metadata.name,
                    'command_id': ('%02X' % command_metadata.id),
                    'command_details': (' - ' + command_details) if command_details else '',
                    'data_details': data_details or ''
                })

        return None
