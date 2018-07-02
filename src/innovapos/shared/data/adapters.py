import logging

import socket
import uuid
from _thread import start_new_thread
from time import sleep
from typing import Callable, Any

import pika
import serial
from pika.adapters.blocking_connection import BlockingChannel
from pika.channel import Channel

from innovapos.shared.data import utils
from innovapos.shared.data.abstractions import BaseDataAdapterParameters, AbstractDataAdapter


class TCPDataAdapterParameters(BaseDataAdapterParameters):
    def __init__(self, hostname: str, port: int, send_end_char: str = None, recv_end_char: str = None,
                 timeout: float = None, answer_delay: float = None):
        """
        TCPDataAdapter parameters needed for opening connections

        :param hostname: hostname or ip
        :type hostname: str
        :param port: port for connection
        :type port: int
        :param send_end_char: character with which each sending message is finalized. Defaults to "\\n" 
        :type send_end_char: str
        :param recv_end_char: character with which each received message is finalized. Defaults to "\\n" 
        :type recv_end_char: str
        :param timeout: connection timeout in seconds. Defaults to 1
        :type timeout: float
        :param answer_delay: seconds to wait before reading answer
        :type answer_delay: float
        """
        super().__init__(send_end_char, recv_end_char, timeout, answer_delay)
        self.hostname = hostname
        self.port = port


