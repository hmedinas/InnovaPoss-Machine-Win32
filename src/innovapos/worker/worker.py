import logging
import logging.handlers
import os
import traceback
import json
import time
from enum import Enum
from pathlib import Path
from time import sleep


from typing import Callable, Sequence

import pika
import re
from pika.adapters.blocking_connection import BlockingChannel

from innovapos.shared.data import utils
from innovapos.shared.data.abstractions import AbstractDataAdapter, BaseDataAdapterParameters
from innovapos.shared.data.adapters import TCPDataAdapterParameters, TCPDataAdapter, SerialDataAdapterParameters#,SerialDataAdapter
from innovapos.shared.data.exceptions import NotUnderstoodException
from innovapos.shared.data.utils import Singleton
from innovapos.worker.clients import HardwareClient, BlockingAMQPClient
import datetime
import os

class HardwareWorkerSettings:
    def __init__(self):
        """
        Reflects the configuration file that is read from the drive.
        By default targets the simulator and a local RabbitMQ instance
        """
        self.machine_id = None
        self.restart_on_fail_seconds: str = None
        self.include_stacktrace: bool = False
        self.rabbitmq_incoming_connection_string: str = None
        self.rabbitmq_incoming_queue_name: str = None
        self.rabbitmq_outgoing_connection_string: str = None
        self.rabbitmq_outgoing_queue_name: str = None
        self.rabbitmq_app_gate_connection_string: str = None
        self.rabbitmq_app_gate_queue_name: str = None
        self.logging_logger_name: str = None
        self.logging_level: int = None
        self.logging_filename: str = None
        self.logging_format: str = None
        self.ccm_adapter_type: str = None
        self.ccm_connection_string: str = None
        self.mon_adapter_type: str = None
        self.mon_connection_string: str = None
        self.general_adapter = BaseDataAdapterParameters()
        self.general_adapter.send_msg_end = "\n"
        self.general_adapter.recv_msg_end = "\n"
        self.general_adapter.timeout = 1
        self.general_adapter.answer_delay = 1


    @staticmethod
    def parse_config_to_settings(path: str):
        """
        Parses a settings file with its configuration. 

        :param path: path to load configuration from
        :type path: str
        :return: loaded settings object
        :rtype: HardwareWorkerSettings
        """
        # check that file exists. if it does not - raise
        if not path:
            raise ValueError("Path to config file is None")
        else:
            from pathlib import Path
            print(f'Path {path}')
            my_file = Path(path)
            if not my_file.is_file():
                raise FileNotFoundError("Could not find config file at provided path")
        from configparser import ConfigParser
        parser = ConfigParser()
        parser.read(path)
        config = HardwareWorkerSettings()

        # uuid from getnode is the mac address of the current machine in the case that we don't have one defined
        import uuid
        config.machine_id = utils.get_with_default(parser, "worker", "machine_id", uuid.getnode())
        config.include_stacktrace = utils.get_with_default(parser, "worker", "include_stacktrace", False)
        config.restart_on_fail_seconds = int(utils.get_with_default(parser, "worker", "restart_on_fail_seconds", 3))

        config.logging_level = utils.get_with_default(parser, "logging", "level", "DEBUG")
        config.logging_filename = utils.get_with_default(parser, "logging", "filename", 'innovapos_no_config.log')
        config.logging_format = utils.get_with_default(parser, "logging", "format",
                                                       "%%(asctime)s %%(name)s %%(levelname)s %%(message)s")
        config.ccm_adapter_type = utils.get_with_default(parser, "ccm_adapter", "type", None)
        config.ccm_connection_string = utils.get_with_default(parser, "ccm_adapter", "connection_string", None)
        config.mon_adapter_type = utils.get_with_default(parser, "mon_adapter", "type", None)
        config.mon_connection_string = utils.get_with_default(parser, "mon_adapter", "connection_string", None)
        # config.general_adapter.send_msg_end = utils.get_with_default(parser, "general_adapters", "send_end_char",
        #                                                              config.general_adapter.send_msg_end)
        # config.general_adapter.recv_msg_end = utils.get_with_default(parser, "general_adapters", "receive_end_char",
        #                                                              config.general_adapter.recv_msg_end)
        # TODO: fix ini file \n auto escape
        config.general_adapter.send_msg_end = '\n'
        config.general_adapter.recv_msg_end = '\n'

        timeout_int = int(utils.get_with_default(parser, "general_adapters", "timeout", "2"))
        config.general_adapter.timeout = timeout_int
        answer_delay_int = int(utils.get_with_default(parser, "general_adapters", "answer_delay", "2"))
        config.general_adapter.answer_delay = answer_delay_int
        conn = parser.get("rabbitmq_incoming", "connection_string")
        print(f'conexcion: {conn}')
        config.rabbitmq_incoming_connection_string = parser.get("rabbitmq_incoming", "connection_string")
        config.rabbitmq_incoming_queue_name = f'{parser.get("rabbitmq_incoming", "queue_name")}{config.machine_id}'
        config.rabbitmq_outgoing_connection_string = parser.get("rabbitmq_outgoing", "connection_string")
        config.rabbitmq_outgoing_queue_name = f'{parser.get("rabbitmq_outgoing", "queue_name")}{config.machine_id}'
        #gateway
        config.rabbitmq_app_gate_connection_string = parser.get("rabbitmq_local", "connection_string")
        config.rabbitmq_app_gate_queue_name = f'{parser.get("rabbitmq_local", "queue_name")}-{config.machine_id}'



        return config



