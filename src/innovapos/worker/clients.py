import logging
import threading
import time
from typing import Callable, Any
from uuid import uuid4
import sys
import psutil
import subprocess
import pika
import psutil
from pika.adapters.blocking_connection import BlockingChannel
from pika.channel import Channel

from innovapos.shared.data.abstractions import AbstractDataAdapter
from innovapos.shared.data.adapters import TCPDataAdapter
import os

hw_lock = threading.Lock()



def reconnect_on_broken_pipe(fn):
    def wrapper(self, *args, **kwargs):
        max_retries: int = 3
        retry = 0
        while retry < max_retries:
            try:
                return fn(self, *args, **kwargs)
            except BrokenPipeError as e:
                logging.info(
                    f"BrokenPipeError during message transaction {repr(e)}. Retrying... ({retry}/{max_retries})")

            self.close_connections()
            time.sleep(1)  # wait 1 seconds before reopening ports
            self.open_connections()
            retry = retry + 1

    return wrapper


class HardwareClient:
    def __init__(self, ccm_adapter: AbstractDataAdapter, mon_adapter: AbstractDataAdapter):
        #self.startProcess()
        #time.sleep(2)
        """
        HardwareClient acts as the connection bridge between the 

        :param ccm_adapter: communication adapter for CCM
        :type ccm_adapter: AbstractDataAdapter
        :param mon_adapter: communication adapter for Monedero
        :type mon_adapter: AbstractDataAdapter
        """
        self.logger = logging.getLogger(__name__)
        self.logger.debug("HardwareClient instantiated")
        self.ccm_adapter = ccm_adapter
        self.mon_adapter = mon_adapter
        self.__monedero_handler__: Callable[[Any, str], str] = None

    @staticmethod
    def shared_hw_lock():
        def wrapper(fn):
            with hw_lock:
                return fn

        return wrapper
    #iniciando procesos
    def startProcessSeg(self):
        pathSockmon = f'/home/pi/AppInnova/Eject/Sockmon'
        print('HMS: Ejecutando Sockmon')
        statusSockmon = subprocess.Popen([pathSockmon])
    def startProcess(self):

        time.sleep(0.5)
        os.system("fuser -k 3000/tcp")
        os.system("fuser -k 3001/tcp")

        for i in psutil.pids():
            process = psutil.Process(i)
            if process.name() == '3001':
                process.kill()
            if process.name() == 'CCM':
                process.kill()
            if process.name() == 'Sockmon':
                process.kill()
            if process.name() == 'Sockserver':
                process.kill()


                # EJECUTAMOS LOS PROCESOS
        time.sleep(2)
        path3001 = f'/home/pi/AppInnova/Eject/3001'
        pathCCM = f'/home/pi/AppInnova/Eject/CCM'
        pathSockserver = f'/home/pi/AppInnova/Eject/Sockserver'
        pathSockmon = f'/home/pi/AppInnova/Eject/Sockmon'
        print('HMS: Ejecutando 3001')
        status3001 = subprocess.Popen([path3001])
        time.sleep(1)
        print('HMS: Ejecutando CCM')
        statusCCM = subprocess.Popen([pathCCM])
        time.sleep(1)
        print('HMS: Ejecutando Sockserver')
        statusSockserver = subprocess.Popen([pathSockserver])
        time.sleep(1)
        print('HMS: Ejecutando Sockmon')
        # statusSockmon = subprocess.Popen([pathSockmon])


        pass
    def open_connections(self):
        """
        Opens the connections to CCM and Monedero using the provided adapters and parameter dictionaries
        :return: None
        :rtype: None
        """

        self.logger.debug("Setting up binding for Monedero")
        self.mon_adapter.bind_and_setup_listening()
        time.sleep(1)
        #TODO: solo para linux
        #self.startProcessSeg()
        time.sleep(1)
        self.logger.debug("Opening connection to CCM")
        self.ccm_adapter.open()
        self.logger.info("Connections initialized")


    def close_connections(self):
        """
        Closes the connections to CCM and Monedero
        :return: None
        :rtype: None
        """
        self.logger.debug("Closing connection to CCM")
        self.ccm_adapter.close()
        self.logger.debug("Closing connectiong for Monedero")
        self.mon_adapter.close()
        self.logger.info("Connections stopped")

    @reconnect_on_broken_pipe
    def transact_message_to_ccm(self, message: str):
        """
        Transacts a message using the configured adapters. 
        Using this method makes use of the adapter configuration in terms of the delays required
        """
        self.logger.debug(f" PI --> CCM: {message}")
        result = self.ccm_adapter.transact_message(message)
        self.logger.debug(f" CCM --> PI: {result}")
        return result

    @reconnect_on_broken_pipe
    def send_message_to_ccm(self, message: str):
        """
        Sends a message to the CCM using the configured adapter. Does not return a reply. Locks the data client.

        :param message: 
        :type message: 
        :return: None
        :rtype: None
        """
        with hw_lock:
            self.logger.debug(f" PI --> CCM: {message}")
            self.ccm_adapter.send_message(message)

    def receive_message_from_ccm(self) -> str:
        """
        Receives a message from the CCM using the configured adapter

        :return: message
        :rtype: str
        """
        with hw_lock:
            return self.ccm_adapter.receive_message_with_stop_byte()

    def set_monedero_callback(self, message_callback: Callable[[Any, str], str]) -> None:
        """
        Sets the callback function for messages received from Monedero

        :param message_callback: callback function for incoming messages on bound port. only required if you will be \
            listening on that specific port in order to be able to notify whoever it may interest. 

            The callback function may return a value. That value will be used to reply to the received message. \
            If the returned value is None, no message will be sent
        :type message_callback: Callable[[Any, str], str]
        """
        print('Configurando Monedero')
        self.mon_adapter.set_message_handler(message_callback)


