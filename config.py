import os
from dotenv import load_dotenv

load_dotenv()

# Postgres
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_host = os.getenv("POSTGRES_HOST")
postgres_port = os.getenv("PG_PORT")
postgres_db = os.getenv("POSTGRES_DB")

# RabbitMQ: строим URL из отдельных переменных
rabbitmq_user = os.getenv("USERNAME_QUEUE")
rabbitmq_pass = os.getenv("PASSWORD_QUEUE")
rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
rabbitmq_port = os.getenv("RABBITMQ_PORT", "5672")

rabbitmq_url = (
    f"amqp://{rabbitmq_user}:{rabbitmq_pass}@{rabbitmq_host}:{rabbitmq_port}/"
)

# Имена очередей
call_queue = os.getenv("CALL_QUEUE")
pars_queue = os.getenv("PARS_QUEUE")
