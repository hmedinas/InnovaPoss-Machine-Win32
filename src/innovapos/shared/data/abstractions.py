from abc import ABC, abstractmethod
from typing import Callable, Any


class BaseDataAdapterParameters:
    def __init__(self, send_end_char: str = None, recv_end_char: str = None,
                 timeout: float = None, answer_delay: float = None):
        """
        AbstractDataAdapter parameters
        
        :param send_end_char: character with which each sending message is finalized. Defaults to "\n" 
        :type send_end_char: str
        :param recv_end_char: character with which each received message is finalized. Defaults to "\n" 
        :type recv_end_char: str
        :param timeout: connection timeout in seconds. Defaults to 1
        :type timeout: float
        :param answer_delay: seconds to wait before reading answer
        :type answer_delay: float 
        """
        self.send_msg_end = send_end_char if send_end_char else '\n'
        self.recv_msg_end = recv_end_char if recv_end_char else '\n'
        self.timeout = timeout if timeout else 1
        self.answer_delay = answer_delay if answer_delay else 0


class AbstractDataAdapter(ABC):
    parameters: BaseDataAdapterParameters

    @abstractmethod
    def open(self) -> None:
        """
        Abstract opening of a connection.

        :param params: adapter specific parameters
        :type params: object
        :return: None
        :rtype: None
        """
        pass

    @abstractmethod
    def bind_and_setup_listening(self) -> None:
        """
        Abstract binding of a port for incoming connections
        
        :return: None
        :rtype: None
        """
        pass

    @abstractmethod
    def set_message_handler(self, handler: Callable[[Any, str], str]):
        """
        Handler function to call when a message is received on the listening port
        
        :param handler: handler function to be called
        :type handler: function 
        :return: 
        :rtype: 
        """

    @abstractmethod
    def send_message(self, message: str):
        """
        Abstract method. Sends a message without waiting for replies
        :param message: message to send
        :type message: 
        :return: 
        :rtype: 
        """
        pass

    @abstractmethod
    def receive_message_with_stop_byte(self) -> str:
        """
        Abstract message receival
        :param message: 
        :type message: 
        :return: 
        :rtype: 
        """
        pass

    @abstractmethod
    def transact_message(self, message: str) -> str:
        """
        Abstract method. Sends a message and receives an answer
        :param message: message to send
        :type message: str
        :return: received answer
        :rtype: str
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Abstract closing of a connection
        :return: 
        :rtype: 
        """
        pass

