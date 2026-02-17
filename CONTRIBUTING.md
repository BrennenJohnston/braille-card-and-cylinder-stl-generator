# Contributing

Thanks for your interest in contributing. Here's how to get set up.

## Getting started

1. Fork the repo and clone it:

```bash
git clone https://github.com/<YOUR-USERNAME>/braille-card-and-cylinder-stl-generator.git
cd braille-card-and-cylinder-stl-generator
```

2. Set up a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

4. Start the dev server:

```bash
python backend.py
```

Open [http://localhost:5001](http://localhost:5001).

## Making changes

Use descriptive branch names (`feature/add-hexagonal-dots`, `fix/cylinder-overflow`, `docs/update-guides`).

Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages:

```
feat(geometry): add hexagonal dot shape option
fix(translation): correct Grade 2 contraction handling
docs(api): update endpoint documentation
```

Before submitting a PR:

```bash
pytest
ruff check .
ruff format .
```

## Code style

**Python:** PEP 8 enforced by ruff. Use type hints. Max 120 characters. Single quotes for strings.

**JavaScript:** ES6+. Document complex logic.

**Architecture:** Read the relevant specification docs in `docs/specifications/` before changing how a feature works. The two HTML files (`public/index.html` and `templates/index.html`) must stay in sync.

## Testing

```bash
pytest                        # All tests
pytest tests/test_smoke.py    # Smoke tests
pytest tests/test_golden.py   # Golden file regression tests
```

## Accessibility

This project targets WCAG 2.1 Level AA. For UI changes:

1. Run the W3C HTML Validator (target: 0 errors)
2. Run Lighthouse accessibility audit (target: 100/100)
3. Check color contrast ratios

See `docs/development/ADA_ACCESSIBILITY_VALIDATION_SOP.md` for details.

## Questions?

Search existing issues first, then open a new one with the `question` label.
