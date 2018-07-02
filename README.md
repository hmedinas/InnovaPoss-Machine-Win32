Title:  Readme de protobuf

Author: Hugo Medina Sotomayor hugo.medinas@outlook.com and
        Borys Makogonyuk Vasylev boris.makogonyuk@gmail.com



Date:   24/05/2017

### Abreviaturas

- IPV - Innova Pos Vending
- RPI - Raspberry Pi
- WS - Web Server (servidor web)
- RMQ - RabbitMQ
- RMQRPI - RabbitMQ en Raspberry Pi
- RMQWS - RabbitMQ en el servidor web


## Descripcion general del proyecto
La solucion "Innova Pos Vending" (IPV en adelante) consiste de 4 partes :

- InnovaPos Vending Mobile App. Aplicacion movil a traves de la cual
  el cliente interactua con el sistema.
- InnovaPos Vending API. API que usa la aplicacion movil como para
  guardar y recuperar datos al igual que hacer otras acciones.
- InnovaPos Vending Gestion. Portal de gestion del sistema. Permite
  gestionar las maquinas de vending, stock, etc.
- **InnovaPos Vending Dispenser (este proyecto)**. Esta es la parte
  que va instalada en unas Raspberry Pi que van a estar en la maquina.
  Esta parte procesa los comandos que vienen desde el servidor y desde
  la aplicacion movil.

## Descripcion general de IPV *Dispenser*
IPV Dispenser es un conjunto de programas escrito en Python. Comunica
con IPV API (en la parte servidor) utilizando RabbitMQ como medio
de transporte.

Consiste de dos partes que interactuan entre ellas:

- **API** (Raspberry Pi). Esta es la API que va a estar disponible
  en las Raspberry Pi para poder recibir ordenes desde los dispositivos
  moviles. Al recibir una consulta, va a encolarla en RMQ y va
  a esperar a una respuesta desde RMQ.
- **Worker**. Es un procesador de tareas. Esta escuchando constantemente
  para nuevos comandos desde el servidor y desde los dispositivos moviles
  en las colas correspondientes de RabbitMQ.

## Comunicacion por RabbitMQ

RabbitMQ se eligio como medio de transporte ya que garantiza la entrega
de mensajes hasta si uno de los participantes no esta disponible en el
momento de envio. En .NET, usando WCF, es posible user RMQ como un
proveedor de transporte sin tener que configurar muchas cosas. En Python
tenemos que gestionar las colas manualmente. Por lo cual, lo que
terminamos teniendo son dos servidores de RMQ. Uno que va instalado en
el servidor web (RMQWS) y otro que va instalado en la RPI (RMQRPI).

La comunicacion entre esos dos servidores funciona a traves de un plugin
de RMQ llamado Shovel (https://www.rabbitmq.com/shovel.html). Shovel
permite especificar dos colas en cualquier sitio y va a recoger los
mensajes de una cola y ponerlos en la otra. Nosotros estamos usando esto
para transferir mensajes en los siguientes casos:

 - de la cola de "SALIDA" de RMQWS a la cola de "ENTRADA" de RMQRPI
 - de la cola de "SALIDA" de RMQRPI a la cola de "ENTRADA" de RMQWS

### Seguridad de RMQ
La seguridad de RMQ se tiene que implementar a base de certificados
al igual en la parte servidor como en la parte cliente. Como la RPI y
el WS nunca en realidad comunican entre si directamente, el unico
sitio donde se tiene que configurar la comunicacion es en el plugin Shovel.

Shovel acepta como credenciales de tipo "login:password", tanto certificados
ya que en realidad para la conexion una una cadena de tipo `amqp://`



