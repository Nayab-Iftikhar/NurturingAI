# Testing and Evaluation Guide

This document describes the testing and evaluation framework for NurturingAI.

## Overview

The project includes:
- **Unit/Integration Tests**: Comprehensive test suite using Pytest
- **Agent Evaluation**: DeepEval-based evaluation of the LangGraph agent
- **Test Coverage**: Coverage reports for all components

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# API workflow tests
pytest tests/test_api_workflow.py

# Document ingestion tests
pytest tests/test_document_ingestion.py

# Text-to-SQL tests
pytest tests/test_text_to_sql.py

# Document RAG tests
pytest tests/test_document_rag.py

# Integration tests
pytest tests/test_integration.py
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
```

Coverage reports will be generated in `htmlcov/index.html`

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_api_workflow.py::TestAuthenticationAPI

# Run a specific test function
pytest tests/test_api_workflow.py::TestAuthenticationAPI::test_register_user
```

## Agent Evaluation

### Running Agent Evaluation

The agent evaluation uses DeepEval to assess the LangGraph agent's performance on various metrics:

```bash
# Using pytest
pytest tests/test_agent_evaluation.py -v

# Using the dedicated evaluation script
python tests/run_eval.py
```

### Evaluation Metrics

The evaluation measures:

1. **Answer Relevancy**: How relevant the agent's response is to the query
2. **Faithfulness**: How faithful the response is to the source documents
3. **Contextual Relevancy**: How well the response uses the provided context
4. **Tool Selection Accuracy**: Whether the agent selects the correct tool (Text-to-SQL vs Document RAG)

### Evaluation Results

Results are saved to `agent_evaluation_scores.json` with the following structure:

```json
{
  "evaluation_date": "2025-01-XX...",
  "total_test_cases": 4,
  "summary": {
    "average_relevancy": 0.85,
    "average_faithfulness": 0.90,
    "average_contextual_relevancy": 0.88,
    "tool_accuracy": 1.0
  },
  "results": [
    {
      "test_case_number": 1,
      "input": "...",
      "actual_output": "...",
      "expected_output": "...",
      "expected_tool": "document_rag",
      "actual_tool": "document_rag",
      "tool_match": true,
      "metrics": {
        "relevancy": {
          "score": 0.85,
          "success": true,
          "reason": "..."
        },
        ...
      }
    }
  ]
}
```

## Test Structure

### Test Files

- `tests/test_api_workflow.py`: Tests for all API endpoints
- `tests/test_document_ingestion.py`: Tests for document upload and processing
- `tests/test_text_to_sql.py`: Tests for Text-to-SQL functionality
- `tests/test_document_rag.py`: Tests for Document RAG retrieval
- `tests/test_integration.py`: End-to-end integration tests
- `tests/test_agent_evaluation.py`: DeepEval evaluation tests
- `tests/run_eval.py`: Standalone evaluation script

### Fixtures

Common fixtures are defined in `tests/conftest.py`:
- `test_user`: Creates a test user
- `authenticated_client`: Django test client with authenticated user
- `api_client`: API client with JWT token
- `sample_lead_data`: Sample lead data for testing
- `sample_pdf_file`: Sample PDF file for testing
- `temp_chromadb_dir`: Temporary ChromaDB directory

## Requirements

### Environment Variables

Some tests require API keys:
- `OPENAI_API_KEY`: For OpenAI LLM (optional, falls back to Ollama)
- `OLLAMA_BASE_URL`: For Ollama LLM (optional, defaults to http://localhost:11434)

Tests that require LLM will be skipped if no API key is available.

### Dependencies

All testing dependencies are listed in `requirements.txt`:
- `pytest>=7.0.0`
- `pytest-django>=4.5.0`
- `pytest-cov>=4.0.0`
- `pytest-mock>=3.10.0`
- `deepeval>=0.17.0`
- `reportlab>=4.0.0`

## Continuous Integration

To run tests in CI/CD:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=. --cov-report=xml

# Run evaluation
python tests/run_eval.py
```

## Troubleshooting

### Tests Failing Due to Missing API Keys

If tests are skipped due to missing API keys, set them in your environment:

```bash
export OPENAI_API_KEY="your-key-here"
# or ensure Ollama is running locally (defaults to http://localhost:11434)
```

### ChromaDB Lock Issues

If you encounter ChromaDB lock issues, ensure no other processes are using the database:

```bash
# Kill any running Django processes
pkill -f "python.*manage.py"
```

### Import Errors

If you encounter import errors, ensure you're in the project root and the virtual environment is activated:

```bash
cd /path/to/NurturingAI
source .venv/bin/activate
```

