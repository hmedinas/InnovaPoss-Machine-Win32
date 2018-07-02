from time import sleep

import serial


class SimpleSerial():
    import serial
    serial_port: serial.Serial

    """Fixed connection parameters"""
    __baudrate__: int = 96000
    __bytesize__: int = serial.EIGHTBITS
    __parity__: str = serial.PARITY_NONE
    __stopbits__: int = serial.STOPBITS_ONE

    def __init__(self):
        """
        SerialDataAdapter constructor

        :param parameters: parameters for SerialDataAdapter 
        :type parameters: SerialDataAdapterParameters
        """

        self.serial_port = serial.Serial()
        self.serial_port.port = '/dev/tty.usbserial'
        self.serial_port.baudrate = self.__baudrate__
        self.serial_port.bytesize = self.__bytesize__
        self.serial_port.parity = self.__parity__
        self.serial_port.stopbits = self.__stopbits__
        self.serial_port.timeout = 3

ser = SimpleSerial()
ser.serial_port.open()
print("port open")
ser.serial_port.write(b"CCM_GetStatus\n")
print("written. waiting")
sleep(3)
reply = ser.serial_port.read_all()
print(f"got reply? {reply}")