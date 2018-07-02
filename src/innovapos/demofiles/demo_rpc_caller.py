#!/usr/bin/env python
from time import sleep

import pika
import uuid
import sys

from pika.adapters.blocking_connection import BlockingChannel

class RPCClient(object):
    def __init__(self):
        self.response = None
        self.machine_connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', port=5672, credentials=pika.PlainCredentials(
                username="innova_demo",
                password="dimatica"
            )))
        self.server_connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='innova.boromak.com', port=5672, credentials=pika.PlainCredentials(
                username="innova_demo",
                password="dimatica"
            )))

        self.server_to_pi: BlockingChannel = self.server_connection.channel()
        self.pi_to_server: BlockingChannel = self.machine_connection.channel()

        self.server_to_pi.queue_declare("INC-demomachine")
        self.pi_to_server.queue_declare("OUT-demomachine")
        self.pi_to_server.basic_consume(self.on_response, no_ack=True,
                                        queue="OUT-demomachine")

    def on_response(self, ch, method, props, body):
        print("GOT RESPONSE")
        self.response = body
        print(body)

    def call(self, body):
        delivery_result = self.server_to_pi.basic_publish(body=body, routing_key="INC-demomachine", exchange='',
                                                          properties=pika.BasicProperties(delivery_mode=2))

        print(delivery_result)


demo_rpc = RPCClient()
while True:
    text = input("Text to send:")
    demo_rpc.call(text)
    demo_rpc.machine_connection.process_data_events()
    sleep(0.25)