class BlockingAMQPClient:
    def __init__(self, incoming_mq_params: pika.connection.Parameters, outgoing_mq_params: pika.connection.Parameters,
                 incoming_queue_name: str, outgoing_queue_name: str, message_handler:
            Callable[[BlockingChannel, pika.spec.Basic.Deliver, pika.spec.BasicProperties, bytes], None],auto_delete: bool = False):
        """
        Cliente bloqueante de AMQP, sincrono. Abre dos conexiones a dos servidores: uno para la lectura y el otro para
        la escritura. Puede ser el mismo servidor. Cada vez que se llama la funcion process_data_events los eventos
        de pika se gestionan. Si hay mensajes nuevos, se llama la funcion de callback - message_handler. Al enviar los 
        mensajes se usan los parametros pasados al constructor.
         
        Es posible instanciar esta clase sin definir una cola de respuesta. En este caso, se espera a que en las 
        llamadas a send_message se pase el nombre de la cola a la que se tiene que responder. 
        
        
        :param incoming_mq_params: parametros de conexion para la conexion de lectura
        :type incoming_mq_params: pika.connection.Parameters
        :param outgoing_mq_params: parametros de conexion para la conexion de escritura
        :type outgoing_mq_params: pika.connection.Parameters
        :param incoming_queue_name: nombre de la cola para la conexion de lectura
        :type incoming_queue_name: str
        :param outgoing_queue_name: nombre de la cola para la conexion de escritura
        :type outgoing_queue_name: str
        :param message_handler: funcion de callback para nuevos mensajes leidos
        :type message_handler: Callable[[BlockingChannel, pika.spec.Basic.Deliver, pika.spec.BasicProperties, bytes],None]
        :param auto_delete: indica si las colas tienen que ser creadas con auto_delete
        :type auto_delete: bool
        :param out_queue_phone_params: conexion para la cola con el phone
        :type out_queue_phone_name: nombre de la cola de salida con el phone
        """
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing BlockingAMQPClient")
        self._incoming_queue_name_ = incoming_queue_name
        self._outgoing_queue_name_ = outgoing_queue_name
        self._message_handler_: Callable[[BlockingChannel, pika.spec.Basic.Deliver,
                                          pika.spec.BasicProperties, bytes], None] = message_handler
        # incoming consume
        self._incoming_connection_ = pika.BlockingConnection(incoming_mq_params)
        self._incoming_channel_: Channel = self._incoming_connection_.channel()
        self._incoming_channel_.queue_declare(incoming_queue_name, durable=not auto_delete,
                                              auto_delete=auto_delete)
        self._incoming_channel_.basic_qos(prefetch_count=1)
        self._outgoing_connection_: pika.BlockingConnection = None
        # outgoing push

        self._outgoing_connection_ = pika.BlockingConnection(outgoing_mq_params)
        self._outgoing_channel_: Channel = self._outgoing_connection_.channel()
        self._outgoing_channel_.queue_declare(outgoing_queue_name, durable=not auto_delete,
                                              auto_delete=auto_delete)
        self.logger.debug("BlockingAMQPClient initialized")
        #iniciamos parametros de queue Phone





    def set_message_handler(self, handler: Callable[[BlockingChannel, pika.spec.Basic.Deliver,
                                                     pika.spec.BasicProperties, bytes], None]) -> None:
        """
        Sets the message handler for messages coming from the web service. BlockingAMQPClient will propagate \
        events coming from the queue to this handler.
        
        :param handler: function that handles the received message
        :type handler: Callable[[BlockingChannel, pika.spec.Basic.Deliver, pika.spec.BasicProperties, bytes], None]
        :return: None
        :rtype: None
        """
        self._message_handler_ = handler

    def begin_consuming(self):
        """
        Begins consuming the pika queue. Uses the provided callback function as callback
        :param callback: callback function
        :type callback: Callable
        """
        self.logger.debug(f"Now listening incoming messages on {self._incoming_connection_} in queue" +
                          f"{self._incoming_queue_name_}. Reply is configured to {self._outgoing_connection_} in queue" +
                          f"{self._outgoing_queue_name_}")
        self._incoming_channel_.basic_consume(self._message_handler_, queue=self._incoming_queue_name_,
                                              no_ack=True)

    def send_bytes(self, message: bytes, props: pika.spec.BasicProperties = None):
        self.send_message(bytes.decode(message), props)

    def send_message(self, message: str, props: pika.spec.BasicProperties = None, queue_name_override: str = None):
        """
        Sends a message to the outgoing queue. If the message properties are empty 
         
        :param message: message to send
        :type message: str
        :param props: pika message properties
        :type props: pika.spec.BasicProperties
        :param queue_name_override: outgoing queue, overrides defined in config
        :type queue_name_override:
        """
        print('envio mensaje')
        print(props)
        if props is None:
            props = pika.spec.BasicProperties()
        if props.message_id is None:
            props.message_id = str(uuid4())
        if props.delivery_mode is None:
            props.delivery_mode = 2  # 2 - persistent
        if props.timestamp is None:
            props.timestamp = int(time.time())  # current time UTC unix



        routing_key: str = self._outgoing_queue_name_

        if queue_name_override is not None:
            routing_key = queue_name_override
            self._outgoing_channel_.queue_declare(routing_key, auto_delete=True, durable=False)

        body = message
        if not self._outgoing_channel_.is_open:
            self._outgoing_channel_.open()
        self.logger.debug(f"Sending outgoing message on queue {self._outgoing_queue_name_}: {props.message_id}")
        self._outgoing_channel_.basic_publish(exchange='',
                                              routing_key=routing_key,
                                              body=body,
                                              properties=props)


    def process_data_events(self) -> None:
        """
        Processes AMQP data events. Due to this being a blocking client the order in which the data events are \
        processed is critical as it gives priority to operations 
        
        """
        self._incoming_connection_.process_data_events()
        if self._outgoing_connection_ is not None:
            self._outgoing_connection_.process_data_events()

    def queue_delete(self, props: pika.spec.BasicProperties = None, queue_name_override: str = None):
        print('<<<<<<<<<<<<<<<======================================>>>>>>>>>>>>>>>>>>>>>')
        print('<<<<<<<<<<<<<<<======================================>>>>>>>>>>>>>>>>>>>>>')
        print('<<<<<<<<<<<<<<<======================================>>>>>>>>>>>>>>>>>>>>>')
        if props is None:
            props = pika.spec.BasicProperties()
        routing_key: str = self._outgoing_queue_name_

        if queue_name_override is not None:
            routing_key = queue_name_override
            self._outgoing_channel_.queue_declare(routing_key, auto_delete=False, durable=False)

        print('<<<<<<<<<<<<<<<======================================>>>>>>>>>>>>>>>>>>>>>')
        print('<<<<<<<<<<<<<<<======================================>>>>>>>>>>>>>>>>>>>>>')
        print('<<<<<<<<<<<<<<<======================================>>>>>>>>>>>>>>>>>>>>>')
        if not self._outgoing_channel_.is_open:
            self._outgoing_channel_.open()
        self._outgoing_channel_.queue_purge(queue_name_override)
        
