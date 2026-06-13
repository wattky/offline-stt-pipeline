# Contributing to Offline STT Pipeline

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/offline-stt-pipeline/offline-stt-pipeline.git
cd offline-stt-pipeline
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

4. Run the development server:
```bash
python run.py --verbose
```

## Running Tests

```bash
pytest tests/ -v
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and small

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Reporting Issues

When reporting issues, please include:
- Operating system and version
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Error messages or logs
