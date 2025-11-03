# Contributing to Equitas

Thank you for your interest in contributing to Equitas! Please read these guidelines before submitting contributions.

## Code Style

**Read [CODE_STYLE.md](CODE_STYLE.md) for complete code style guidelines.**

### Critical Rules

1. **NO EMOJIS** - Emojis are strictly prohibited in all code, documentation, and messages
2. Follow PEP 8 Python style guide
3. Use type hints for all functions
4. Write comprehensive docstrings
5. Include tests for new features

## Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/Equitas.git`
3. Install dependencies: `pip install -e ".[dev]"`
4. Install pre-commit hooks: `pre-commit install`
5. Create a branch: `git checkout -b feature/your-feature-name`

## Making Changes

1. Write code following the style guidelines
2. Add tests for new functionality
3. Update documentation as needed
4. Run linters: `ruff check .` and `black .`
5. Run tests: `pytest`
6. Ensure all checks pass

## Submitting Changes

1. Commit your changes with clear messages:
   ```
   Add feature: credit transaction history
   
   Implement database model and API endpoints for tracking
   credit transactions with pagination support.
   ```

2. Push to your fork: `git push origin feature/your-feature-name`
3. Create a Pull Request on GitHub
4. Ensure CI checks pass
5. Respond to review feedback

## Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Include tests for new features
- Update documentation
- Reference related issues
- Ensure CI checks pass

## Reporting Issues

When reporting bugs or requesting features:

- Use clear, descriptive titles
- Provide reproduction steps
- Include relevant code examples
- Specify environment details
- Avoid emojis in issue descriptions

## Code Review Process

1. Maintainers review PRs for:
   - Code style compliance
   - Test coverage
   - Documentation completeness
   - No emojis in code/docs
   - Security considerations

2. Requested changes must be addressed
3. Approval required from at least one maintainer
4. All CI checks must pass

## Questions?

- Check existing documentation
- Review [CODE_STYLE.md](CODE_STYLE.md)
- Open a GitHub Discussion
- Contact maintainers

Thank you for contributing to Equitas!

