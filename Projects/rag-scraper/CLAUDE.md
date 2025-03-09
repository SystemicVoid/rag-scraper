# RAG Scraper - Development Guidelines

## Build & Development Commands
- Setup: `pip install -e ".[dev]"`
- Run: `python -m rag_scraper.cli --domain example.com --output-dir ./data`
- Format: `black . && isort .`
- Lint: `flake8 .`
- Type Check: `mypy .`
- Test: `pytest`
- Single Test: `pytest tests/path/to/test_file.py::test_function_name -v`

## Code Style
- Python: 3.12+
- Formatting: Black (88 char line length)
- Imports: isort with Black profile
- Type hints: Required and checked with mypy
- Docstrings: Google style with Args/Returns
- Error handling: Use try/except with specific exceptions and logging
- Naming: snake_case for variables/functions, PascalCase for classes
- Logging: Use loguru instead of print statements
- Dependencies: Maintain in pyproject.toml with clear version constraints
- Classes: Add descriptive docstrings for each class and method