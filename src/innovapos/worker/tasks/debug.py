import pika

from innovapos.worker.app_worker import worker
from innovapos.worker.clients import BlockingAMQPClient
from innovapos.worker.worker import WorkerStates


@worker.ws_message_handler("debug.states.get", [WorkerStates.ANY])
def states_change(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    Devuelve el estado actual 
    """
    client.send_message(f"Current state is {worker.current_state}")


@worker.ws_message_handler("debug.states.change", [WorkerStates.ANY])
def states_change(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    Actualiza el estado actual al estado proporcionado en el body
    """
    message = message.upper()
    if message not in WorkerStates.__dict__:
        client.send_message("Not a valid enum")
        return
    old_state = worker.current_state
    worker.current_state = WorkerStates[message]
    client.send_message(f"State changed from {old_state} to {worker.current_state}")


@worker.ws_message_handler("debug.states.simple_any", [WorkerStates.ANY])
def states_any(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    Llamada de prueba para ANY
    """
    client.send_message(f"You called DEBUG.STATES.SIMPLE_ANY. Current state is {worker.current_state}")


@worker.ws_message_handler("debug.states.debugging_pass", [WorkerStates.DEBUGGING])
def states_fail(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    Llamada con filtrado de prueba
    """
    client.send_message(f"Current state is {worker.current_state}")


# @worker.ws_message_handler("debug.states.valid_state_definition") -> falla. valid_states no esta definido
# @worker.ws_message_handler("debug.states.valid_state_definition", []) -> falla, valid_states esta vacio
@worker.ws_message_handler("debug.states.valid_state_definition", [WorkerStates.NONE])
def states_fail(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    Ejemplo de definicion correcta de handler de mensajes
    """
    # unreachable code, no state defined
    client.send_message(f"Current state is {worker.current_state}")


@worker.ws_message_handler("debug.multihandler_ping", [WorkerStates.ANY])
@worker.gateway_message_handler("debug.multihandler_ping", [WorkerStates.ANY])
@worker.app_message_handler("debug.multihandler_ping", [WorkerStates.ANY])
def multihandler_ping(client: BlockingAMQPClient, props: pika.spec.BasicProperties, message: str) -> None:
    """
    Ejemplo de definicion correcta de handler de mensajes
    """
    # unreachable code, no state defined
    client.send_message("PONG")
