# Contributing to Braille STL Generator

Thank you for your interest in contributing to the Braille STL Generator! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Please:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/<YOUR-USERNAME>/braille-card-and-cylinder-stl-generator.git
   cd braille-card-and-cylinder-stl-generator
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/BrennenJohnston/braille-card-and-cylinder-stl-generator.git
   ```

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js (for frontend dependencies)
- Git

### Installation

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Install pre-commit hooks**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **Run the development server**:
   ```bash
   python backend.py
   ```

5. **Open** http://localhost:5001 in your browser

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-shape-type`
- `fix/cylinder-generation-error`
- `docs/update-api-documentation`
- `refactor/simplify-geometry-code`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(geometry): add hexagonal dot shape option

fix(translation): correct Grade 2 contraction handling

docs(api): update endpoint documentation
```

## Pull Request Process

1. **Update your fork** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** and commit them

4. **Run tests and linting**:
   ```bash
   pytest
   ruff check .
   ruff format .
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request** on GitHub

### PR Requirements

- [ ] All tests pass
- [ ] Code follows project style guidelines
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages follow conventions
- [ ] PR description explains the changes

## Coding Standards

### Python

- **Style**: Follow PEP 8, enforced by `ruff`
- **Formatting**: Use `ruff format` for consistent formatting
- **Type Hints**: Use type hints for function signatures
- **Line Length**: Maximum 120 characters
- **Quotes**: Single quotes for strings

### JavaScript

- **ES6+**: Use modern JavaScript features
- **Modules**: Use ES modules (`import`/`export`)
- **Comments**: Document complex logic

### Architecture

Before making changes, consult the specification documents:

- `docs/specifications/SPECIFICATIONS_INDEX.md` — Master index
- `docs/specifications/SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md` — Settings reference

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_smoke.py

# Run with coverage
pytest --cov=app
```

### Test Categories

- **Smoke tests**: Basic functionality checks
- **Unit tests**: Individual component tests
- **Golden tests**: Output validation against known-good fixtures

### Writing Tests

- Place tests in the `tests/` directory
- Follow the naming convention `test_*.py`
- Use descriptive test names that explain the expected behavior
- Include both positive and negative test cases

## Documentation

### When to Update Documentation

- Adding new features
- Changing API endpoints
- Modifying configuration options
- Fixing bugs that affect documented behavior

### Documentation Locations

- `README.md` — Project overview and quick start
- `docs/specifications/` — Technical specifications
- `docs/development/` — Development guides
- `docs/deployment/` — Deployment instructions

### Accessibility

This project follows WCAG 2.1 Level AA guidelines. For UI changes:

1. Run W3C HTML Validator (target: 0 errors)
2. Run Lighthouse Accessibility audit (target: 100/100)
3. Verify color contrast ratios

See `docs/development/ADA_ACCESSIBILITY_VALIDATION_SOP.md` for details.

## Questions?

If you have questions or need help:

1. Check existing documentation
2. Search existing issues
3. Open a new issue with the `question` label

Thank you for contributing! 🙏
