Title:  Readme de protobuf

Author: Borys Makogonyuk Vasylev boris.makogonyuk@gmail.com

Date:   17/05/2017 
  
## Porque estamos usando algun tipo de serializador?
Necesitamos algo que sea mejor que JSON. JSON es leible pero el tamaño
es demasiado grande para los datos que vamos a estar enviando
considerando de que tenemos una conexion celular.

## Porque Protobuf?

Se habian considerado los siguientes:

- [**Thrift** (link)](http://thrift.apache.org/).
    Hace demasiado. No necesitamos que la libreria de serializacion
    tambien se encargue de los protocolos y servicios. A ver.
    Seria perfecto, pero teniendo en cuenta de que estamos usando
    RabbitMQ con Shovel no es viable. **Rechazado**.
- [**MsgPack** (link)](http://msgpack.org/).
    La idea principal de MsgPack es reemplazar JSON en los lugares
    donde el tamaño es importante. Me parecio la mejor opcion, pero
    despues de montar una demo pequeña me di cuenta de que no tiene
    ni esquemas ni ninguna otra manera de definir los datos.
    Como tenemos comunicacion entre diferentes idiomas necesitamos
    garantizar de que objeto mapeado de Python a MsgPack va a ser
    mapeado a un objeto C# sin problemas durante la deserializacion.
    No podemos garantizar eso. **Rechazado**.
- [**Cap'n Proto** (link)](https://capnproto.org).
    Tiene esquemas y soporte para una variedad de idiomas. El problema
    con este es que la implementacion de la libreria de Python esta
    basada en otra libreria C++. Por lo cual cualquier entorno de
    desarollo y produccion va a tener que tener un compilador C++
    ya que no la proporcionan. Me parecio demasiado jaleo y considere
    posibles errores en diferentes plataformas. **Rechazado**.
- **Python Pickles**.
    Su estructura es parecida a un JSON. Es gordo. **Rechazado**.

- [**Protobuf** (link)](https://github.com/google/protobuf).
    Tiene esquemas y librerias para Python y CSharp. Es necesario
    instalar un compilador propio para poder convertir los esquemas en
    codigo para la plataforma necesaria, pero eso no es un problema ya
    que los demas serializadores hacen lo mismo.

## Que es necesario para recompilar los mensajes?

[Guia oficial para Python](https://developers.google.com/protocol-buffers/docs/pythontutorial)


[Guia oficial para CSharp](https://developers.google.com/protocol-buffers/docs/csharptutorial)


### Comentarios
En general, en un entorno de desarollo "limpio" es necesario
instalar el compilador de protobuf `protoc`. La instalacion me parecio
simple en todas las plataformas (Ubuntu / OSX / Windows). Los binarios
estan en el final de la lista de descargas.

### Compilacion
Aqui es donde tengo que decir que el compilador de protobuf es una mierda.
Los namespace son replicados en relacion a las carpetas que se
indican por parametros. Los `import` dentro de los archivos `.proto`
apuntan de una forma relativa y eso es como terminan generandose los
archivos con codigo. Para que protobuf respete los namespace del proyecto
es necesario hacer lo siguiente (lo que sigue son los contenidos del
archivo `dev_python_gen_proto.sh`:

```
SRC_DIR=protobuf/
DST_DIR=src/
echo $SRC_DIR

protoc $SRC_DIR/innovapos/shared/protocols/messaging.proto \
$SRC_DIR/innovapos/shared/protocols/common.proto \
--proto_path=$SRC_DIR --python_out=$DST_DIR
```

Si uno se fija en la estructura del proyecto vera que la carpeta
`protobuf` tiene replicada la estructura de carpetas de `src`. Esto
se tiene que hacer a propocito para que protobuf no rompa los imports.

Al llamar a `protoc` le indicamos que archivos quemos que nos convierta.
El parametro `protopath` indica que tiene que considerar como la raiz durante
la generacion de codigo deste .proto .
El parametro `python_out` indica a donde tiene que guardar los archivos generados.

**SRC_DIR** esta apuntando a una carpeta que es la carpeta raiz
de la estructura replicada de nuestro proyecto.

**DST_DIR** apunta a la carpeta de la que se replica la estructura,
o sea donde en realidad tenemos el codigo fuente.



