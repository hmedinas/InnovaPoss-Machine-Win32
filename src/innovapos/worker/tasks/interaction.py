import pika
import sys
import json

from innovapos.worker.app_worker import worker
from innovapos.worker.clients import BlockingAMQPClient
from innovapos.worker.worker import WorkerStates
from innovapos.worker.worker import MessageJson
from innovapos.worker.worker import ErrorProcess
from innovapos.worker.worker import SussesProcess
from innovapos.worker.worker import ConstantesProcess
from innovapos.worker.clients import QueueDestroid
import datetime
import time
import os


#region Metodos Globales
def CCM_Getstatus(Accion:str=None) -> MessageJson():
    _Result = MessageJson()
    _Result.Accion = Accion
    rpt = worker.hardware_client.transact_message_to_ccm('CCM_Getstatus')
    print(f" ----> Respuesta Status: {rpt}")
    if 'OK' in rpt:
        _Result.Status = 'OK'
        _Result.Mensaje = ''
    else:
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.CCM_STATUS
    return _Result

def CCM_Select(_Carril:str,Accion:str=None) -> MessageJson():
    _Result = MessageJson()
    _Result.Accion = Accion
    rpt = worker.hardware_client.transact_message_to_ccm('CCM_Select(' + _Carril + ')')
    print(f" ------> Respuesta Select: {rpt}")
    if 'OK' in rpt:
        _Result.Status = 'OK'
        _Result.Mensaje = ''
    else:
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.CCM_SELECT
    return _Result

def CCM_Write(_Carril:str,Accion:str=None) ->MessageJson():
    _Result = MessageJson()
    _Result.Accion = Accion
    rpt = worker.hardware_client.transact_message_to_ccm('CCM_Write(' + _Carril + ')')
    print(f"Respuesta Write: {rpt}")
    if 'OK' in rpt:
        _Result.Status='OK'
        _Result.Mensaje = ''
    else:
        _Result.Status='KO'
        _Result.Mensaje = ErrorProcess.CCM_WRITE
    return _Result
def GetStockStar():
    reply = worker.hardware_client.transact_message_to_ccm("CCM_stockfull")
    print(f'Full Stock: {reply}')
    return reply

def setLocalVar():
    worker.restart()
    worker.current_state = WorkerStates.APP

def Devolucion() -> bool:
    print('Ejecutando devolucion')
    reply1 = worker.hardware_client.transact_message_to_ccm("CCM_Devolucion")
    print(f' -----> devolucion {reply1}')
    if 'OK' in reply1 or 'CCM_Devolucion' in reply1:
        return True
    else:
        return False


def FechaActual():
    _FechaActual = datetime.datetime.now()
    #_x = _FechaActual.strftime('%H:%M:%S')
    return _FechaActual
def TimeBloq():
    try:
        h1=worker.Fecha
        h2=FechaActual()
        hhmmss=h1-h2
        Segundos = hhmmss.seconds
        return Segundos
    except Exception as e:
        return 0

def ProductoEnTambor(Accion:str)->MessageJson():
    _Result = MessageJson()
    _Result.Accion=Accion
    if (worker.current_state == WorkerStates.WAIT_PRODUCT_OUT):
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.CCM_OUT_PRODUC
        return _Result
    else:
        _Result.Status = 'OK'
        _Result.Mensaje = ''
        return _Result

def SetValUse(_Result:MessageJson,Estado:WorkerStates) ->MessageJson():
    if (ConexionTimeBloq() == True):
        print('***************************')
        print(' ERROR MAQUINA EN USO')
        print(f'Fecha Actual : {FechaActual()}')
        print(f'Fecha Bloqueada : {worker.Fecha}')
        print('***************************')
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.CONEXION_USO
        return _Result
    else:
        print('***************************')
        print(' DESTRUIMOS LAS COLAS DE LA APP')
        print('***************************')
        print('====================================')
        print(f'Fecha Actual: {FechaActual()}')
        print(f'Fecha Activa Comunicacion: {worker.Fecha}')
        print('Session Expirada por tiempo ')
        print('====================================')
        _Result.Status = 'OK'
        _Result.Mensaje=ErrorProcess.TIME_OUT
        oQueueDestroid = QueueDestroid()
        if(worker.new_inc_queue !=''):
            oQueueDestroid.queue_delete(worker.new_inc_queue)
            oQueueDestroid.queue_delete(worker.new_out_queue)
        setLocalVar()
        return _Result

def AddTimeConectionWorker(time_new: int):
    # si sobra mas de 1 minuto no se suma nada
    h1 = worker.Fecha
    h2 = FechaActual()
    hhmmss = h1 - h2
    Segundos = hhmmss.seconds
    if (Segundos < 55):
        worker.KeyTime = worker.KeyTime + time_new
        _FechaActual = worker.Fecha
        _FechaNueva = datetime.timedelta(seconds=time_new)
        _FechaResult = _FechaActual + _FechaNueva
        print(f'***************************************')
        print(f'Fecha Actual: {FechaActual()}')
        print(f'Fecha Bloq: {worker.Fecha}')
        print(f'Nueva Fe. Bloq: {_FechaResult}')
        print(f'****************************************')
        worker.Fecha = _FechaResult

def MessageJsonStock(Carril: str = None):
    _CarrilesFormat: str = '''{
            "11":2,
            "12":5,
            "13":6,
            "14":5,
            "15":8,
            "16":4,
            "21":2,
            "22":5,
            "23":6,
            "24":5,
            "25":8,
            "26":4,
            "31":2,
            "32":5,
            "33":6,
            "34":5,            
            "35":8,
            "36":4,
            "41":2,
            "42":5,
            "43":6,
            "44":5,
            "45":8,
            "46":4,
            "51":2,
            "52":5,
            "53":6,
            "54":5,
            "55":8,
            "56":4
  }'''
    _CarrilesFormat: str = str(GetStockStar())
    _CarrilesFormat = '{' + _CarrilesFormat + '}'
    _Machine: str = "PRUEBAS_HMS"

    Comando = '{"Comand":"STOCK","Machine":"' + _Machine + '","Fecha":"' + FechaActual() + '" ,"Stock":"' + _CarrilesFormat + '"}'
    return Comando

def MessageJsonDispacher(_Carril: str = None, _User: str = None, _Camp: str = None):
    _CarrilesFormat: str = None
    _Machine: str = worker.machine_id
    Comando = '{"Accion":"DISPACHER","Machine":"' + _Machine + '","Fecha":"' + FechaActual().strftime(
        '%d/%m/%Y') + '","User":"' + _User + '","Camp":"' + _Camp + '" ,"Carril":"' + _Carril.replace(',',
                                                                                                      '') + '"}'
    return Comando

