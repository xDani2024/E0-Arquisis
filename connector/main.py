import json
import logging
import os
import ssl
import time
from pathlib import Path

import pika
import requests


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5671"))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE")
MASTER_URL = os.getenv("MASTER_URL")

HEALTH_FILE = Path("/tmp/connector_healthy")


def validate_environment():
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
    ssl_context = ssl.create_default_context()

    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )

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
        blocked_connection_timeout=30,
    )

    return pika.BlockingConnection(parameters)


def process_message(channel, method, properties, body):
    try:
        event = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.exception("Invalid JSON received from RabbitMQ")

        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )
        return

    try:
        response = requests.post(
            MASTER_URL,
            json=event,
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("Could not communicate with master")

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

        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )
        return

    if response.status_code == 409:
        logger.info("Duplicate event already stored")

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

        channel.basic_ack(
            delivery_tag=method.delivery_tag
        )
        return

    logger.error(
        "Master returned status %s",
        response.status_code,
    )

    channel.basic_nack(
        delivery_tag=method.delivery_tag,
        requeue=True,
    )


def consume_events():
    validate_environment()

    while True:
        connection = None

        try:
            HEALTH_FILE.touch()

            logger.info(
                "Connecting to RabbitMQ at %s:%s",
                RABBITMQ_HOST,
                RABBITMQ_PORT,
            )

            connection = create_rabbitmq_connection()
            channel = connection.channel()

            channel.basic_qos(prefetch_count=1)

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
            if connection is not None and connection.is_open:
                connection.close()


if __name__ == "__main__":
    consume_events()