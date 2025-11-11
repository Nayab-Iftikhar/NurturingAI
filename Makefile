.PHONY: test test-cov test-eval clean

# Run all tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=. --cov-report=html --cov-report=term-missing

# Run agent evaluation
test-eval:
	python tests/run_eval.py

# Run all tests and evaluation
test-all: test test-eval

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