def ConexionTimeBloq():
    Fecha = worker.Fecha
    _FechaActual = datetime.datetime.now()
    if (Fecha > _FechaActual):
        return True
    else:
        return False

def NameQueueServer():
    return ConstantesProcess.QueueServerCompra
#endregion

#region Comandos Mobil
#==============================================================================
#==============================================================================
#                COMUNICACION DE MANERA LOCAL CON EL APLICATIVO
#==============================================================================
#==============================================================================
@worker.ws_message_handler("ccm.start", [WorkerStates.ANY])
def StartProyect(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str)->None:
    '''

           :param client: 
           :param props: 
           :param message: 
           :return: 
           '''
    # region Accion del metodo
    # 1.- verificamos si la mauina esta en uso
    # 2.- Cambiamos el estatus de uso de la maquina
    # 3.- Verificamos el Status de la maquina
    # 4.- Preparamos la maquina hacemos el select
    # 5.- Despachamos el producto
    # endregion
    # region  Variables locales de configuracion
    _Result = MessageJson()
    _Result.Accion = "START"
    _props = pika.spec.BasicProperties()
    _props.expiration =ConstantesProcess.TimeMessageExpire
    _minutos: float = 0
    _segundos: float = 0
    _fecha: datetime = None
    print('************************************')
    print(f'Message Start: {message}')
    print('************************************')
    # endregion

    try:
        # region 1,2.- Verificamos si la maquins esta en uso y cambiamos estado a uso de la mauina
        # ==========================================
        # si la maquina esta en nada cambiamos de estado, si la macuina esta en uso verficamos por cuanto tiempo
        # esta tomada la maquina para ver si puede ser usada o no
        # ==========================================

        _tempResult = MessageJson();
        _tempResult = CCM_Getstatus(_Result.Accion)
        if (_tempResult.Status == 'KO'):
            _Result = _tempResult
            return


        if(ProductoEnTambor(_Result.Accion).Status=='KO'):
            _Result=ProductoEnTambor(_Result.Accion)
            return
        if (worker.current_state == WorkerStates.IDLE):
            setLocalVar()
        else:
            _Result = SetValUse(_Result,WorkerStates)
            if (_Result.Status == 'KO'):  # solo si existe error
                msg = worker.messageJsonOutput(_Result, None)
                return



        params: dict = json.loads(message)
        worker.new_inc_queue = str(params['QueueIn'])
        worker.new_out_queue = str(params['QueueOut'])
        worker.KeyTime = int(params['QueueTime'])
        _minutos = worker.KeyTime / 60
        _temp = worker.KeyTime % 60
        _segundos = 0
        if _temp > 0:
            _segundos = worker.KeyTime - (60 * _minutos)

        _FechaActual = datetime.datetime.now()
        _FechaNueva = datetime.timedelta(minutes=_minutos, seconds=_segundos)
        _FechaResult = _FechaActual + _FechaNueva
        worker.Fecha = _FechaResult
        _x = worker.Fecha.strftime('%H:%M:%S')

        print(f''' =========================
       parametros de Inicio
       =====================
       Fecha Actual :{_FechaActual}
       workwer.Fecha : {_FechaResult}
       Queue1 :{worker.new_inc_queue} 
       Queue2 :{worker.new_out_queue}
                       ''')

        # TODO: Consultando el Stock
        print('solicitando Stock full')
        _CarrilesFormat: str = str(GetStockStar())

        # Creamos el cliente dinamico
        worker.cur_app_user_client = BlockingAMQPClient(
        incoming_mq_params=pika.URLParameters(worker.settings.rabbitmq_app_gate_connection_string),
        outgoing_mq_params=pika.URLParameters(worker.settings.rabbitmq_app_gate_connection_string),
        incoming_queue_name=worker.new_inc_queue,
        outgoing_queue_name=worker.new_out_queue,
        message_handler=worker._app_message_received_callback_,
        auto_delete=False
        )
        worker.cur_app_user_client.begin_consuming()

        _Result.Status = 'OK'
        _Result.Phone = ''
        _Result.Mensaje = SussesProcess.START  # 'Communicacion Aceptada'
        _Result.TimeBloq = str(TimeBloq())
        # mensaje en la cola nueva creada
        print('******************************************')
        msg = worker.messageJsonOutput(_Result, None)
        print(f'Mensaje a Cola nueva creada')
        worker.cur_app_user_client.send_message(f'{msg}', _props)
        time.sleep(0.5)
        print('******************************************')

        _Result.Mensaje = _CarrilesFormat  # 'stock del producto'
    except Exception as e:
        worker.logger.exception(e)
        _Result.Phone = ''
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.DESCONOCIDO  # 'ERR-1000: Error no controlado. '
    finally:

        print('******************************************')
        msg = worker.messageJsonOutput(_Result, None)
        print(f'Enviando Mensaje server: {msg}')
        client.send_message(f'{msg}', _props)
        print('******************************************')