class TCPDataAdapter(AbstractDataAdapter):
    def __init__(self, parameters: TCPDataAdapterParameters):
        """
        TCPDataAdapter constructor
        
        :param parameters: TCPDataAdapterParameters object that is used for the configuration of the data adapter
        :type parameters: TCPDataAdapterParameters
        """
        self.parameters = parameters
        self.read_stop_byte = str.encode(self.parameters.recv_msg_end)
        self.sock: socket.socket = None
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Adapter instantiated")
        self.incoming_msg_handler: Callable[[Any, str], str] = None
        self._is_opened_ = False

    def open(self) -> None:
        """
        Initializes a new connection

        :return: None
        :rtype: None
        """
       # self.EjecuteEmulator()
        self.logger.debug("Opening connection")
        if not self.parameters:
            raise TypeError("params object was not provided")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f'Estableciendo conexion con: {self.parameters.hostname}:{self.parameters.port}')
        self.sock.connect((self.parameters.hostname, self.parameters.port))
        self.sock.settimeout(self.parameters.timeout)
        self.logger.debug("Connection opened")
        self._is_opened_ = True



    def bind_and_setup_listening(self):
        """
        Binds the passed port for new connections
        
        :return: None
        :rtype: None
        """

        self.logger.debug("Binding port")
        if not self.parameters:
            raise TypeError("parameters were not provided for adapter")
        print('HMS : Binding port 3001')

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f'Hostname ==> {self.parameters.hostname}')
        print(f'Port ==> {self.parameters.port}')
        print(f'Time ==> {self.parameters.timeout}')
        print(f'socket.AF_INET ==> {socket.AF_INET}')
        print(f'socket.SOCK_STREAM ==> {socket.SOCK_STREAM}')

        self.sock.bind((self.parameters.hostname, self.parameters.port))
        self.sock.settimeout(self.parameters.timeout)
        print('Port binding done')
        self.logger.debug(f"Port binding done {self.parameters.hostname}:{self.parameters.port}")
        self.sock.listen()
        self._is_opened_ = True
        start_new_thread(self.accept_new_connections_loop, ())
        self.logger.debug("Port bound and listener started")

    def set_message_handler(self, handler: Callable[[Any, str], str]):
        """
        Sets the handler function for messages received on the listened port
        
        :param handler: handler function for incoming messages on bound port. only required if you will be \
            listening on that specific port in order to be able to notify whoever it may interest. 
            
            The handler function may return a value. That value will be used to reply to the received message. \
            If the returned value is None, no message will be sent
        :type handler: Callable[[Any, str], str]
        :return: 
        :rtype: 
        """
        self.incoming_msg_handler = handler

    def send_message(self, message: str):
        self.logger.debug(f"Sending message '{message}'")
        self.sock.send(str.encode(f'{message}{self.parameters.send_msg_end}'))

    def receive_message_with_stop_byte(self) -> str:
        """
        Reads a message from the TCP stream until it encounters the stop byte
        :return: read message 
        :rtype: str
        """
        self.logger.debug(f"Starting to read reply")
        reply = self.__read_until_stop_byte_or_timeout__(self.sock)
        self.logger.debug(f"Reply length - {len(reply)}. Reply - '{reply}'")
        return reply

    def transact_message(self, message: str) -> str:
        """
        Sends a message and receives an answer until stopbyte is received
        :param message: message to send
        :type message: str
        :return: received answer
        :rtype: str
        """
        self.logger.debug(f"Transacting message {message}")
        self.send_message(message)
        sleep(self.parameters.answer_delay)
        reply = self.receive_message_with_stop_byte()
        return reply

    def accept_new_connections_loop(self):
        print('Nueva Conexion TCP')
        while self._is_opened_:
            try:
                conn, address = self.sock.accept()
                self.logger.debug(f"Accepted a new connection on. Starting handler thread")
                start_new_thread(self.handle_client_messages_loop, (conn, address))
            except  Exception:
                pass


    def handle_client_messages_loop(self, connection, address):
        print('client handler loop entered')
        while self._is_opened_:
            #print('Lectura puerto 3001')
            try:

                result = self.__read_until_stop_byte_or_timeout__(connection)
                #print('================')
                #print('================')
                #print(f'HMS: result ==>{result}>>> incoming_msg_handler==>{self.incoming_msg_handler}')
                if result and self.incoming_msg_handler is not None:
                    #print(f'HMS :antes => {result}')
                    result = result.replace('\r', '')
                    #print(f'HMS : Despues =>{result}')
                    self.logger.debug(f"New message on binded port {address} -> {str(result)} ")
                    reply_to_send = ''
                    try:
                        reply_to_send = self.incoming_msg_handler(result)
                    except Exception as e:
                        self.logger.exception(e)

                    if reply_to_send:
                        self.logger.debug(f"Callback returned {reply_to_send}. Replying")
                        connection.send(str.encode(reply_to_send))
                else:
                    sleep(0.5)
            except Exception as e:
                print(f'HMS:  estado conexion: {self._is_opened_}')
                print(e)


    def close(self) -> None:
        self._is_opened_ = False
        if self.sock is not None:
            self.sock.close()
        self.sock = None

    def __read_until_stop_byte_or_timeout__(self, connection: socket.socket) -> str:
        """
        Reads the TCP stream until the end char is met
        :return: full response
        :rtype: str
        """
        result: str = ""
        while True:
            try:

                #print(f'HMS: read_stop_byte ==> {self.read_stop_byte}')
                current_char = connection.recv(1)
                if current_char == self.read_stop_byte:
                    #print(f'HMS-er: 003 {current_char}-{self.read_stop_byte}')
                    break
                #print(f'HMS-er: 004 {current_char}')
                result += bytes.decode(current_char)
            except TimeoutError:
                print('HMS-er: 001 TimeoutError ')
                break
            except OSError:
                print('HMS-er: 002 OSError ')
                break
        return result


class SerialDataAdapterParameters(BaseDataAdapterParameters):
    def __init__(self, serial_port: str, send_end_char: str = None, recv_end_char: str = None,
                 timeout: float = None, answer_delay: float = None):
        """
        SerialDataAdapter parameters needed for opening connections
    
        :param hostname: hostname or ip
        :type hostname: str
        :param port: port for connection
        :type port: int
        :param send_end_char: character with which each sending message is finalized. Defaults to "\\n" 
        :type send_end_char: str
        :param recv_end_char: character with which each received message is finalized. Defaults to "\\n" 
        :type recv_end_char: str
        :param timeout: connection timeout in seconds. Defaults to 1
        :type timeout: float
        :param answer_delay: seconds to wait before reading answer
        :type answer_delay: float
        """
        super().__init__(send_end_char, recv_end_char, timeout, answer_delay)
        self.serial_port = serial_port

