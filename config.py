import pika
from dotenv import load_dotenv
import os

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_host = os.getenv("POSTGRES_HOST")
postgres_port = os.getenv("PG_PORT")
postgres_db = os.getenv("POSTGRES_DB")


def connect_queue():

    connection_params = pika.ConnectionParameters(
        host=os.getenv("HOST_QUEUE"),
        port=os.getenv("PORT_QUEUE"),
        virtual_host="/",
        credentials=pika.PlainCredentials(
            username=os.getenv("USERNAME_QUEUE"),
            password=os.getenv("PASSWORD_QUEUE"),
        ),
    )

    connection = pika.BlockingConnection(connection_params)

    channel = connection.channel()
    return channel, connection

call_queue = os.getenv("CALL_QUEUE")
pars_queue = os.getenv("PARS_QUEUE")