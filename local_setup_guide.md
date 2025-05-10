# Local Setup Guide for Running Three Services

This guide will help you run three microservices locally:
1. Auth Service (Port 8000)
2. Supplier Ranking Service (Port 8001)
3. Product/Order Service (Port 8002)

## Prerequisites

- Python 3.8+
- PostgreSQL
- Docker (optional, for Kafka if needed)

## Setup Steps

### 1. Set up your .env file

Create a `.env` file in the root directory with these settings:

```
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-goes-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_NAME=supplier_ranking
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Port Settings
PORT=8001

# Service URLs (pointing to your local services)
AUTH_SERVICE_URL=http://localhost:8000
ORDER_SERVICE_URL=http://localhost:8002/api/order
WAREHOUSE_SERVICE_URL=http://localhost:8003/api/warehouse
PRODUCT_SERVICE_URL=http://localhost:8002/api/product

# Kafka Settings (if using)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SUPPLIER_EVENTS_TOPIC=supplier-events
KAFKA_RANKING_EVENTS_TOPIC=ranking-events
KAFKA_CONSUMER_GROUP_ID=ranking-service-group
KAFKA_INTEGRATION_EVENTS_TOPIC=integration-events
```

### 2. Setup the Database

Create a PostgreSQL database:

```bash
createdb supplier_ranking
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Running the Supplier Ranking Service

Use the run script to start the service on port 8001:

```bash
python run_ranking_service.py
```

Alternatively, use the Django command:

```bash
python manage.py runserver 0.0.0.0:8001
```

### 5. Running the Other Services

Set up and run your other services similarly, configuring them to use ports 8000 and 8002:

#### Auth Service (Port 8000)
Navigate to your auth service directory and run:
```bash
python manage.py runserver 0.0.0.0:8000
```

#### Product/Order Service (Port 8002)
Navigate to your product service directory and run:
```bash
python manage.py runserver 0.0.0.0:8002
```

## Verifying the Setup

Once all services are running, verify they can communicate with each other:

1. Access the supplier ranking service at http://localhost:8001
2. Test the API endpoints to ensure they're correctly communicating with the other services

## Troubleshooting

- If services can't communicate, check your firewall settings
- Verify PostgreSQL is running and accessible with your credentials
- If you're using Kafka, ensure it's properly configured and running 