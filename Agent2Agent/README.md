# Candidate Extraction Pipeline

Automated recruiting pipeline that extracts candidate information from PDF resumes, matches them against a job description, writes qualified candidates to `interns.txt`, and sends offer emails via Gmail SMTP.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
  │                   LOCAL ENVIRONMENT                     │
  │                                                         │
  │  [candidate/*.pdf]          [job_description.txt]       │
  │           │                           │                 │
  │           └─────────────┬─────────────┘                 │
  │                         ▼                               │
  │                ┌─────────────────┐                      │
  │                │   reader.py     │                      │
  │                │ (Recruiting Agt)│                      │
  │                └────────┬────────┘                      │
  │                         │                               │
  │                         ▼                               │
  │                  [interns.txt]                          │
  │                         │                               │
  │                         ▼                               │
  │                ┌─────────────────┐                      │
  │                │   sender.py     │                      │
  │                │  (Sender Agt)   │                      │
  │                └────────┬────────┘                      │
  └─────────────────────────┼───────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌───────────────┐                       ┌───────────────┐
│  OpenRouter   │                       │  SMTP Server  │
│     API       │                       │ (Port 587/TLS)│
│  (LLM Model)  │                       └───────┬───────┘
└───────────────┘                               │
                                                ▼
                                        ┌───────────────┐
                                        │   Candidate   │
                                        │   Inboxes     │
                                        └───────────────┘
```

## Project Structure

```
pipelines/
├── .env                      # API keys & credentials
├── job_description.txt       # Job requirements text
├── interns.txt               # Generated: matched candidates
├── candidate/                # PDF resumes input
│   ├── databoy.pdf
│   └── jhon.pdf
├── graph.py                  # Main orchestrator (LangGraph)
├── reader.py                 # Candidate extraction agent
├── sender.py                 # Email dispatch agent
├── pyproject.toml
└── README.md
```

## Data Flow

### 1. Input Layer
- **`job_description.txt`** - Plain text job requirements
- **`candidate/*.pdf`** - Resume PDFs (3 files currently)

### 2. Extraction Layer (`reader.py`)
- **Agent**: `build_recruiting_agent()` using `create_deep_agent`
- **Model**: `google/gemini-2.5-flash` via OpenRouter
- **Tools**: 
  - `read_pdf(path)` - Extract text from PDF resumes
  - Built-in: `ls`, `read_file`, `write_file`
- **Output**: `interns.txt` with format `Name - email`

### 3. Dispatch Layer (`sender.py`)
- **Agent**: `build_sender_agent()` using `create_deep_agent`
- **Model**: `google/gemini-2.5-flash` via OpenRouter
- **Tools**:
  - `get_interns_list()` - Reads `interns.txt`
  - `send_email(recipient, subject, body)` - Gmail SMTP
- **Email**: Gmail SMTP (SSL, port 465)

### 4. Orchestration (`graph.py`)
- **LangGraph** StateGraph with 2 nodes
- Sequential execution: `recruiting` → `sender`
- Retry logic with exponential backoff for rate limits

## Configuration (`.env`)

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
SENDER_EMAIL=
SENDER_PASSWORD=
```

## Running the Pipeline

```bash
# Install dependencies
uv sync

# Run the full pipeline
uv run graph.py
```

## Expected Output

1. **`interns.txt`** generated with matched candidates:
```
Jordan Taylor - jordan.taylor@email.com
Jagan K K - jagsonjob@gmail.com
```

2. **Console output** showing email dispatch:
```
[tool] Email sent to jordan.taylor@email.com
[tool] Email sent to jagsonjob@gmail.com
[ai] Internship offer emails have been sent to Jordan Taylor and Jagan K K.
interns.txt generated: True
```

## Rate Limit Handling

Both agents use OpenRouter free tier models with automatic retry:
- Exponential backoff (10s, 20s, 40s...)
- Max 5 retries by default
- Handles HTTP 429 and OpenRouter rate limit errors

## Adding More Candidates

Drop additional PDF files into `candidate/` folder and re-run:
```bash
uv run graph.py
```