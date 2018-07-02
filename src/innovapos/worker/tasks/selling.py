import json

import pika

from innovapos.worker.app_worker import worker
from innovapos.worker.clients import BlockingAMQPClient
from innovapos.worker.worker import WorkerStates


@worker.ws_message_handler("app.lock", [WorkerStates.IDLE])
def lock_worker_for_app(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    Locks the machine in order for the user to pay
    Responses:
        GenericMessage:
            metadata:
                status_code:
                    200: CCM returned OK
    """
    # todo: worker -> Locked
    worker.current_state = WorkerStates.BUYING_CASH

    device_id = "DEMO"
    new_inc_queue = f"op-inc-{worker.machine_id}-{device_id}"
    new_out_queue = f"op-out-{worker.machine_id}-{device_id}"
    # instantiate new cur_app_user_client
    worker.cur_app_user_client = BlockingAMQPClient(
        incoming_mq_params=pika.URLParameters(worker.settings.rabbitmq_app_gate_connection_string),
        outgoing_mq_params=pika.URLParameters(worker.settings.rabbitmq_app_gate_connection_string),
        incoming_queue_name=new_inc_queue,
        outgoing_queue_name=new_out_queue,
        message_handler=worker._app_message_received_callback_,
        auto_delete=True
    )
    worker.cur_app_user_client.begin_consuming()
    msg=worker.messageJsonOutput_Encoding(Accion='InicioComunicacion',Phone='',Success='true',Status='OK',Mensaje='Communicacion Aceptada')
    client.send_message(msg,queue_name_override=new_out_queue)



@worker.ws_message_handler("ccm.write", [WorkerStates.ANY])
def rasp_dispense(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str)-> None:
    """
    Executes the command on the CCM and returns its reply
    Responses:
        GenericMessage:
            metadata:
                status_code:
                    200: CCM returned OK
    """
    params: dict = json.loads(message)
    ccm_status = worker.hardware_client.transact_message_to_ccm("CCM_Getstatus")
    if 'OK' not in ccm_status:
        client.send_message("ERROR")
    ccm_write_response = worker.hardware_client.transact_message_to_ccm(f"CCM_Write({params['columna']},{params['fila']})")

    response = worker.hardware_client.transact_message_to_ccm(message)
    client.send_message(response)

