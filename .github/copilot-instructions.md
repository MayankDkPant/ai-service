# CIRM AI Classification Service - Agent Instructions

## Project Overview
This is a **civic complaint classification microservice** powered by Ollama (local LLM). It routes citizen complaints to appropriate government departments based on text analysis.

**Key Purpose**: Accept raw complaint text → classify into departments (SANITATION, WATER, ELECTRICITY, ROADS, PUBLIC_SAFETY, OTHER) with priority and confidence scoring.

## Architecture

### Component Flow
```
FastAPI endpoint (/classify) → Classifier.classify() → Ollama LLM → JSON extraction → Validator → Response
```

### Core Files
- **[main.py](main.py)**: FastAPI app with `/health` and `/classify` endpoints
- **[classifier.py](classifier.py)**: Core classification logic (prompting, LLM calls, JSON parsing)
- **[validator.py](validator.py)**: Pydantic schema enforcement for classification output

### Data Flow
1. `ComplaintRequest.text` enters via FastAPI
2. Text sanitized (strip + 1000 char limit) in `sanitize_input()`
3. Prompt constructed with strict system instructions (JSON-only output)
4. Ollama LLM called with `temperature=0` for deterministic output
5. Raw response parsed for JSON block using regex
6. Pydantic validates against `ClassificationResponse` schema
7. **Confidence threshold**: If < 0.6, force `department = "OTHER"`
8. Safe fallback returns if any step fails

## Critical Patterns

### Ollama Integration
- Uses local Ollama instance at `http://localhost:11434/api/generate`
- Model: `llama3:8b` (hardcoded in classifier.py line 5)
- **Temperature=0** enforces deterministic output—do NOT increase without testing
- Timeout: 10 seconds
- Response parsing expects JSON within response text (extracts via regex)

### JSON Validation Strategy
- System prompt forces strict JSON format to prevent parsing failures
- `extract_json()` uses regex to isolate JSON object from surrounding text
- Pydantic validates schema **after** JSON extraction—catches malformed fields early
- Confidence threshold (0.6) is business logic, not schema validation

### Error Handling
- All exceptions in `classify()` caught silently → returns safe fallback
- **Intentional silent failure**: Logs not implemented; fails gracefully to prevent service crashes
- When adding features: preserve fallback behavior for production robustness

## Developer Workflow

### Running the Service
```bash
# Terminal 1: Start Ollama (prerequisite)
ollama serve

# Terminal 2: In project directory
python -m fastapi dev main.py
# Service runs at http://localhost:8000
```

### Testing Classification
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "There is a pothole on Main Street"}'
```

### Debugging LLM Output
Add to `classifier.py` (before `extract_json()` call):
```python
print(f"Raw Ollama: {raw_output}")  # See unprocessed LLM response
```

## Project-Specific Conventions

### Strict Constraints
- **Department values** are literal strings (no flexibility). Changing these requires updating: system prompt + validator schema + endpoint docs
- **Confidence range** must be 0.0-1.0 (Pydantic enforces via `Field(ge=0.0, le=1.0)`)
- **Intent field** is hardcoded as "COMPLAINT"—not extracted from LLM (design decision for single-purpose service)

### Adding New Departments
1. Add to `validator.py` Literal type
2. Add to system prompt in `classifier.py`
3. Update FastAPI docs (optional, but recommended)
4. **Test with Ollama** to ensure model recognizes new category

### Extending Classification Features
- **Do NOT** change sanitize_input() logic without impact analysis (affects all requests)
- **Do NOT** modify system prompt formatting—strict JSON parsing depends on current structure
- Add new fields to `ClassificationResponse` schema first, update system prompt second

## External Dependencies
- **Ollama**: Required local service (not containerized in this codebase)
- **FastAPI/Uvicorn**: HTTP framework and ASGI server
- **Pydantic**: Schema validation (already enforcing constraints)
- **Requests**: HTTP calls to Ollama

## Known Limitations
- No request logging/monitoring (silent failures for production stability)
- No rate limiting or authentication
- Ollama service must be running—no fallback if unreachable
- Fixed 10s timeout may be insufficient for complex complaints under load