@worker.app_message_handler("ccm.prepare", [WorkerStates.APP,WorkerStates.WAIT_PRODUCT_OUT])
@worker.ws_message_handler("PrepareProduct", [WorkerStates.WAIT_PRODUCT_OUT,WorkerStates.LOCAL])
def PrepareProduct(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str)->None:
    _Result = MessageJson()
    _ResultTemp=MessageJson()
    _Result.Accion = "PREPARE"
    _Result.TimeBloq = str(TimeBloq())
    props = pika.spec.BasicProperties()
    props.expiration = ConstantesProcess.TimeMessageExpireMovil
    print(f'Mensaje Prepare Input: {message}')
    try:
        if (ConexionTimeBloq() == False):
            print('====================================')
            print('  SESSION EXPIRADA POR TIEMPO ')
            print(f'Fecha: {FechaActual()}')
            print(f'Fecha Actual: {FechaActual()}')
            print(f'Fecha Activa Comunicacion: {worker.Fecha}')
            print('====================================')
            _Result.Status = 'KO'
            _Result.Mensaje = ErrorProcess.TIME_OUT
            Devolucion()
            get_ccm_finish(client, props, '')

            return
        if (ProductoEnTambor(_Result.Accion).Status == 'KO'):
            _Result = ProductoEnTambor(_Result.Accion)
            return
        #adicionamos 15 segundos
        AddTimeConectionWorker(15)
        _mensaje = message.split('|');  # 'SR|GUID|4'
        worker.precioProducto = 0;
        worker.importeIngresado = 0;
        params: dict = json.loads(message)
        _carril = str(params['Carril'])
        #******************************************************
        print('Ejecutando Getstatus')
        _ResultTemp=CCM_Getstatus(_Result.Accion)
        if(_ResultTemp.Status=='KO'):
            worker.current_state = WorkerStates.IDLE
            _Result=_ResultTemp
            return
        else:
            if(Devolucion()==False):
                print(f'Error en devolucion de dinero')
                worker.current_state = WorkerStates.IDLE
                return
            else:
                _ResultTemp=CCM_Select(_carril, _Result.Accion)
                if(_ResultTemp.Status=='KO'):
                    _Result=_ResultTemp
                    worker.current_state = WorkerStates.IDLE
                    return
                else:
                    _Result.Status='OK'
                    _Result.Mensaje= SussesProcess.PREPARE
        #***********************************************************

    except ValueError:
        worker.current_state = WorkerStates.IDLE
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.DESCONOCIDO
        print("Oops!  Error Maquina Defectuosa...")
    finally:
        msg = worker.messageJsonOutput(_Result)
        print('Enviando Correo APP: PREPARE')
        print(f'Estado Maquina: {worker.current_state}')
        if(worker.current_state==WorkerStates.APP or worker.current_state==WorkerStates.WAIT_PRODUCT_OUT):
            worker.cur_app_user_client.send_message(f'{msg}', props)
        else:
            print(f'>>> Sin cola a cual notificar')

