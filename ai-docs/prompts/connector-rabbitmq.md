# Declaración de uso de inteligencia artificial: connector RabbitMQ

## Prompt realizado

> Ahora quiero implementar el connector. Entiendo que este servicio funciona como la conexión entre RabbitMQ y la API master: recibe desde RabbitMQ los eventos de demanda y los envía mediante HTTP POST al endpoint /events, para que luego sean almacenados en PostgreSQL. ¿Es correcto? Si es así, ayúdame a implementarlo en Python considerando la conexión segura, la confirmación de mensajes y la reconexión automática si RabbitMQ deja de estar disponible.

## Herramienta utilizada

ChatGPT, modelo de OpenAI.

## Respuesta IA

La herramienta confirmó que el servicio `connector` funciona como intermediario entre RabbitMQ y la API `master`. Su función es consumir los eventos de demanda disponibles en la cola asignada y enviarlos mediante una solicitud HTTP POST al endpoint `/events`, donde son validados y almacenados en PostgreSQL.

Se propuso el siguiente flujo:

```text
Central de eventos → RabbitMQ → cola observer.X.q → connector → POST /events → master → PostgreSQL
```

A partir de este flujo, se generó una propuesta para implementar `connector/main.py` en Python utilizando las bibliotecas Pika y Requests. La solución considera una conexión cifrada con RabbitMQ, el procesamiento controlado de los mensajes y la reconexión automática ante interrupciones.

## Código generado con apoyo de IA


```python
import json
import logging
import os
import ssl
import time
from pathlib import Path

import pika
import requests


# Configura el formato de los mensajes mostrados en los logs.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

# Obtiene desde el entorno los parámetros privados de RabbitMQ
# y la dirección interna de la API master.
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5671"))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE")
MASTER_URL = os.getenv("MASTER_URL")

# Este archivo es utilizado por el HEALTHCHECK del contenedor
# para comprobar que el proceso connector comenzó a ejecutarse.
HEALTH_FILE = Path("/tmp/connector_healthy")


def validate_environment():
    """Comprueba que todas las variables obligatorias estén configuradas."""

    variables = {
        "RABBITMQ_HOST": RABBITMQ_HOST,
        "RABBITMQ_VHOST": RABBITMQ_VHOST,
        "RABBITMQ_USER": RABBITMQ_USER,
        "RABBITMQ_PASSWORD": RABBITMQ_PASSWORD,
        "RABBITMQ_QUEUE": RABBITMQ_QUEUE,
        "MASTER_URL": MASTER_URL,
    }

    missing = [
        name
        for name, value in variables.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}"
        )


def create_rabbitmq_connection():
    """Crea una conexión AMQP cifrada con RabbitMQ."""

    # Crea una configuración TLS utilizando certificados
    # de autoridades reconocidas por el sistema.
    ssl_context = ssl.create_default_context()

    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )

    # Define los parámetros de conexión con RabbitMQ.
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        ssl_options=pika.SSLOptions(
            ssl_context,
            RABBITMQ_HOST,
        ),
        heartbeat=60,

        # Limita el tiempo de espera cuando RabbitMQ
        # bloquea temporalmente la conexión.
        blocked_connection_timeout=30,
    )

    return pika.BlockingConnection(parameters)


def process_message(channel, method, properties, body):
    """Procesa un mensaje y lo envía a la API master."""

    try:
        event = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.exception("Invalid JSON received from RabbitMQ")

        # El mensaje se confirma para retirarlo de la cola.
        # Reencolar un JSON inválido provocaría un ciclo infinito.
        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )
        return

    try:
        # Envía el evento a master mediante una solicitud HTTP POST.
        response = requests.post(
            MASTER_URL,
            json=event,
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("Could not communicate with master")

        # Si master está temporalmente inaccesible,
        # el evento vuelve a la cola para intentarlo nuevamente.
        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True,
        )
        return

    if response.ok:
        logger.info(
            "Event sent to master with status %s",
            response.status_code,
        )

        # Confirma el mensaje después de que master lo procese.
        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )
        return

    if response.status_code == 409:
        logger.info("Duplicate event already stored")

        # Un evento duplicado ya está almacenado, por lo que
        # no es necesario mantenerlo en la cola.
        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )
        return

    if 400 <= response.status_code < 500:
        logger.error(
            "Master rejected event with status %s: %s",
            response.status_code,
            response.text,
        )

        # Un error de validación no se solucionará reintentando
        # el mismo evento, por lo que se retira de la cola.
        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )
        return

    logger.error(
        "Master returned status %s",
        response.status_code,
    )


    # Los errores del servidor pueden ser temporales.
    # El evento se reencola para procesarlo posteriormente.
    channel.basic_nack(
        delivery_tag=method.delivery_tag,
        requeue=True,
    )


def consume_events():
    """Mantiene activo el consumo de eventos y la reconexión."""
    validate_environment()

    while True:
        connection = None

        try:
            # Crea el archivo utilizado por el HEALTHCHECK.
            HEALTH_FILE.touch()

            logger.info(
                "Connecting to RabbitMQ at %s:%s",
                RABBITMQ_HOST,
                RABBITMQ_PORT,
            )

            connection = create_rabbitmq_connection()
            channel = connection.channel()

            # Procesa un mensaje a la vez para evitar retirar
            # varios eventos antes de confirmar su almacenamiento.
            channel.basic_qos(prefetch_count=1)

            # Registra la función que procesará cada mensaje.
            # auto_ack=False exige confirmar manualmente cada evento.
            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=process_message,
                auto_ack=False,
            )

            logger.info(
                "Waiting for events from queue %s",
                RABBITMQ_QUEUE,
            )

            channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("Connector stopped manually")
            break

        except Exception:
            logger.exception(
                "Connector error. Retrying in 5 seconds"
            )

            time.sleep(5)

        finally:
            # Cierra ordenadamente la conexión si continúa abierta.
            if connection is not None and connection.is_open:
                connection.close()


if __name__ == "__main__":
    consume_events()
```