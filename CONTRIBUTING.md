# Contributing to groster

Welcome to groster! This project is open source and we welcome contributions from the community. Whether you're here to explore, learn, experiment, or contribute, this guide will help you navigate the contribution process effectively.

## Getting Started

### Prerequisites

- **Python 3.12+**: Latest Python with modern async capabilities
- **Git**: Version control system
- **uv**: Ultra-fast Python package manager

### Development Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sergeyklay/groster.git
   cd groster
   ```

2. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install all dependencies**:
   ```bash
   uv sync --locked --all-packages --all-groups
   ```

4. **Set up environment configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

5. **Verify setup**:
   ```bash
   make test
   ```

## Development Workflow

### Creating a New Feature

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/descriptive-feature-name
   ```

2. **Implement the feature**:

3. **Write comprehensive tests**:
   ```bash
   # Add unit tests
   tests/unit/test_your_feature.py
   ```
4. **Follow coding standards**:
   - Use modern Python 3.12 features and type hints
   - Follow the project's style guide (see [Coding Standards](./docs/coding-standards.md))
   - Use structured logging patterns

5. **Verify quality**:
   ```bash
   make format lint test
   ```

### Bug Fixes

1. **Create a bug fix branch**:
   ```bash
   git checkout -b fix/descriptive-bug-name
   ```

2. **Write regression tests first**:
   - Add tests that would have caught the bug
   - Verify tests fail without the fix

3. **Implement minimal fix**:
   - Keep changes focused on the specific issue
   - Avoid refactoring unrelated code

### Code Quality Requirements

- **Type Hints**: Required for all functions and public APIs
- **Test Coverage**: Minimum 90% overall, 95% for new code
- **Documentation**: Google-style docstrings for all public APIs
- **Formatting**: Code must pass `make format lint`

## Pull Request Process

### Before Submitting

1. **Run quality checks**: `make format lint test`
2. **Verify test coverage**: Ensure new code has appropriate test coverage
3. **Update documentation**: Include docstrings and update relevant docs
4. **Check dependencies**: Use `uv` for all dependency management

### PR Guidelines

1. **Fill out the PR template** completely with clear description
2. **Link related issues** using GitHub keywords (fixes #123)
3. **Keep PRs focused** on a single feature, bug fix, or refactoring
4. **Include examples** for UI changes or new features
5. **Explain complex changes** in the PR description

### PR Review Checklist

- **Architecture**: Follows clean architecture principles
- **Type Safety**: Comprehensive type hints throughout
- **Testing**: New functionality is well-tested
- **Documentation**: Public APIs are documented
- **Performance**: Efficient async patterns and database usage
- **Learning Value**: Demonstrates interesting patterns or techniques

## Code Review Guidelines

### What We Look For

- **Architectural Alignment**: Does it fit clean architecture principles?
- **Code Quality**: Proper type hints, error handling, documentation
- **Test Coverage**: Comprehensive tests with meaningful assertions
- **Async Patterns**: Correct use of async/await and resource management
- **Educational Value**: Does it showcase interesting patterns or techniques?

### Review Process

1. **Technical Review**: Code quality, architecture, performance
2. **Learning Discussion**: What patterns or techniques are demonstrated?
3. **Experimental Value**: How does this contribute to our technology exploration?
4. **Documentation**: Are the changes well-documented and explained?

### Feedback Guidelines

- **Be constructive**: Focus on improvement opportunities
- **Be specific**: Provide concrete suggestions and examples
- **Be educational**: Share knowledge and explain reasoning
- **Be respectful**: Remember this is a learning environment

---

**Happy Contributing!**
