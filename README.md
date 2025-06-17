# Serj Consumer

Serj Consumer is a FastAPI based service that acts as a voice bot for table reservations. It consumes booking tasks from RabbitMQ, fetches booking details from PostgreSQL, tries to book a table via the web parser and communicates with the customer through a WebSocket connection using speech-to-text and text-to-speech models.

## Project structure

```
.
├── app.py                # FastAPI application with WebSocket endpoint
├── config.py             # Configuration loaded from environment variables
├── voice_bot/            # ASR/TTS/LLM models and service helpers
│   ├── models.py
│   └── services.py
├── utils/                # Helper utilities
│   ├── db_connection.py  # Async PostgreSQL access
│   ├── logger.py
│   ├── process_queue.py  # RabbitMQ consumers
│   └── request.py        # Send booking status to backend
├── parsing/              # Selenium based web booking
│   └── booking.py
├── Dockerfile            # Container build definition
├── requirements.txt      # Python dependencies
└── drone.yaml            # CI pipeline sample
```

## Web API

The application exposes a single WebSocket endpoint:

- `GET /ws` – exchange audio messages with the bot. The server pulls booking information from the queue and starts a conversation. Audio messages are sent and received as binary frames.

## Background tasks

On startup the service launches a background consumer for the `pars_queue`. Messages from this queue trigger the Selenium parser to try booking a table automatically. If successful, the booking status is reported back to the backend.

## Environment variables

The service expects the following variables to be defined (usually via a `.env` file):

| Variable | Purpose |
|----------|---------|
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_HOST` | PostgreSQL host |
| `PG_PORT` | PostgreSQL port |
| `POSTGRES_DB` | PostgreSQL database name |
| `USERNAME_QUEUE` | RabbitMQ username |
| `PASSWORD_QUEUE` | RabbitMQ password |
| `RABBITMQ_HOST` | RabbitMQ host |
| `RABBITMQ_PORT` | RabbitMQ port |
| `BOOKING_SUCCESS_STATE` | Status string used when a booking succeeds |
| `BOOKING_FAILURE_STATE` | Status string used when a booking fails |
| `CALL_QUEUE` | Name of the queue with new calls |
| `PARS_QUEUE` | Name of the queue for parser tasks |
| `GROQ_TOKEN` | API token for the Groq LLM service |

At runtime `TOKENIZERS_PARALLELISM=false` is set automatically to avoid warnings from the transformers library.

## Running locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Provide a `.env` file with the variables listed above.
3. Start the application:
   ```bash
   python app.py
   ```
   The server will listen on `0.0.0.0:8080`.

Alternatively, build and run via Docker:

```bash
docker build -t serj-consumer .
docker run --env-file .env -p 8080:8080 serj-consumer
```

## License

This project is provided without a specific license.