class QueueDestroid:
    def __init__(self):
        self.Credential:str='amqp://MachineDimatica:Machine@innova.vservers.es:5672'


    def queue_delete(self,_queue:str):
        try:
            Conexion=pika.BlockingConnection(pika.URLParameters(self.Credential))
            Canal:Channel=Conexion.channel()
            Canal.queue_delete(_queue,False,False)
            Canal.close()
        except Exception:
            print('Error Eliminando Cola')


        '''
        self.Conexion = pika.BlockingConnection(pika.URLParameters(self.Credenciales))
        self.Canal = self.Conexion.channel()
        self.Canal.queue_delete(_Queue,False,False)
        else:
             self.Canal.queue_delete(self.IN_NameQueue_App,False,False)
             self.Canal.queue_delete(self.PUT_NameQueue_App,False,False)
        pass
        '''
    def queue_purge(self,_queue:str):
        try:
            Conexion = pika.BlockingConnection(pika.URLParameters(self.Credential))
            Canal:Channel = Conexion.channel()

            Canal.queue_purge(_queue)
            Canal.close()
        except Exception:
            print('Error Purgando cola')

    def newMessageServer(self, message: str, props: pika.spec.BasicProperties = None, queue_name: str = None):
        print('HMS: envioo mensaje server')
        try:
            if props is None:
                props = pika.spec.BasicProperties()
            if props.message_id is None:
                props.message_id = str(uuid4())
            if props.delivery_mode is None:
                props.delivery_mode = 2  # 2 - persistent
            if props.timestamp is None:
                props.timestamp = int(time.time())

            Conexion = pika.BlockingConnection(pika.URLParameters(self.Credential))
            Canal = Conexion.channel()
            Canal.queue_declare(queue=queue_name,durable=True)
            body=message
            Canal.basic_publish(exchange='',
                                              routing_key=queue_name,
                                              body=body,
                                              properties=props)
            Conexion.close()




        except Exception:
            pass



        pass