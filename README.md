# MentorMuni API

MentorMuni is an AI-driven mentorship platform. This API is built using FastAPI and is designed to be scalable and extensible.

## Features
- AI text generation using OpenAI's GPT-5.2
- Health check endpoint
- Environment-based configuration
- Centralized logging

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```

2. Navigate to the project directory:
   ```bash
   cd MentorMuniAPI
   ```

3. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file based on `.env.example` and add your OpenAI API key.

6. Run the application:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

7. Access the API documentation at:
   ```
   http://127.0.0.1:8000/docs
   ```