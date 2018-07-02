import innovapos.shared.data.utils as utils
import innovapos.shared.protocols.messaging_pb2 as pb_msg

byties = b"\n\x08\n\x03123\x10\xf8\x03\x12YCurrent state is WorkerStates.IDLE. Expected: [<WorkerStates.BUYING_CASH: 'BUYING_CASH'>]"
msg = pb_msg.GenericResponse()
msg.ParseFromString(byties)
print(msg)

