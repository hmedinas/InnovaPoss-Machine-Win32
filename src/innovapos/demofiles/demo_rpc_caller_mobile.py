#!/usr/bin/env pythonfrom time import sleep
from time import sleep

import pika
from pika.adapters.blocking_connection import BlockingChannel


class RPCClient(object):
    def __init__(self):
        self.response = None
        self.direct_conn = pika.BlockingConnection(pika.ConnectionParameters(
            host='192.168.1.64', port=5672, credentials=pika.PlainCredentials(
                username="innova_demo",
                password="dimatica"
            )))

        self.mobile_to_pi: BlockingChannel = self.direct_conn.channel()

        self.mobile_to_pi.queue_declare("DIRECT-demodevice-in", durable=True)
        self.mobile_to_pi.queue_declare("DIRECT-demodevice-out", durable=True)
        self.mobile_to_pi.basic_consume(self.on_response, no_ack=True,
                                        queue="DIRECT-demodevice-out")

    def on_response(self, ch, method, props, body):
        self.response = body
        print(f"Response is {body}")

    def call(self, body):
        self.response = None
        self.mobile_to_pi.basic_publish(body=body, routing_key="DIRECT-demodevice-in", exchange='',
                                        properties=pika.BasicProperties(delivery_mode=2))
        demo_rpc.direct_conn.process_data_events(3)

    def receive_until_timeout(self):
        self.response = None
        demo_rpc.direct_conn.process_data_events(3)


demo_rpc = RPCClient()
while True:
    mode = input("Choose a mode(1 - send, 2 - receive): ")
    if '1' in mode:
        text = input("Text to send: ")
        demo_rpc.call(text)
    else:
        print("Trying to receive message")
        demo_rpc.receive_until_timeout()