@worker.app_message_handler("ccm.dispacher", [WorkerStates.APP])
@worker.ws_message_handler("ccm.dispacher", [WorkerStates.ANY])
def DispacherProduct(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    El metodo tiene que 
    1.- Verificar si el monto introducido es >= que el solicitado
    2.- Verificar el Status
    3.- Pre-Seleccionar
    4.- Despachar
    :param client: 
    :param props: 
    :param message: SR|GUID|2|1,1|1.5 ==>
                    SR=>Servidor
                    GUID=>GUID del cliente
                    2 ==> dispacher
                    1,1 ==> carril a despachar
                    1,5 ==> precio 
    :return: 
    """
    # region  Variables locales de configuracion

    _Result = MessageJson()
    _ResultTemp=MessageJson()
    _Result.Accion = "DISPACHER"
    _props = pika.spec.BasicProperties()
    oQueueDestroid = QueueDestroid()
    _props.expiration = ConstantesProcess.TimeMessageExpireMovil
    _minutos: float = 0
    _segundos: float = 0
    _fecha: datetime = None
    print(f'Dispacher Mensaje Input: {message}')
    # endregion
    try:
        if (ConexionTimeBloq() == False):
            print('====================================')
            print(f'Fecha Actual: {FechaActual()}')
            print(f'Fecha Activa Comunicacion: {worker.Fecha}')
            print('Session Expirada por tiempo ')
            print('====================================')
            _Result.Status = 'KO'
            _Result.Mensaje = ErrorProcess.TIME_OUT
            msg = worker.messageJsonOutput(_Result)
            worker.cur_app_user_client.send_message(f'{msg}', props)
            #destruimos la cola y devolvemos el dinero
            try:
                Devolucion()
                get_ccm_finish(client, props, '')

            except:
                pass

            return
        '''
          {
              "Comand": "DISPACHER",
              "Phone": "-",
              "Ejecut": "2",
              "Carril":"1,1",
              "Price":1.5,
              "Promo":"true" o false
          } 
        '''
        params: dict = json.loads(message)
        _price = float(params['Price'])
        _carril = str(params['Carril'])
        _IdUser: str = str(params['User'])
        _IdCamp: str = str(params['Camp'])
        if (str(params['Promo']).upper() == 'TRUE'):
            _Promo = True
        else:
            _Promo = False

        worker.precioProducto = _price
        print('===================================')
        print('DISPACHER')
        print(f'Fecha: {FechaActual()}')
        print(f'importe ingresado: {worker.importeIngresado}')
        print(f'importe esperado: {_price}')
        print(f'Es promo:{_Promo}')
        print('===================================')
        # ******************************************************
        if (worker.importeIngresado >= _price):
            _ResultTemp = CCM_Getstatus(_Result.Accion)
            if (_ResultTemp.Status == 'KO'):
                worker.current_state = WorkerStates.IDLE
                _Result = _ResultTemp
                return
            else:
                worker.precioProducto = _price
                # se quita a peticion de pablo
                #_ResultTemp = CCM_Select(_carril, _Result.Accion)
                _ResultTemp.Status='OK'
                if (_ResultTemp.Status == 'KO'):
                    _Result = _ResultTemp
                    worker.current_state = WorkerStates.IDLE
                    return
                else:
                    _ResultTemp=CCM_Write(_carril,_Result.Accion)
                    if(_ResultTemp.Status=='KO'):
                        _Result=_ResultTemp
                        return
                    else:
                        print('===================================')
                        print('PRODUCTO DESPACHADO')
                        print(f'Fecha: {FechaActual()}')
                        print('===================================')
                        _Result.Status='OK'
                        _Result.Mensaje=SussesProcess.CCM_WRITE
                        #TODO: enviamos la compra al servidor
                        msgNew = MessageJsonDispacher(_carril, _User=_IdUser, _Camp=_IdCamp)
                        print(f'Message al Server: {msgNew}')
                        oQueueDestroid.newMessageServer(msgNew, props=None, queue_name=NameQueueServer())
                        time.sleep(0.5)
                        #cambiamos el stado para retirar el producto
                        worker.current_state = WorkerStates.WAIT_PRODUCT_OUT #//fecha 09/08/2018
                        #worker.current_state = WorkerStates.IDLE

                        print('===================================')
                        print('ENVIO DE COMPRA LA SERVIDOR')
                        AddTimeConectionWorker(15)
                        print('===================================')
            # client.send_message(f'{msg}',props=None,queue_name_override=worker.new_out_queue)
        else:
            print('===================================')
            print('PRECIO INSUFICIENTE PARA HACER LA COMPRA')
            print(f'Fecha: {FechaActual()}')
            print(f'Estado Maquina: {worker.current_state}')
            print('===================================')
            _Result.Status = "KO"
            _Result.Mensaje = ErrorProcess.PRICE_LACK
            msg = worker.messageJsonOutput(_Result)
            print(f'Mensaje : {msg}')

    except Exception as ex:
        _Result.Status = "KO"
        _Result.Success = 'false'
        _Result.Mensaje = ErrorProcess.DESCONOCIDO
        msg = worker.messageJsonOutput(_Result)
        print(f'Estado Maquina: {worker.current_state}')
        worker.cur_app_user_client.send_message(f'{msg}', props=_props)

    finally:
        msg = worker.messageJsonOutput(_Result)
        print(f'Mensaje : {msg}')
        worker.cur_app_user_client.send_message(f'{msg}', props=_props)
        if (_Result.Status == 'OK'):
            if _Promo:
                print(f'===========  PROMO ============')
                AddTimeConectionWorker(45)
                print(f'Estado Maquina: {worker.current_state}')
            else:
                worker.precioProducto = 0
                worker.importeIngresado = 0
                worker.isFinish = False
                print(f'Estado Maquina: {worker.current_state}')

# TODO: Finalizacionn de la compra
@worker.app_message_handler("ccm.finish", [WorkerStates.ANY])
@worker.ws_message_handler("ccm.finish", [WorkerStates.ANY])
def get_ccm_finish(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    _Result = MessageJson()
    oQueueDestroid = QueueDestroid()
    _Result.Accion = "FINISH"
    _Result.TimeBloq = str(TimeBloq())
    _Promo: bool = False
    _props = pika.spec.BasicProperties()
    _props.expiration = ConstantesProcess.TimeMessageExpire
    worker.isFinish = True
    try:
        print('=================')
        print(f'Iniciando Finish')
        print('=================')
        worker.current_state = WorkerStates.IDLE
        # TODO: DETRUIR COLAS IN y OUT
        if(worker.new_out_queue is not None):
            oQueueDestroid.queue_delete(_queue=worker.new_out_queue)
        if(worker.new_inc_queue is not None):
            oQueueDestroid.queue_delete(_queue=worker.new_inc_queue)

        worker.restart()


    except Exception as e:
        print('Error metodo finish')

    print('=================')
    print(f'Finalizo ejecucion de Finish')
    print('=================')

# TODO: Envio del Stock a demana del Servidor
@worker.ws_message_handler("ccm.stock", [WorkerStates.ANY])
def get_ccm_stock(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    print('generando Stock')
    oQueueDestroid = QueueDestroid()
    oQueueDestroid.newMessageServer(MessageJsonStock(), props=None, queue_name=NameQueueServer())


#TODO: Set Stock Temporal de maquina
@worker.ws_message_handler("ccm.SetStock",[WorkerStates.ANY])
def SetStock(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    print(f'Message : {message}')
    _Result = MessageJson()
    _Result.Accion = "SET_STOCK"
    _Error=list()
    _Temp:str=''
    print('=====================')
    print('SOLICITANDO ACTUALIZACION')
    print('======================')
    _props = pika.spec.BasicProperties()
    _props.expiration = '12000'
    try:
        params: dict = json.loads(message)
        reply = worker.hardware_client.transact_message_to_ccm("CCM_Getstatus")
        if 'OK' in reply:
            _Carriles= params['CARRIL']
            for i in _Carriles:
                print(f'i =>{i}')
                print(f'carrilesi =>{_Carriles[i]}')
                _SetComand="CCM_putstock("+str(i[0:1])+","+str(i[-1])+")_"+str(_Carriles[i])
                _Temp="("+str(i[0:1])+","+str(i[-1])+")_"+str(_Carriles[i])
                print(f'Comand:{_SetComand}')
                reply = worker.hardware_client.transact_message_to_ccm(_SetComand)
                if 'OK' in reply:
                    _Result.Status='OK'
                    _Result.Mensaje=SussesProcess.SET_STOCK
                    print('*********************')
                    print('STOCK ACTUALIZADO')
                    print(f'Rpt: {reply}')
                    print('*********************')
                else:
                    _Result.Status = 'OK'
                    _Result.Mensaje =ErrorProcess.SET_STOCK
                    _Error.append(_Temp)
                    '''
                    if(len(_Error)>2):
                        _Error="&"+_Temp
                    else:
                        _Error=_Temp'''

                    print('*********************')
                    print('ERROR ACTUALIZADO')
                    print(reply)
                    print('*********************')

            if (len(_Error) >0):

                for reg in _Error:
                    _SetComand = "CCM_putstock" + str(reg)
                    print(f'Comand:{_SetComand}')
                    reply = worker.hardware_client.transact_message_to_ccm(_SetComand)
                    if 'OK' in reply:
                        print('*********************')
                        print('STOCK ACTUALIZADO')

                        print('*********************')
                    else:
                        print('*********************')
                        print('ERROR ACTUALIZADO')
                        print(reply)
                        print('*********************')
        else:
            _Result.Status='KO'
            _Result.Mensaje=ErrorProcess.CCM_STATUS
            print('*********************')
            print('ERROR ACTUALIZANDO- ESTATUS')
            print('*********************')
    except ValueError:
            worker.current_state = WorkerStates.IDLE
            _Result.Status='KO'
            _Result.Mensaje=ErrorProcess.DESCONOCIDO
            print('*********************')
            print('ERROR ACTUALIZANDO- DESCONOCIDO')
            print('*********************')
    finally:
        msg = worker.messageJsonOutput(_Result)
        print(f'Mensaje : {msg}')
        client.send_message(f'{msg}',props=_props)

#TODO: Continue Compra
@worker.app_message_handler("ccm.Continue", [WorkerStates.APP])
@worker.ws_message_handler("ccm.Continue", [WorkerStates.ANY])
def Continue(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    _Result = MessageJson()
    _Result.Accion = "SET_CONTINUE"
    _Error = list()
    _Temp: str = ''
    print('=====================')
    print('SOLICITANDO CONTINUE')
    print(f'Message : {message}')
    print('======================')
    try:
        AddTimeConectionWorker(60)
    except ValueError:
        print('Error actualizando Fecha')

@worker.ws_message_handler("ccm.GetStock", [WorkerStates.ANY])
def GetStock(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    print(f'Message : {message}')
    _Result = MessageJson()
    _Result.Accion = "GET_STOCK"
    print('=====================')
    print('SOLICITANDO STOCK')
    print('======================')
    try:
        print(message)
        params: dict = json.loads(message)
        reply = worker.hardware_client.transact_message_to_ccm("CCM_Getstatus")
        if 'OK' in reply:
            _Carril = params['CARRIL']
            print(f'carril=> {_Carril}')
            _SetComand = "CCM_stock(" + str(_Carril[0:1]) + "," + str(_Carril[-1]) + ")"
            print(f' comand=>{_SetComand}')
            reply = worker.hardware_client.transact_message_to_ccm(_SetComand)
            _Result.Status = 'OK'
            _Result.Mensaje = 'Strock opkkkkk'

            print('*********************')
            print('STOCK CARRIL')
            print(reply)
            resp = reply.replace(_SetComand + "_", '')
            print(resp)
            print('*********************')
        else:
            _Result.Status = 'KO'
            _Result.Mensaje = ErrorProcess.CCM_STATUS
            print('*********************')
            print('ERROR - ESTATUS')
            print('*********************')
    except ValueError:
        worker.current_state = WorkerStates.IDLE
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.DESCONOCIDO
        print('*********************')
        print('ERROR - DESCONOCIDO')
        print('*********************')
    finally:
        msg = worker.messageJsonOutput(_Result)
        print(f'Mensaje : {msg}')
        client.send_message(f'{msg}')

@worker.ws_message_handler("ccm.SetStockFull", [WorkerStates.ANY])
def SetStockFull(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:

    _Result = MessageJson()
    _Result.Accion = "SET_STOCK_FULL"
    print('=====================')
    print('SOLICITANDO ACTUALIZACION FULL')
    print(f'Message : {message}')
    print('======================')
    _props = pika.spec.BasicProperties()
    _props.expiration = '12000'

    try:
        params: dict = json.loads(message)
        _Carril = params['CARRIL']

        _SetComand = "CCM_putstockfull" + _Carril
        print(f'Colmand: {_SetComand}')
        reply = worker.hardware_client.transact_message_to_ccm(_SetComand)
        print(f'Stock Full: {reply}')
        if 'OK' in reply:
            _Result.Status = 'OK'
            _Result.Mensaje = SussesProcess.SET_STOCK_FULL

        else:
            _Result.Status = 'KO'
            _Result.Mensaje = ErrorProcess.SET_STOCK_FULL

    except ValueError:
        worker.current_state = WorkerStates.IDLE
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.DESCONOCIDO
        print('*********************')
        print('ERROR ACTUALIZANDO- DESCONOCIDO')
        print('*********************')
    finally:
        msg = worker.messageJsonOutput(_Result)
        print(f'Mensaje : {msg}')
        client.send_message(f'{msg}', props=_props)

@worker.ws_message_handler("ccm.GetStockFull", [WorkerStates.ANY])
def GetStockFull(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    _Result = MessageJson()
    _Result.Accion = "GET_SOCK_FULL"
    print('=====================')
    print('SOLICITANDO STOCK FULL')
    print(f'Message : {message}')
    print('======================')
    try:

        _SetComand = "CCM_stockfull"

        reply = GetStockStar()
        print(f'respuesta: {reply}')
        if reply is not None:
            _Result.Status = 'OK'
            _Result.Mensaje = reply
        else:
            _Result.Status = 'KO'
            _Result.Mensaje = 'error en stock'

    except ValueError:
        worker.current_state = WorkerStates.IDLE
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.DESCONOCIDO
        print('*********************')
        print('ERROR OBTENIENDO- DESCONOCIDO')
        print('*********************')
    finally:
        msg = worker.messageJsonOutput(_Result)
        print(f'Mensaje : {msg}')
        client.send_message(f'{msg}')

@worker.ws_message_handler("ccm.SetPrecio", [WorkerStates.ANY])
def SetPrice(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    _Result = MessageJson()
    _Result.Accion = "SET_PRICE"
    print('=====================')
    print('SOLICITANDO SET PRICE')
    print(f'Message : {message}')
    print('======================')
    _props = pika.spec.BasicProperties()
    _props.expiration = '12000'

    try:
        params: dict = json.loads(message)
        _Carril = params['CARRIL']
        _Price = params['PRICE']

        _SetComand = "CCM_putprecio(" + str(_Carril[0:1]) + "," + str(_Carril[-1]) + ")_" + _Price
        print(f'Colmand: {_SetComand}')
        reply = worker.hardware_client.transact_message_to_ccm(_SetComand)
        print(f'Set Price: {reply}')
        if 'OK' in reply:
            _Result.Status = 'OK'
            _Result.Mensaje = SussesProcess.SET_PRICE

        else:
            _Result.Status = 'KO'
            _Result.Mensaje = ErrorProcess.SET_PRICE

    except ValueError:
        worker.current_state = WorkerStates.IDLE
        _Result.Status = 'KO'
        _Result.Mensaje = ErrorProcess.DESCONOCIDO
        print('*********************')
        print('ERROR ACTUALIZANDO- DESCONOCIDO')
        print('*********************')
    finally:
        msg = worker.messageJsonOutput(_Result)
        print(f'Mensaje : {msg}')
        client.send_message(f'{msg}', props=_props)


#endregion

@worker.ws_message_handler("ccm.get_status", [WorkerStates.BUYING_CASH])
def get_ccm_get_status(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str)-> None:
    """
    Executes the command on the CCM and returns its reply
    Responses:
        GenericMessage:
            metadata:
                status_code:
                    200: CCM returned OK
    """
    reply = worker.hardware_client.transact_message_to_ccm("CCM_Getstatus")
    client.send_message("OK" if reply is not None and 'OK' in reply else "ERROR")


@worker.ws_message_handler("ccm.execute_command", [WorkerStates.ANY])
def rasp_get_stock(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str)-> None:
    """
    Executes the command on the CCM and returns its reply
    Responses:
        GenericMessage:
            metadata:
                status_code:
                    200: CCM returned OK
    """
    print(f'Mensaje Origen: {message}')
    response = worker.hardware_client.transact_message_to_ccm(message)
    print(f'respuesta CCM: {response}')
    client.send_message(response)

#TODO: Inicio de Comandos Maquina
@worker.ws_message_handler("ccm.start_", [WorkerStates.ANY])
def rasp_start(client:BlockingAMQPClient, props: pika.spec.BasicProperties, message: str)-> None:
    #PHONE_[GUID]_IN    |   PHONE_[GUID]_OUT    |   TIME
    _message='PHONE_HUGO_IN|PHONE_HUGO_OUT|120'
    _Result = MessageJson()
    _Result.Accion = "START"

    _props = pika.spec.BasicProperties()
    _props.expiration = '24000'
    oQueueDestroid=QueueDestroid()
    _minutos:float=0
    _segundos:float=0
    _fecha:datetime=None
    print(f'Mensaje Input: {message}')
    worker.isFinish=False
    try:
        if (CCM_Getstatus() == False):
            _Result.Accion = "PREPARE"
            _Result.Status = "KO"
            _Result.Mensaje = ErrorProcess.CCM_STATUS
            return


        if (worker.current_state == WorkerStates.WAIT_PRODUCT_OUT):
            _Result.Status = 'KO'
            _Result.Mensaje = ErrorProcess.CCM_OUT_PRODUC
            msg = worker.messageJsonOutput(_Result)
            client.send_message(msg, props=_props)
            return

        if (worker.current_state == WorkerStates.IDLE):
            worker.current_state = WorkerStates.APP

        else:
            #si tiene una conexion activa ya
            #_FechaActual = datetime.datetime.now()
            if(ConexionTimeBloq()==True):
                print('***************************')
                print(' ERROR DOBLE INICIO DE SESSION')
                print(f'Fecha Actual : {FechaActual()}')
                print(f'Fecha Bloqueada : {worker.Fecha}')
                print('***************************')
                _Result.Status = 'KO'
                _Result.Mensaje = ErrorProcess.CONEXION_USO
                msg = worker.messageJsonOutput(_Result, None)
                print(f'{msg}')
                client.send_message(msg,props=_props)
                return
            else:
                print('***************************')
                print(' DESTRUCCION DE COLA POR INICIO NUEVO')
                print('***************************')
                oQueueDestroid.queue_delete(worker.new_inc_queue)
                oQueueDestroid.queue_delete(worker.new_out_queue)
                worker.restart()
                worker.current_state = WorkerStates.APP

        '''
        {
            "Comand": "START",
            "QueueIn": "PHONE_START_IN",
            "QueueOut": "PHONE_START_OUT",
            "QueueTime":120
        }
        
        '{"Comand": "START","QueueIn": "PHONE_START_IN","QueueOut": "PHONE_START_OUT","QueueTime":2}'
        
        '''
        print(f'Mensaje Comand Start: {message}')
        print(f'Fecha Inicio msg :{FechaActual()}')
        params: dict = json.loads(message)
        _Result.Accion = "START"

        worker.new_inc_queue = str(params['QueueIn'])
        worker.new_out_queue = str(params['QueueOut'])
        worker.KeyTime = int(params['QueueTime'])

        _minutos=worker.KeyTime/60
        _temp=worker.KeyTime%60
        _segundos=0
        if _temp>0:
            _segundos=worker.KeyTime -(60*_minutos)

        _FechaActual = datetime.datetime.now()
        _FechaNueva = datetime.timedelta(minutes=_minutos, seconds=_segundos)
        _FechaResult = _FechaActual + _FechaNueva
        worker.Fecha = _FechaResult
        _x=worker.Fecha.strftime('%H:%M:%S')

        print(f''' =========================
parametros de Inicio
=====================
Fecha Actual :{_FechaActual}
workwer.Fecha : {_FechaResult}
Queue1 :{worker.new_inc_queue} 
Queue2 :{worker.new_out_queue}

                ''')

        #TODO: Consultando el Stock
        print('solicitando Stock full')
        _CarrilesFormat: str = str(GetStockStar())



        # instantiate new cur_app_user_client
        worker.cur_app_user_client = BlockingAMQPClient(
            incoming_mq_params=pika.URLParameters(worker.settings.rabbitmq_app_gate_connection_string),
            outgoing_mq_params=pika.URLParameters(worker.settings.rabbitmq_app_gate_connection_string),
            incoming_queue_name=worker.new_inc_queue,
            outgoing_queue_name=worker.new_out_queue,
            message_handler=worker._app_message_received_callback_,
            auto_delete=False
        )
        worker.cur_app_user_client.begin_consuming()
        # mensaje de inicio de comunicacion

        _Result.Status = 'OK'
        _Result.Phone = ''
        _Result.Mensaje = SussesProcess.START# 'Communicacion Aceptada'
        _Result.TimeBloq = str(TimeBloq())
        msg = worker.messageJsonOutput(_Result,None)

        # mensaje en la cola nueva creada
        worker.cur_app_user_client.send_message(f'{msg}',_props)
        time.sleep(0.5)
        # TODO: Metodo del Stock de la Maquina total
        # reply = worker.hardware_client.transact_message_to_ccm("CCM_Devolucion")

        _Result.Mensaje =_CarrilesFormat# 'stock del producto'
        print("Enviando Mensaje Phone")
        print(f'Fecha Phone msg :{FechaActual()}')

    except Exception as e:
        worker.logger.exception(e)
        _Result.Phone=''
        _Result.Status='KO'
        _Result.Mensaje=ErrorProcess.DESCONOCIDO# 'ERR-1000: Error no controlado. '

    finally:
        print("Enviando Mensaje server")
        _Result.TimeBloq = str(TimeBloq())
        msg= worker.messageJsonOutput(_Result,None)
        client.send_message(f'{msg}',_props)
        print(f'Fecha server msg :{FechaActual()}')


#TODO: Comando de Cancelar Operacion
@worker.ws_message_handler("ccm.Cancel", [WorkerStates.APP])
@worker.app_message_handler("ccm.Cancel", [WorkerStates.APP])
def rasp_Cancel(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    # PHONE_[GUID]_IN    |   PHONE_[GUID]_OUT    |   TIME
    try:
        #worker.current_state = WorkerStates.IDLE
        print(f'==================')
        print(f'        CANCEL ')
        print(f'mensaje imput: {message}')
        print(f'==================')
        worker.precioProducto=0
        worker.importeIngresado=0
        worker.KeyTime=0
        worker.KeyApi=''
        print('Lecturas Canceladas')
        _Result = MessageJson()
        _Result.Accion = "CANCEL"
        _Result.Status = 'OK'
        _Result.Phone = ''
        _Result.TimeBloq = str(TimeBloq())
        _Result.Mensaje =SussesProcess.CANCEL# 'Communicacion Aceptada'
        msg = worker.messageJsonOutput(_Result)
        print(f'msg: {msg}')

        print(f'----> Ejecutando CCM_Devolucion')
        reply1 = worker.hardware_client.transact_message_to_ccm("CCM_Devolucion")
        print(f'CCM_Devolucion: {reply1}')

        # mensaje en la cola nueva creada
        #client.send_message(f'{msg}', props=None, queue_name_override=worker.new_out_queue)
        #worker.cur_app_user_client.queue_purge()

        #client.queue_purge()
        #worker.cur_app_user_client.queue_delete(props=None,queue_name_override=worker.new_out_queue)

    except Exception:
        print('errrrrrr')
        e = sys.exc_info()[1]

        _Result.Phone = ''
        _Result.Status = "KO"
        _Result.Success = 'false'
        _Result.Mensaje = ErrorProcess.DESCONOCIDO + ' => ' + e.args[0]

    finally:
        msg = worker.messageJsonOutput(_Result)
        client.send_message(msg)

# TODO: Prepara el Aplicativo para ventas al Contado, hace una devolucion de las monedas ingresadas previas
@worker.app_message_handler("ccm.prepare_", [WorkerStates.APP,WorkerStates.WAIT_PRODUCT_OUT])
def get_ccm_prepare(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
       Prepara el aplicativo,
       1. devolucion de monedas
       2. pone el contador de precio a 0
       3.- cambia de estado al App
       """

    _Result=MessageJson()
    _Result.Accion="PREPARE"
    _Result.TimeBloq = str(TimeBloq())
    props = pika.spec.BasicProperties()
    props.expiration = '120000'
    print(f'Mensaje Input: {message}')
    try:
        if(ConexionTimeBloq()==False):
            print('====================================')
            print('  SESSION EXPIRADA POR TIEMPO ')
            print(f'Fecha: {FechaActual()}')
            print(f'Fecha Actual: {FechaActual()}')
            print(f'Fecha Activa Comunicacion: {worker.Fecha}')

            print('====================================')
            _Result.Status = 'KO'
            _Result.Mensaje = ErrorProcess.TIME_OUT
            msg = worker.messageJsonOutput(_Result)
            worker.cur_app_user_client.send_message(f'{msg}', props)
            return
        if (worker.current_state==WorkerStates.WAIT_PRODUCT_OUT):
            _Result.Status='KO'
            _Result.Mensaje=ErrorProcess.CCM_OUT_PRODUC
            msg = worker.messageJsonOutput(_Result)
            worker.cur_app_user_client.send_message(f'{msg}', props)
            return

        AddTimeConectionWorker(15)

        #time_new = 20
        #worker.KeyTime = worker.KeyTime + time_new
        #_FechaActual = worker.Fecha
        #_FechaNueva = datetime.timedelta(seconds=time_new)
        #_FechaResult = _FechaActual + _FechaNueva
        #worker.Fecha = _FechaResult
        '''
        {
        "Comand": "PREPARE",
        "Phone": "",
        "Carril":"1,1"
        }
        
        '{"Comand": "PREPARE","Phone": "-"'
        
        '''
        print('Escucho APP: PREPARE')
        _mensaje = message.split('|');#'SR|GUID|4'
        worker.precioProducto=0;
        worker.importeIngresado=0;
        print(f'----> Ejecutando CCM_Getstatus')
        reply = worker.hardware_client.transact_message_to_ccm("CCM_Getstatus")
        print(f'CCM_Getstatus: {reply}')
        print(f'-----> Fin CCM_Getstatus')

        params: dict = json.loads(message)
        _carril = str(params['Carril'])
        if 'OK' in reply:
            print(f'----> Ejecutando CCM_Devolucion')
            reply1 = worker.hardware_client.transact_message_to_ccm("CCM_Devolucion")
            print(f'CCM_Devolucion: {reply1}')
            print(f'-----> Fin CCM_Devolucion')

            if 'OK' in reply1 or 'CCM_Devolucion' in reply1:
                _Result.Status='OK'
                _Result.Mensaje=SussesProcess.PREPARE
                print(f'----> Ejecutando CCM_Select("{_carril}")')
                reply = worker.hardware_client.transact_message_to_ccm("CCM_Select(" + _carril + ")")
                print(f'CCM_Select=>{reply}')
                print(f'-----> Fin CCM_Select')
                if 'OK' in reply:
                    print('====================')
                    print(f'devolucion: {reply}')
                    print(f'Fecha: {FechaActual()}')
                    print('MAQUINA PREPARADA')
                    print('====================')
                    _Result.Status = 'OK'
                    _Result.Mensaje = SussesProcess.PREPARE
                else:
                    print('====================')
                    print(f'Fecha: {FechaActual()}')
                    print('ERROR PREPARANDO LA MAQUINA')
                    print('====================')
                    _Result.Status = 'KO'
                    _Result.Mensaje = ErrorProcess.CCM_SELECT  # 'Maquina Defectuosa'
                    #worker.current_state = WorkerStates.IDLE
            else:
                print('====================')
                print(f'Fecha: {FechaActual()}')
                print('ERROR PREPARANDO LA MAQUINA')
                print('====================')
                _Result.Status='KO'
                _Result.Mensaje=ErrorProcess.CCM_STATUS# 'Maquina Defectuosa'
                worker.current_state = WorkerStates.IDLE
        else:
            _Result.Mensaje=ErrorProcess.CCM_STATUS
            _Result.Status='KO'
            worker.current_state = WorkerStates.IDLE


    except ValueError:
        worker.current_state = WorkerStates.IDLE
        _Result.Status='KO'
        _Result.Mensaje=ErrorProcess.DESCONOCIDO
        print("Oops!  Error Maquina Defectuosa...")
    finally:
        msg=worker.messageJsonOutput(_Result)
        print('Enviando Correo APP: PREPARE')
        print(f'Estado Maquina: {worker.current_state}')
        worker.cur_app_user_client.send_message(f'{msg}',props)

        #client.send_message(f'{msg}', props=None, queue_name_override=worker.new_out_queue)


#TODO: Despacho de producto
@worker.app_message_handler("ccm.dispacher_", [WorkerStates.APP])
@worker.ws_message_handler("ccm.dispacher_", [WorkerStates.ANY])
def get_ccm_dispacher(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    El metodo tiene que 
    1.- Verificar si el monto introducido es >= que el solicitado
    2.- Verificar el Status
    3.- Pre-Seleccionar
    4.- Despachar
    :param client: 
    :param props: 
    :param message: SR|GUID|2|1,1|1.5 ==>
                    SR=>Servidor
                    GUID=>GUID del cliente
                    2 ==> dispacher
                    1,1 ==> carril a despachar
                    1,5 ==> precio 
    :return: 
    """
    print('=========================')
    print('    DISPACHER        ')
    _Result = MessageJson()
    _Result.Accion = "DISPACHER"
    _Result.TimeBloq = str(TimeBloq())
    _Promo:bool=False
    _props = pika.spec.BasicProperties()
    _props.expiration = '30000'
    oQueueDestroid=QueueDestroid()
    print(f'Mensaje Input: {message}')
    print('=========================')

    try:
        if (ConexionTimeBloq() == False):
            print('====================================')
            print(f'Fecha Actual: {FechaActual()}')
            print(f'Fecha Activa Comunicacion: {worker.Fecha}')
            print('Session Expirada por tiempo ')
            print('====================================')
            _Result.Status = 'KO'
            _Result.Mensaje = ErrorProcess.TIME_OUT
            msg = worker.messageJsonOutput(_Result)
            worker.cur_app_user_client.send_message(f'{msg}', props)
            #TODO: Ejecutar una destruccion de la cola y una devolucion de dinero
            try:
                worker.hardware_client.transact_message_to_ccm("CCM_Devolucion")
                get_ccm_finish(client,props,'')

            except:
                pass

            return
        '''
          {
              "Comand": "DISPACHER",
              "Phone": "-",
              "Ejecut": "2",
              "Carril":"1,1",
              "Price":1.5,
              "Promo":"true" o false
          } 
        '''
        #

        params: dict = json.loads(message)
        _price =float(params['Price'])
        _carril=str(params['Carril'])

        if(str(params['Promo']).upper()=='TRUE'):
            _Promo=True
        else:
            _Promo=False
        #_Promo=bool(params['Promo'])
        _IdUser:str=str(params['User'])
        _IdCamp:str=str(params['Camp'])


        _Result.Status='OK'
        _Result.Phone=''
        worker.precioProducto =_price
        print('===================================')
        print('DISPACHER')
        print(f'Fecha: {FechaActual()}')
        print(f'importe ingresado: {worker.importeIngresado}')
        print(f'importe esperado: {_price}')
        print(f'Es promo:{_Promo}')
        print('===================================')
        if(worker.importeIngresado>=_price):
            print(f'----> Ejecutando CCM_Getstatus')
            reply = worker.hardware_client.transact_message_to_ccm("CCM_Getstatus")
            print(f'CCM_Getstatus: {reply}')
            print(f'-----> Fin CCM_Getstatus')

            worker.precioProducto =_price
            if 'OK' in reply:
                print('Dispacher')
                reply ='OK' # worker.hardware_client.transact_message_to_ccm("CCM_Select(" + _carril + ")")
                print(f'CCM_Select=>{reply}')
                if 'OK' in reply:
                    print(f'----> Ejecutando CCM_Write("{_carril}")')
                    reply = worker.hardware_client.transact_message_to_ccm("CCM_Write(" + _carril + ")")
                    print(f'CCM_Write=>{reply}')
                    if 'OK' in reply:
                        print('===================================')
                        print('PRODUCTO DESPACHADO')
                        print(f'Fecha: {FechaActual()}')
                        print(_carril)
                        print('===================================')
                        _Result.Mensaje=SussesProcess.CCM_WRITE
                        #Todo: envio de cambio de Stock al servidor
                        msgNew=MessageJsonDispacher(_carril,_User=_IdUser,_Camp=_IdCamp)
                        print(f'{msgNew}')
                        oQueueDestroid.newMessageServer(msgNew,props=None,queue_name=NameQueueServer())
                        time.sleep(0.5)
                        #en espera de producto ser retirado
                        worker.current_state= WorkerStates.WAIT_PRODUCT_OUT
                        print('===================================')
                        print('ENVIO DE COMPRA LA SERVIDOR')
                        AddTimeConectionWorker(15)
                        print('===================================')
                    else:
                        _Result.Status = 'KO'
                        _Result.Mensaje = ErrorProcess.CCM_WRITE
                else:
                    _Result.Status='KO'
                    _Result.Mensaje=ErrorProcess.CCM_SELECT
            else:
                # enviar mensaje de error
                _Result.Status='KO'
                _Result.Mensaje=ErrorProcess.CCM_STATUS

            msg = worker.messageJsonOutput(_Result)
            print(f'Mensaje : {msg}')
            worker.cur_app_user_client.send_message(f'{msg}',props=_props)
            #client.send_message(f'{msg}',props=None,queue_name_override=worker.new_out_queue)
        else:
            print('===================================')
            print('PRECIO INSUFICIENTE PARA HACER LA COMPRA')
            print(f'Fecha: {FechaActual()}')
            print(f'Estado Maquina: {worker.current_state}')
            print('===================================')
            _Result.Status="KO"
            _Result.Mensaje=ErrorProcess.PRICE_LACK
            msg = worker.messageJsonOutput(_Result)
            print(f'Mensaje : {msg}')
            #se envia el mensaje al cliente
            worker.cur_app_user_client.send_message(f'{msg}',props=_props)

            #client.send_message(f'{msg}', props=None, queue_name_override=worker.new_out_queue)

    except Exception as ex:

        print('Error..... dispacher ')
        print(ex)
        _Result.Status = "KO"
        _Result.Success='false'
        _Result.Mensaje =ErrorProcess.DESCONOCIDO
        msg = worker.messageJsonOutput(_Result)
        print(f'Mensaje : {msg}')
        client.send_message(f'{msg}')
        print(f'Estado Maquina: {worker.current_state}')

    finally:
        if (_Result.Status=='OK'):
            if _Promo:
                print(f'===========  PROMO ============')
                AddTimeConectionWorker(45)
                print(f'Estado Maquina: {worker.current_state}')


            else:
                #worker.current_state=WorkerStates.IDLE
                #worker.KeyTime=0
                worker.precioProducto=0
                worker.importeIngresado=0
                worker.isFinish=False
                print(f'Estado Maquina: {worker.current_state}')


#region
#==============================================================================
#==============================================================================
#                COMUNICACION CON TV
#==============================================================================
#==============================================================================
@worker.ws_message_handler("On_TV",[WorkerStates.ANY])
def On_TV(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str)-> None:
    print(f'MENSAJE IMPUT: {message}')
    os.system("echo 'on 0' | cec-client -s")
    print(f'ejecutado: {message}')

    pass

@worker.ws_message_handler("Off_TV",[WorkerStates.ANY])
def Off_TV(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str)-> None:
    print(f'MENSAJE IMPUT: {message}')
    os.system("echo 'standby 0' | cec-client -s")
    pass


#endregion