class WorkerStates(Enum):
    NONE = "NONE"  # --si
    DEBUGGING = "DEBUGGING"
    ANY = "ANY"  # --si
    BOOTING = "BOOTING"
    IDLE = "IDLE"
    BUYING_CASH = "BUYING_CASH"
    BUYING_CASH_NO_APP = "BUYING_CASH_NO_APP"
    WAITING_CASH = "WAITING_CASH"
    RETURN_CASH = "RETURN_CASH"
    DISPENSING = "DISPENSING"
    WAIT_COLLECTION = "WAIT_COLLECTION"
    MANUAL = "MANUAL"  # --si
    APP = "APP"  # --si
    WAIT_PRODUCT_OUT="WAIT_PRODUCT_OUT" #--si
    WAIT_PRODUCT_OUT_LOCAL="WAIT_PRODUCT_OUT_LOCAL"
    LOCAL="LOCAL"

class MessageJson():
    Accion=''
    Phone=''
    Success='true'
    Status=''
    Mensaje=''
    TimeBloq=''

class ErrorProcess():
    DESCONOCIDO = "ERR-1000: ERROR DESCONOCIDO"  # --si
    CONEXION_USO= "ERR-1001: La conexion esta en uso"
    USO_APP = "ERR-1002: Maquina usada por APP"
    CCM_STATUS = "ERR-2001: Maquina No disponible"
    CCM_SELECT = "ERR-2002: No se puede Seleccionar el producto"
    CCM_OUT_PRODUC="ERR-2003: Existe un Producto en el Dispensador, Retirelo para continuar"
    CCM_WRITE = "ERR-2004: No se puede Despachar el producto"
    TIME_OUT="ERR-2004: Su compra ha exedido el tiempo Establecido."
    PRICE_LACK="ERR-3001: Precio Insuficente "

    SET_STOCK="ERR-3002: no se puede Actualizar el Stock"
    SET_STOCK_FULL="ERR-3003: No se puede actualizar el Stock Full"
    GET_STOCK="ERR-3004: No se puede obtener el Stock"
    GET_STOCK_FULL="ERR-3005:  No se puede obtener el Stock Full"
    SET_PRICE="ERR-3006: Error Actualizando el Precio"

class SussesProcess():
    START='Proceso Iniciado con Exito'
    PREPARE='Equipo Preparado Para Compra'
    CANCEL='Operaciones Canceladas'
    CCM_STATUS = "Maquina disponible"
    CCM_SELECT = "Producto Seleccionado"
    CCM_WRITE = "Producto Despachado"

    SET_STOCK = "Stock Agregado con Exito"
    SET_STOCK_FULL = "Stock Agregado con Exito"
    SET_PRICE = "Actiualizacion de Precio Correcto"
    ADD_TIME = "Tiempo extra Asignado"

class ConstantesProcess():
    TimeMessageExpire:str='60000'
    QueueServer:str='SERVER'
    TimeMessageExpireMovil:str='120000'
    QueueServerCompra:str='OUT_ServerREAD'




