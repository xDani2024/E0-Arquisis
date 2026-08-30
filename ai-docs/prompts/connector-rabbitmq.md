# Declaración de uso de inteligencia artificial: connector RabbitMQ

## Prompt realizado

> Ahora quiero implementar el connector. Entiendo que este servicio funciona como la conexión entre RabbitMQ y la API master: recibe desde RabbitMQ los eventos de demanda y los envía mediante HTTP POST al endpoint /events, para que luego sean almacenados en PostgreSQL. ¿Es correcto? Si es así, ayúdame a implementarlo en Python considerando la conexión segura, la confirmación de mensajes y la reconexión automática si RabbitMQ deja de estar disponible.

## Herramienta utilizada

ChatGPT, modelo de OpenAI.

## Respuesta y apoyo recibido

La herramienta confirmó que el servicio `connector` funciona como intermediario entre RabbitMQ y la API `master`. Su función es consumir los eventos de demanda disponibles en la cola asignada y enviarlos mediante una solicitud HTTP POST al endpoint `/events`, donde son validados y almacenados en PostgreSQL.

Se propuso el siguiente flujo:

```text
Central de eventos → RabbitMQ → cola observer.X.q → connector → POST /events → master → PostgreSQL
```

A partir de este flujo, se generó una propuesta para implementar `connector/main.py` en Python utilizando las bibliotecas Pika y Requests. La solución considera una conexión cifrada con RabbitMQ, el procesamiento controlado de los mensajes y la reconexión automática ante interrupciones.

## Código generado con apoyo de IA

El contenido inicial de `connector/main.py` fue propuesto completamente por ChatGPT. La propuesta incluye:

* Lectura de credenciales y parámetros mediante variables de entorno.
* Validación de las variables requeridas antes de iniciar la conexión.
* Conexión cifrada con RabbitMQ mediante TLS y el puerto 5671.
* Uso de `pika.BlockingConnection` para mantener una conexión activa con RabbitMQ.
* Consumo de la cola asignada mediante `basic_consume`.
* Conversión del mensaje recibido desde texto JSON a un objeto Python.
* Envío del evento hacia `POST /events` mediante `requests.post`.
* Confirmación del mensaje mediante `basic_ack` después de una respuesta exitosa de `master`.
* Uso de `basic_nack` con reencolado cuando `master` no responde o presenta un error temporal.
* Tratamiento de eventos duplicados cuando `master` responde con estado HTTP 409.
* Reintento de conexión con RabbitMQ cada cinco segundos después de una desconexión.
* Registro de la actividad y de los errores mediante `logging`.
* Creación de un archivo de estado para utilizarlo posteriormente en el `HEALTHCHECK` del contenedor.

## Decisiones propuestas por la IA

ChatGPT propuso las siguientes decisiones de implementación:

1. Procesar un mensaje a la vez mediante `prefetch_count=1`.
2. Confirmar cada mensaje solamente después de recibir una respuesta de `master`.
3. Reencolar el mensaje cuando se produzca un error temporal de comunicación.
4. No declarar ni modificar la cola o el exchange, debido a que estos elementos son administrados por el curso.
5. Considerar el estado HTTP 409 como un evento previamente almacenado y confirmar su procesamiento.
6. Establecer un tiempo máximo de diez segundos para cada solicitud HTTP realizada a `master`.
7. Mantener un ciclo de reconexión para que el servicio no termine permanentemente ante una caída de RabbitMQ.
8. Validar el contenido recibido como JSON antes de enviarlo a la API.
9. Registrar los errores de conexión y procesamiento para facilitar su revisión.

## Fuentes técnicas consultadas

La propuesta fue elaborada considerando:

* El enunciado de la Entrega 0 de EnergyShark.
* La documentación oficial de Pika sobre `BlockingConnection`, consumo de mensajes, confirmaciones y parámetros de conexión.
* La documentación oficial de Requests sobre solicitudes HTTP POST, envío de objetos JSON, excepciones y tiempos máximos de espera.

Referencias:

* [Documentación oficial de Pika](https://pika.readthedocs.io/)
* [Guía oficial de Requests](https://requests.readthedocs.io/en/latest/user/quickstart/)

## Alcance de la intervención

El código no fue copiado de una solución del curso ni de otro estudiante. Fue generado por ChatGPT específicamente para esta entrega, considerando el enunciado y la arquitectura previamente implementada en `master`.

La propuesta se encuentra pendiente de ejecución, revisión y pruebas por parte de la estudiante. Las credenciales reales de RabbitMQ no fueron incorporadas en la conversación ni en este documento.
