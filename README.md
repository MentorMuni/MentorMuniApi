# MentorMuni API

MentorMuni is an AI-driven mentorship platform. This API is built with FastAPI.

## Features
- Interview / skill / aptitude / AI readiness plan generation (OpenAI)
- Voice interview session + analysis
- Resume ATS scoring
- Health check and environment-based configuration

## Setup

1. Clone the repository and enter the project directory:
   ```bash
   cd MentorMuniAPI
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file from `.env.example` and set `OPENAI_API_KEY`.

4. Run the application (from repo root):
   ```bash
   cd mentormuni-api && PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Open the interactive docs:
   ```
   http://127.0.0.1:8000/docs
   ```
