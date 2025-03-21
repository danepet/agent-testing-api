# AI Agent Testing API

A comprehensive API service for testing AI Agents with automated validations. This API allows you to execute test cases against Salesforce AI Agents and validate their responses using multiple validation techniques.

## Features

- Execute batches of tests against Salesforce AI Agents
- Multiple validation types (contains, not_contains, regex, answer_relevancy, contextual_relevancy, faithfulness)
- Content scraping for validating external links
- Real-time test execution status monitoring
- Comprehensive test results with validation details
- Queued batch processing with concurrency control
- Metrics and monitoring endpoints
- Admin interface for system management
- Database persistence for test results

## Architecture

![Architecture Diagram](docs/architecture.png)

The system consists of the following main components:

- **API Server**: FastAPI application that exposes RESTful endpoints for test execution, monitoring, and results retrieval
- **Database**: Stores test configurations, results, and metrics
- **Task Queue**: Manages concurrent test executions with configurable concurrency limits
- **Agent Service**: Communicates with Salesforce AI Agents using their API
- **Validation Service**: Validates agent responses using multiple validation techniques
- **Scraper Service**: Extracts content from URLs in agent responses for contextual validation

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Docker (optional)

### Local Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/ai-agent-testing.git
   cd ai-agent-testing
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your configuration settings.

5. Create the database:
   ```bash
   # Create a PostgreSQL database
   createdb ai_agent_testing
   
   # Run database migrations
   alembic upgrade head
   ```

6. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Installation

1. Build and start the Docker containers:
   ```bash
   docker-compose up -d
   ```

## Usage

The API provides several endpoints for test execution, monitoring, and results retrieval.

### Authentication

All API endpoints require authentication using a JWT token.

```bash
# Get an auth token
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=password"
```

This will return a token that should be used in subsequent requests:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Executing Tests

To execute a batch of tests:

```bash
curl -X POST "http://localhost:8000/api/v1/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "my-batch",
    "tests": [
      {
        "test_id": "test-1",
        "turns": [
          {
            "turn_id": "turn-1",
            "order": 1,
            "user_input": "Hello, can you help me troubleshoot my wifi connection?",
            "validations": [
              {
                "validation_id": "validation-1",
                "validation_type": "contains",
                "validation_parameters": {
                  "text": "WiFi",
                  "case_sensitive": false
                }
              },
              {
                "validation_id": "validation-2",
                "validation_type": "answer_relevancy",
                "validation_parameters": {
                  "threshold": 0.7
                }
              }
            ]
          }
        ],
        "credentials": {
          "sf_org_domain": "https://my-org.my.salesforce.com",
          "sf_client_id": "CLIENT_ID",
          "sf_client_secret": "CLIENT_SECRET",
          "sf_agent_id": "AGENT_ID"
        },
        "config": {
          "html_selector": "main",
          "timeout_seconds": 30
        }
      }
    ]
  }'
```

This will return a job ID that can be used to check the status and results:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Batch execution queued with 1 tests"
}
```

### Checking Test Status

To check the status of a test execution:

```bash
curl -X GET "http://localhost:8000/api/v1/status/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

This will return the current status of the job:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_id": "my-batch",
  "status": "running",
  "started_at": "2023-06-06T12:34:56",
  "progress": 50,
  "total_tests": 1,
  "completed_tests": 0,
  "failed_tests": 0,
  "current_test_id": "test-1",
  "current_turn": 1
}
```

### Getting Test Results

To get the results of a completed test execution:

```bash
curl -X GET "http://localhost:8000/api/v1/results/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

