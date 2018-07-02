import pika

connection: pika.connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
channel: pika.channel = connection.channel()
channel.queue_declare(queue="rpc_queue")



def fib(n):
    if n == 0:
        return 0;
    elif n == 1:
        return 1
    else:
        return fib(n - 1) + fib(n - 2)


def on_request(ch: pika.channel, method, props: dict, body: str):
    n = int(body)
    print(' [server] fibbo - ', n)
    response = fib(n)
    ch.basic_publish(exchange='', routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id=props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue='rpc_queue')

print(" [server] Waiting for requests")

channel.start_consuming()