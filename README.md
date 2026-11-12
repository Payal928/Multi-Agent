# Multi-Agent Chat Application

This project is a Flask-based multi-agent conversational application built with LangGraph and Google Gemini. It routes each user query to the most suitable agent based on the request type:

- Researcher
- Analyst
- Writer
- General assistant

The app also includes guardrails for input validation before routing the request to the appropriate agent.

## Project Overview

The application workflow is:

1. User sends a message through the Flask API.
2. Input guardrails validate the message.
3. If the message contains sensitive PII, it is redacted or flagged.
4. If prompt injection is detected, the request is blocked.
5. A supervisor model selects the best agent.
6. The selected agent generates the final response.

## Tech Stack

- Python 3.11
- Flask
- LangGraph
- Google Gemini API
- Guardrails AI
- Docker

## Guardrails Used

This project uses two main guardrails:

### 1. PII Detection
The app checks for sensitive user information such as:

- email addresses
- phone numbers
- names/people
- credit card numbers

It uses Guardrails AI PII detection and redacts or flags detected content before continuing.

### 2. Prompt Injection Detection
The app checks whether the input contains prompt-injection attempts, malicious instructions, or manipulative prompt patterns. If detected, the request is blocked.

## Folder Structure

```text
multi_agent/
├── app.py
├── multi_agent.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
├── .dockerignore
├── .gitignore
├── templates/
│   └── index.html
└── README.md
```

## Environment Variables

Create a `.env` file in the project root with the following:

```env
GEMINI_API_KEY=your_api_key_here
```

Important:
- Do not commit `.env` to GitHub.
- Keep your API key secret.

## Run Locally Without Docker

1. Create and activate a virtual environment:

```bash
python -m venv venv
```

On Windows:

```bash
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

2. Install requirements:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

4. Open the app in the browser:

```text
http://localhost:5000
```

## Build and Run With Docker

From the project folder:

```bash
docker build -t payalbabar/multi-agent-app:latest .
docker run -d -p 5000:5000 --name multi-agent-app -e GEMINI_API_KEY=your_api_key_here payalbabar/multi-agent-app:latest
```

Then open:

```text
http://localhost:5000
```

## Pull the Docker Image from Docker Hub

You can pull the image directly from Docker Hub using:

```bash
docker pull payalbabar/multi-agent-app:latest
```

Then run it:

```bash
docker run -d -p 5000:5000 --name multi-agent-app -e GEMINI_API_KEY=your_api_key_here payalbabar/multi-agent-app:latest
```

## Docker Compose Setup

If you want to use Docker Compose:

```yaml
services:
  multi-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: multi-agent-app
    ports:
      - "5000:5000"
    env_file:
      - .env
    environment:
      OTEL_SDK_DISABLED: "true"
      PYTHONUNBUFFERED: "1"
      GEMINI_API_KEY: ${GEMINI_API_KEY}
    restart: unless-stopped
```

Run:

```bash
docker compose up --build
```

## Docker Hub Push Example

If you want to push your own image to Docker Hub:

```bash
docker login
docker build -t payalbabar/multi-agent-app:latest .
docker push payalbabar/multi-agent-app:latest
```

## Notes

- This app depends on a valid Gemini API key.
- Do not expose the API key in public repositories.
- Use `.env` and keep it local.
- For Docker usage, pass the key using `-e GEMINI_API_KEY=...` or via `.env` when running Compose.

## License

This project is for learning and demonstration purposes.