#TODO: comentado para windows
'''
class SerialDataAdapter(AbstractDataAdapter):
    import serial
    serial_port:serial.Serial

    """Fixed connection parameters"""
    __baudrate__: int = 96000
    __bytesize__: int = serial.EIGHTBITS
    __parity__: str = serial.PARITY_NONE
    __stopbits__: int = serial.STOPBITS_ONE

    def __init__(self, parameters: SerialDataAdapterParameters):
        """
        SerialDataAdapter constructor
        
        :param parameters: parameters for SerialDataAdapter 
        :type parameters: SerialDataAdapterParameters
        """
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Instantiating adapter")
        self.parameters = parameters
        self.read_stop_byte = str.encode(self.parameters.send_msg_end)
        self.serial_port = serial.Serial()
        self.serial_port.port = self.parameters.serial_port
        self.serial_port.baudrate = self.__baudrate__
        self.serial_port.bytesize = self.__bytesize__
        self.serial_port.parity = self.__parity__
        self.serial_port.stopbits = self.__stopbits__
        self.serial_port.timeout = self.parameters.timeout
        self.message_callback: function = None
        self.logger.debug("Adapter instantiated")

    def open(self) -> None:
        """
        Initializes a new connection to the target
        """
        if not self.parameters:
            raise TypeError("serial data adapter object was not passed")
        self.serial_port.open()
        self.logger.debug("Serial port initialized")

    def bind_and_setup_listening(self) -> None:
        """
        Binds the port for new connections
         
        :return: 
        :rtype: 
        """
        if not self.parameters:
            raise TypeError("serial data adapter object was not passed")
        self.logger.debug(f"Opening serial port on {self.parameters.serial_port}")
        if self.serial_port is not None:
            self.close()
        self.serial_port = serial.Serial(self.parameters.serial_port, self.__baudrate__, self.__bytesize__,
                                         self.__parity__, self.__stopbits__, self.parameters.timeout)
        self.serial_port.open()
        start_new_thread(self.handle_client_messages_loop, ())
        self.logger.debug("Serial port initialized")

    def set_message_handler(self, handler: Callable[[Any, str], str]):
        """
        Sets the callback function for messages received on the listened port

        :param handler: callback function for incoming messages on bound port. only required if you will be \
            listening on that specific port in order to be able to notify whoever it may interest. 
            
            The callback function may return a value. That value will be used to reply to the received message. \
            If the returned value is None, no message will be sent
        :type handler: Callable[[Any, str], str] 
        :return: None
        :rtype: None
        """
        self.message_callback = handler

    def send_message(self, message: str):
        self.logger.debug(f"Sending message '{message}{self.parameters.send_msg_end}'")
        self.serial_port.write(str.encode(f'{message}{self.parameters.send_msg_end}'))

    def receive_message_with_stop_byte(self) -> str:
        """
        Reads a message from the TCP stream until it encounters the stop byte
        :return: read message 
        :rtype: str
        """
        self.logger.debug(f"Starting to read reply")
        reply = self.__read_until_stop_byte_or_timeout__()
        self.logger.debug(f"Reply length - {str(reply)}. Reply - '{reply}'")
        return reply

    def transact_message(self, message: str) -> str:
        """
        Sends a message and receives an answer until stopbyte is received
        :param message: message to send
        :type message: str
        :return: received answer
        :rtype: str
        """
        self.send_message(message)
        sleep(self.parameters.answer_delay)
        reply = self.receive_message_with_stop_byte()
        return reply

    def handle_client_messages_loop(self, args):
        while True:
            result = self.__read_until_stop_byte_or_timeout__()

            if result and self.message_callback is not None:
                self.logger.debug(f"Received new message, calling handler. ")
                reply_to_send = self.message_callback(result)
                if reply_to_send:
                    self.serial_port.send(str.encode(reply_to_send))

    def close(self) -> None:
        self.serial_port.close()
        self.serial_port = None

    def __read_until_stop_byte_or_timeout__(self) -> str:
        """
        Reads the TCP stream until the end char is met
        :return: full response
        :rtype: str
        """
        result: str = ""
        while True:
            try:
                current_char = self.serial_port.read(1)
                if current_char == self.read_stop_byte:
                    break
                result += bytes.decode(current_char)
            except TimeoutError:
                break
        return result
    
    '''