This will return detailed results for the test execution:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_id": "my-batch",
  "status": "completed",
  "started_at": "2023-06-06T12:34:56",
  "completed_at": "2023-06-06T12:35:30",
  "total_tests": 1,
  "completed_tests": 1,
  "failed_tests": 0,
  "total_validations": 2,
  "passed_validations": 2,
  "failed_validations": 0,
  "pass_rate": 100.0,
  "avg_response_time": 752.0,
  "test_results": [
    {
      "test_id": "test-1",
      "status": "completed",
      "started_at": "2023-06-06T12:34:56",
      "completed_at": "2023-06-06T12:35:30",
      "error": null,
      "total_validations": a2,
      "passed_validations": 2,
      "failed_validations": 0,
      "pass_rate": 100.0,
      "avg_response_time": 752.0,
      "turn_results": [
        {
          "turn_id": "turn-1",
          "order": 1,
          "user_input": "Hello, can you help me troubleshoot my wifi connection?",
          "agent_response": "I'd be happy to help you troubleshoot your WiFi connection issues. Let's start with some basic steps...",
          "scraped_content": null,
          "response_time_ms": 752,
          "validations_total": 2,
          "validations_passed": 2,
          "validations_failed": 0,
          "validation_results": [
            {
              "validation_id": "validation-1",
              "validation_type": "contains",
              "is_passed": true,
              "score": 1.0,
              "details": {
                "type": "contains",
                "passed": true,
                "score": 1.0,
                "details": "Expected text found in response"
              }
            },
            {
              "validation_id": "validation-2",
              "validation_type": "answer_relevancy",
              "is_passed": true,
              "score": 0.89,
              "details": {
                "type": "answer_relevancy",
                "passed": true,
                "score": 0.89,
                "details": "Response is relevant to the query"
              }
            }
          ]
        }
      ]
    }
  ],
  "error": null
}
```

### Monitoring

The API provides several endpoints for monitoring the system:

```bash
# Get health status
curl -X GET "http://localhost:8000/api/v1/health"

# Get metrics (Prometheus format)
curl -X GET "http://localhost:8000/api/v1/metrics"

# Get queue status
curl -X GET "http://localhost:8000/api/v1/queue/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Admin Interface

Admin endpoints are available for system management:

```bash
# Get server status
curl -X GET "http://localhost:8000/api/v1/admin/status" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update a setting
curl -X POST "http://localhost:8000/api/v1/admin/settings" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LOG_LEVEL",
    "value": "DEBUG"
  }'

# Restart the task queue
curl -X POST "http://localhost:8000/api/v1/admin/restart-queue" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Configuration

The application can be configured using environment variables or a `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_USERNAME` | Admin username | `admin` |
| `API_PASSWORD` | Admin password | `password` |
| `SECRET_KEY` | Secret key for JWT encoding | `your-secret-key-here` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://postgres:postgres@localhost:5432/ai_agent_testing` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format (`json` or `standard`) | `json` |
| `MAX_CONCURRENT_JOBS` | Maximum concurrent test executions | `10` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per client | `60` |
| `DEFAULT_TIMEOUT_SECONDS` | Default timeout for operations | `60` |
| `SF_AGENT_TIMEOUT_SECONDS` | Timeout for Salesforce Agent API requests | `30` |

## Validation Types

The system supports multiple validation types:

### Basic Validations

- **contains**: Checks if the response contains specified text
  ```json
  {
    "text": "example text",
    "case_sensitive": true
  }
  ```

- **not_contains**: Checks if the response does not contain specified text
  ```json
  {
    "text": "example text",
    "case_sensitive": true
  }
  ```

- **regex**: Checks if the response matches a regular expression
  ```json
  {
    "pattern": "\\d{3}-\\d{2}-\\d{4}",
    "expected_match": true
  }
  ```

### Advanced Validations

- **answer_relevancy**: Checks if the response is relevant to the query
  ```json
  {
    "threshold": 0.7
  }
  ```

- **contextual_relevancy**: Checks if the response is relevant to the provided context
  ```json
  {
    "context": "Context information...",
    "threshold": 0.7
  }
  ```

- **faithfulness**: Checks if the response is faithful to the provided context
  ```json
  {
    "context": "Context information...",
    "threshold": 0.7
  }
  ```

## Development

### Project Structure

```
ai-agent-testing/
├── alembic/              # Database migrations
├── app/                  # Application code
│   ├── api/              # API endpoints
│   │   ├── v1/           # API version 1
│   │   │   ├── endpoints/  # API endpoint implementations
│   ├── core/             # Core functionality
│   ├── db/               # Database models and repositories
│   ├── models/           # Pydantic models
│   ├── services/         # Business logic services
│   ├── utils/            # Utility functions
│   └── main.py           # Application entry point
├── logs/                 # Log files
├── tests/                # Test code
├── .env.example          # Example environment variables
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile            # Docker configuration
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Run migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

## Deployment

### Docker Deployment

The simplest way to deploy the application is using Docker Compose:

```bash
# Build and start containers
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Kubernetes Deployment

For production deployments, we recommend using Kubernetes. Sample Kubernetes manifests are available in the `kubernetes/` directory.

```bash
# Apply Kubernetes manifests
kubectl apply -f kubernetes/
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please contact [support@example.com](mailto:support@example.com).