@Singleton
class HardwareWorker:
    _instance_ = None

    def __init__(self):
        """
        Main coordinator of the interaction with the dispenser
        Uses innovapos.dispenser.adapters.HardwareClient in order to interact with the data; \
        the pika library is used in order to be able to read and write from RabbitMQ

        """
        self._ws_handlers_ = {}
        self._gateway_handlers_ = {}
        self._app_handlers_ = {}
        self.settings: HardwareWorkerSettings = None
        self.hardware_client: HardwareClient = None
        self.ws_client: BlockingAMQPClient = None
        self.gateway_client: BlockingAMQPClient = None
        self.cur_app_user_client: BlockingAMQPClient = None
        self.machine_id = None
        self.current_state = WorkerStates.BOOTING
        # TODO: Variables de Uso local
        self.importeIngresado = 0
        self.precioProducto = 0
        self.KeyApi:str=None
        self.KeyTime:int=0
        self.new_inc_queue:str=None
        self.new_out_queue:str=None
        self.Fecha:datetime=None
        self.isFinish:bool=False

    def restart(self):
        self.current_state = WorkerStates.IDLE
        self.KeyApi: str = None
        self.KeyTime: int = 0
        self.new_inc_queue: str = None
        self.new_out_queue: str = None
        self.Fecha: datetime = None
        self.current_state=WorkerStates.IDLE

    @staticmethod
    def _shared_decorator_(fn, handlers_dict, rule, valid_states):
        if valid_states is None or len(valid_states) == 0:
            raise RuntimeError("Valid states for a handler cannot be None or empty. Use WorkerStates.NONE if needed")
        if rule in handlers_dict:
            raise RuntimeError(f"rule {rule} is being set twice, existing handler is {handlers_dict[rule]}")
        handlers_dict[rule] = {"valid_states": valid_states, "function": fn}
        return fn

    def ws_message_handler(self, rule, valid_states: Sequence[WorkerStates]) -> \
            Callable[[BlockingAMQPClient, pika.BasicProperties, str], None]:
        """
        Message handler decorator. Registers a function in the handlers dictionary so that when a new message arrives
        from the SERVER message queue it gets handled.
        :param rule: 
        :type rule: 
        :param valid_states: 
        :type valid_states: 
        :return: 
        :rtype: 
        """

        def decorator(fn):
            self._shared_decorator_(fn, self._ws_handlers_, rule, valid_states)
            return fn

        return decorator

    def gateway_message_handler(self, rule, valid_states: Sequence[WorkerStates] = None) -> \
            Callable[[BlockingAMQPClient, pika.BasicProperties, str], None]:
        """
        Message handler decorator. Registers a function in the handlers dictionary so that when a new message arrives
        from the GATEWAY message queue it gets handled.
        :param rule: 
        :type rule: 
        :return: 
        :rtype: 
        """

        def decorator(fn):
            self._shared_decorator_(fn, self._gateway_handlers_, rule, valid_states)
            return fn

        return decorator

    def app_message_handler(self, rule, valid_states: Sequence[WorkerStates] = None) -> \
            Callable[[BlockingAMQPClient, pika.BasicProperties, str], None]:
        """
        Message handler decorator. Registers a function in the handlers dictionary so that when a new message arrives
        from the APP message queue it gets handled.
        :param rule: 
        :type rule: 
        :return: 
        :rtype: 
        """

        def decorator(fn):
            self._shared_decorator_(fn, self._app_handlers_, rule, valid_states)
            return fn

        return decorator

    def _setup_logging_(self) -> None:
        self.logger = logging.getLogger(self.settings.logging_logger_name)
        self.logger.setLevel(self.settings.logging_level)
        log_stream_handler = logging.StreamHandler()
        log_stream_handler.setLevel(self.settings.logging_level)
        log_stream_formatter = logging.Formatter(self.settings.logging_format)
        log_stream_handler.setFormatter(log_stream_formatter)

        if self.settings.logging_filename.startswith("~"):
            self.settings.logging_filename = self.settings.logging_filename.replace("~", os.path.expanduser("~"))
        dir_path = Path(self.settings.logging_filename).parent
        os.makedirs(dir_path, exist_ok=True)
        log_file_handler = logging.handlers.TimedRotatingFileHandler(filename=self.settings.logging_filename,
                                                                     when='D', interval=1, backupCount=0)
        log_file_formatter = logging.Formatter(self.settings.logging_format)
        log_file_handler.setFormatter(log_file_formatter)
        self.logger.addHandler(log_stream_handler)
        self.logger.addHandler(log_file_handler)
        self.logger.info(" = = = = = = Bootstrapper logging setup = = = = = = ")
        self.logger.debug("Bootstrapper config complete")

    def configure_from_config_file(self, config_path: str):
        self.settings = HardwareWorkerSettings.parse_config_to_settings(config_path)
        self._setup_logging_()
        self.machine_id = self.settings.machine_id
        self.logger.info(f"Machine configured as {self.machine_id} from config file {config_path}")

    def _create_and_configure_adapter_(self, adapter_type: str, connection_string: str) -> AbstractDataAdapter:
        """
        Configures a data adapter based on the the configuration loaded

        :param connection_string: configuration string for the needed adapter
        :type connection_string: configuration
        :return: 
        :rtype: 
        """
        adapter: AbstractDataAdapter = None
        if adapter_type == "tcp":
            con_str_split = connection_string.split(":")
            hostname = con_str_split[0]
            port = int(con_str_split[1])
            adapter_params = TCPDataAdapterParameters(hostname=hostname, port=port,
                                                      send_end_char=self.settings.general_adapter.send_msg_end,
                                                      recv_end_char=self.settings.general_adapter.recv_msg_end,
                                                      timeout=self.settings.general_adapter.timeout,
                                                      answer_delay=self.settings.general_adapter.answer_delay)
            adapter = TCPDataAdapter(adapter_params)
        elif adapter_type == "serial":
            adapter_params = SerialDataAdapterParameters(serial_port=connection_string,
                                                         send_end_char=self.settings.general_adapter.send_msg_end,
                                                         recv_end_char=self.settings.general_adapter.recv_msg_end,
                                                         timeout=self.settings.general_adapter.timeout,
                                                         answer_delay=self.settings.general_adapter.answer_delay)
            adapter = SerialDataAdapter(adapter_params)
        return adapter

    def _setup_hw_client_(self):
        ccm_adapter = self._create_and_configure_adapter_(self.settings.ccm_adapter_type,
                                                          self.settings.ccm_connection_string)
        mon_adapter = self._create_and_configure_adapter_(self.settings.mon_adapter_type,
                                                          self.settings.mon_connection_string)
        self.hardware_client: HardwareClient = HardwareClient(ccm_adapter=ccm_adapter, mon_adapter=mon_adapter)

        self.hardware_client.set_monedero_callback(self._monedero_message_received_callback_)
        self.hardware_client.open_connections()


    def _setup_ws_amqp_client_(self):
        #TODO: agregado para phone
        self.ws_client = BlockingAMQPClient(
            incoming_mq_params=pika.URLParameters(self.settings.rabbitmq_incoming_connection_string),
            incoming_queue_name=self.settings.rabbitmq_incoming_queue_name,
            outgoing_mq_params=pika.URLParameters(self.settings.rabbitmq_outgoing_connection_string),
            outgoing_queue_name=self.settings.rabbitmq_outgoing_queue_name,
            message_handler=self._ws_message_received_callback_)
        self.ws_client.begin_consuming()
        self.logger.info("WS AMQP setup done")

    def _setup_app_gateway_amqp_client_(self):
        #todo Agregado para phone
        print(f'innova: {self.settings.rabbitmq_app_gate_connection_string}')
        self.gateway_client = BlockingAMQPClient(
            incoming_mq_params=pika.URLParameters(self.settings.rabbitmq_app_gate_connection_string),
            incoming_queue_name=self.settings.rabbitmq_app_gate_queue_name,
            outgoing_mq_params=pika.URLParameters(self.settings.rabbitmq_app_gate_connection_string),
            outgoing_queue_name=self.settings.rabbitmq_app_gate_queue_name + "-default",
            message_handler=self._gateway_message_received_callback_)
        self.gateway_client.begin_consuming()
        self.logger.debug("App Gate AMQP setup done")

    def _setup_cur_app_user_client_(self, incoming_queue_name: str, outgoing_queue_name: str,
                                    message_handler: Callable[[BlockingChannel, pika.spec.Basic.Deliver,
                                                               pika.spec.BasicProperties, bytes], None]):
        self.cur_app_user_client = BlockingAMQPClient(
            incoming_mq_params=pika.URLParameters(self.settings.rabbitmq_app_gate_connection_string),
            incoming_queue_name=incoming_queue_name,
            outgoing_mq_params=pika.URLParameters(self.settings.rabbitmq_app_gate_connection_string),
            outgoing_queue_name=outgoing_queue_name,
            message_handler=message_handler)
        self.cur_app_user_client.begin_consuming()

    def _shared_message_handler_(self, client: BlockingAMQPClient, handlers_dict: dict,
                                 channel: BlockingChannel, method: pika.spec.Basic.Deliver,
                                 props: pika.spec.BasicProperties, body: bytes):
        try:
            self.logger.info(f"Reciviendo mensaje de AMQP. MSG ID: {props.message_id}")
            _props = pika.spec.BasicProperties()
            _props.expiration = '20000'

            if props.type not in handlers_dict:  # no existe handler para este tipo
                print('no existe handler para este tipo')
                self.logger.error('no existe handler para este tipo')
                raise NotUnderstoodException(f"Tipo de Mensaje '{props.type}' No es Soportado por el handler")
            handler_info = handlers_dict[props.type]  # handler existe, lo sacamos
            valid_states = handler_info['valid_states']
            if self.current_state not in valid_states and WorkerStates.ANY not in valid_states:
                # si el estado no es valido o si el comando no soporta "ANY" -> mandamos error
                # TODO: definir como controlar errores de este tipo
                if WorkerStates.NONE in valid_states:
                    self.logger.warning(f"Handler function {handler_info['function']} has a NONE identifier. " +
                                        f"Is this intentional?")
                self.logger.debug(f"Could not handle command {props.message_id}. " +
                                  f"Estado Actual {self.current_state}, Enviado: {valid_states}")


                client.send_message(f"Estado Actual {self.current_state}, Esperado: {valid_states}",props=_props)
                return
            handler = handler_info["function"]
            self.logger.info(f"Handling msg #{props.message_id}, type '{props.type}' with {handler}")
            message = body.decode()
            handler(client, props, message)

        except Exception as exc:
            stack_trace = traceback.format_exc()
            self.logger.error(f"An exception occured while handling MQ message #{props.message_id}\n{stack_trace}")
            client.send_message(stack_trace,props=_props)
            self.logger.debug(f"Error from message #{props.message_id} sent to queue.")

    def _monedero_message_received_callback_(self, message: str) -> str:

        #TODO: hugo monedero callback
        '''
        print('')
        print('')
        print('>>>>>>>>>>>>>< LECTURA MONEDERO >>>>>>>>>>>>>>>>>>>>><')
        print('')
        print('')
        print('')
        '''
        # self.logger.debug(f" Message from Monedero {message}")
        '''
        1.- Verificcamos el comando del monedero
        :param message: 
        :return: 
        '''

        #fecha=str(time.strftime("%H:%M:%S"))
        if 'PING' in message:
            return ''
        self.logger.info(f"Monedero message received: {message}")

        #print(f'Precio Producto:>>>>>>> {self.precioProducto}')
        print(f'====================================')
        print(f'Mensaje monedero: {message}')
        print(f'Status: {self.current_state}')
        print(f'====================================')
        if('CCM_Valor_Introducido' in message and (self.current_state==WorkerStates.APP or self.current_state==WorkerStates.LOCAL)):
            matches = re.search("CCM_Valor_Introducido_(\d+\.\d+)CCM_Valor_Restante_(\d+\.\d+)", message)
            self.importeIngresado = self.importeIngresado + float(matches.groups()[0])
            print('**************************************')
            print('Lectura comandos ')
            print(f'Importe Introducido: {self.importeIngresado}')
            print(f'Mensaje Machine: {message}')
            print('**************************************')
            return 'Status: APP'
        if((self.current_state==WorkerStates.WAIT_PRODUCT_OUT or self.current_state==WorkerStates.WAIT_PRODUCT_OUT_LOCAL) and (('CCM_Producto_OUT' in message)or ('CCM_Producto_Out' in message ))):
            print('Producto retirado OK')
            print('Valida CCM_Producto_OUT Y WAIT_PRODUCT_OUT_LOCAL')
            print(f'Estado Machine:{self.current_state}')
            print(f'isFinish:{self.isFinish}')

            if(self.current_state==WorkerStates.WAIT_PRODUCT_OUT):
                if (self.isFinish==True):
                    self.current_state==WorkerStates.IDLE
                else:
                    self.current_state=WorkerStates.APP
                    print(f'Cambiado Estado:{self.current_state}')
            else:
                if (self.isFinish == True):
                    self.current_state == WorkerStates.IDLE
                else:
                    self.current_state = WorkerStates.LOCAL


            self.importeIngresado=0
            self.precioProducto=0

            return 'OK'

        if ('CCM_OK_DEVOLUCION' in message and (self.current_state==WorkerStates.APP or self.current_state==WorkerStates.LOCAL)):
            self.importeIngresado = 0
            return 'Status: APP'

        print(f'Estatus machine: {self.current_state}')
        #elif ('CCM_DESPEDIDA_OK' in message or 'CCM_OK_DEVOLUCION' in message or 'CCM_Producto_Out' in message or 'CCM_COMMAND_PRODUCTOTAMBOR' in message or 'CCM_Recarga_Stop' in message):
        #
        #    self.current_state=WorkerStates.IDLE
        #    self.importeIngresado=0
        #    self.precioProducto=0
        #else:
        #    print(f'Mensaje: {message}')
        #    self.importeIngresado = 0
        #    self.precioProducto = 0

        return  'Operando'

    def changeStatus(self, Estatus):
        if Estatus.upper() == 'NOR':
            self.current_state = WorkerStates.MANUAL
        elif Estatus.upper() == 'APP':
            self.current_state = WorkerStates.APP
        else:
            self.current_state = WorkerStates.IDLE

    def messageJsonOutput(self, Mensaje: MessageJson,MultiDat:str=None):
        return self.messageJsonOutput_Encoding(Mensaje.Accion, Mensaje.Phone, Mensaje.Success, Mensaje.Status, Mensaje.Mensaje,Mensaje.TimeBloq,MultiDat)

    ''
    def messageJsonOutput_Encoding(self, Accion, Phone, Success, Status, Mensaje,TimeBloq,MultiDat):

        jsonData = '{"Accion":"'+str(Accion)+'","Phone":"'+str(Phone)+'","Success":'+str(Success)+',"Status":"'+str(Status)+'","Mensaje":"'+str(Mensaje)+'","TimeBloq":"'+str(TimeBloq)+'"}'
        if MultiDat!=None:
            jsonData = '{"Accion":"' + str(Accion) + '","Phone":"' + str(Phone) + '","Success":' + str(
                Success) + ',"Status":"' + str(Status) + '","Mensaje":' + str(Mensaje) + '}'
        jsonToPython =jsonData# json.loads(jsonData)
        print(f'Mensaje >>>> : {jsonToPython}')
        return jsonToPython

    def _ws_message_received_callback_(self, channel: BlockingChannel, method: pika.spec.Basic.Deliver,
                                       props: pika.spec.BasicProperties, body: bytes):
        self._shared_message_handler_(self.ws_client, self._ws_handlers_, channel, method, props, body)

    def _gateway_message_received_callback_(self, channel: BlockingChannel, method: pika.spec.Basic.Deliver,
                                            props: pika.spec.BasicProperties, body: bytes):
        self._shared_message_handler_(self.gateway_client, self._gateway_handlers_, channel, method, props, body)

    def _app_message_received_callback_(self, channel: BlockingChannel, method: pika.spec.Basic.Deliver,
                                        props: pika.spec.BasicProperties, body: bytes):
        self._shared_message_handler_(self.cur_app_user_client, self._app_handlers_, channel, method, props, body)

    def run_with_autorecover(self):
        """
        Runs the worker
        """
        self.logger.info("Starting up dispenser main loop")
        self.logger.info(f"Following command handlers were registered:\n {', '.join(self._ws_handlers_.keys())}")
        while True:
            try:
                self.logger.info(f"Ejecutando Autorecover.Inicio el worker de conexiones")
                print('HMS: configurando hw_client_')
                #TODO: TV
                self.logger.info(f"Configurando conexiones con los Soket")
                self._setup_hw_client_()
                print('HMS: configurando amqp_client_')
                self._setup_ws_amqp_client_()
                #TODO: desactivamos la parte del gateway
                print('HMS: configurando gateway')
                # HMS: gateway
                #self._setup_app_gateway_amqp_client_()
                self.logger.info(f"Conexion Iniciada con Exito. Inicio de Loop de eventos.")
                self.current_state = WorkerStates.IDLE

                #import threading
                #import sys
                #from innovapos.worker.tasks.Api import API
                #Service=API()
                #Service.Run()

                #t=threading.Thread(target=Service.Run())
                #t.start()
                #t.join()
                #Service.Run()

                while True:
                    self.ws_client.process_data_events()
                    #HMS: gateway
                    #self.gateway_client.process_data_events()
                    if self.cur_app_user_client is not None:
                        self.cur_app_user_client.process_data_events()
                    sleep(0.1)
            except Exception as e:
                self.logger.exception(f"An error has occurred during worker execution.")
                self.logger.info("Recovering from error. Restarting in " +
                                 f"{self.settings.restart_on_fail_seconds} seconds...")
                sleep(self.settings.restart_on_fail_seconds)
