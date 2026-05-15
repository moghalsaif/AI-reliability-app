# Contributing to AI Reliability Lab

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork
3. Install dependencies: `make install`
4. Run tests: `make test`

## Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `make test`
4. Format code: `make format`
5. Submit a pull request

## Code Style

### Python
- Type hints required on all functions
- Use `from __future__ import annotations`
- Follow PEP 8
- Maximum line length: 100 characters

### TypeScript/JavaScript
- Use TypeScript for all new code
- Follow the existing component patterns
- Use Tailwind CSS for styling

## Adding Evaluators

1. Create `packages/evals/src/evaluators/my_evaluator.py`
2. Inherit from `BaseEvaluator`
3. Implement `default_threshold()` and `evaluate()`
4. Register in `packages/evals/src/__init__.py`
5. Add tests

## Adding Benchmarks

1. Create `benchmarks/<category>/my_suite.py`
2. Define test cases
3. Export to JSON
4. Register in `benchmarks/runner.py`

## Commit Messages

- Use present tense: "Add feature" not "Added feature"
- Use imperative mood: "Move cursor to..." not "Moves cursor to..."
- Limit first line to 72 characters

## Testing

- All new features must have tests
- Maintain or improve code coverage
- Integration tests for evaluators

## Questions?

Open an issue or join our discussions.
