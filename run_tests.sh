#!/bin/bash
# Quick script to run all tests and evaluation

set -e

echo "=========================================="
echo "Running NurturingAI Test Suite"
echo "=========================================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo ""
echo "1. Running unit and integration tests..."
pytest tests/ -v --tb=short

echo ""
echo "2. Running tests with coverage..."
pytest --cov=. --cov-report=term-missing --cov-report=html

echo ""
echo "3. Running agent evaluation..."
if [ -z "$OPENAI_API_KEY" ] && [ -z "$OLLAMA_BASE_URL" ]; then
    echo "WARNING: No LLM API key found. Skipping evaluation."
    echo "Set OPENAI_API_KEY or ensure Ollama is running (OLLAMA_BASE_URL) to run evaluation."
else
    python tests/run_eval.py
fi

echo ""
echo "=========================================="
echo "Test Suite Complete!"
echo "=========================================="
echo "Coverage report: htmlcov/index.html"
echo "Evaluation results: agent_evaluation_scores.json"

