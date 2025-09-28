# Contributing to Second Brain Stack

First off, thank you for considering contributing to Second Brain Stack! It's people like you that make this project a great tool for knowledge management.

## 🌟 How to Contribute

### Types of Contributions

We welcome many different types of contributions:

- **🐛 Bug Reports**: Help us identify and fix issues
- **💡 Feature Requests**: Suggest new functionality or improvements
- **📝 Documentation**: Improve guides, examples, and API docs
- **🔧 Code Contributions**: Fix bugs, add features, optimize performance
- **🧪 Testing**: Write tests, test edge cases, test on different platforms
- **🎨 UI/UX**: Improve interfaces and user experience
- **📊 Performance**: Profile and optimize system performance

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/your-username/second-brain-stack.git
cd second-brain-stack

# Add upstream remote
git remote add upstream https://github.com/original-owner/second-brain-stack.git
```

### 2. Set Up Development Environment

```bash
# Create and activate virtual environment
make setup-dev
source .venv/bin/activate

# Install development dependencies
pip install -e ".[dev,performance,monitoring]"

# Initialize pre-commit hooks
pre-commit install

# Create configuration file
make create-sample-config

# Initialize database
python -m interfaces.cli db init
```

### 3. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or a bugfix branch
git checkout -b bugfix/issue-123
```

## 📋 Development Guidelines

### Code Style

We use several tools to maintain code quality:

```bash
# Format code
make format

# Run linters
make lint

# Type checking
mypy core/ services/ interfaces/ connectors/

# Run tests
make test
```

### Python Code Standards

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Document all public functions and classes
- **Async/Await**: Use async/await for I/O operations
- **Error Handling**: Use specific exception types and meaningful messages

### Example Code Structure

```python
"""Module docstring describing purpose and usage."""

import asyncio
from typing import List, Optional

from core.utils import get_logger
from core.database import DatabaseManager


logger = get_logger(__name__)


class ExampleClass:
    """Class docstring explaining purpose and usage."""
    
    def __init__(self, config: dict) -> None:
        """Initialize with configuration."""
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
    
    async def process_data(self, data: List[str]) -> Optional[dict]:
        """
        Process data and return results.
        
        Args:
            data: List of strings to process
            
        Returns:
            Processed results or None if no data
            
        Raises:
            ValueError: If data format is invalid
        """
        if not data:
            return None
            
        try:
            # Implementation here
            result = {"processed": len(data)}
            self.logger.info("Data processed", count=len(data))
            return result
            
        except Exception as e:
            self.logger.error("Processing failed", error=str(e))
            raise ValueError(f"Invalid data format: {e}") from e
```

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes

Examples:
```
feat(search): add semantic search with embeddings

- Implement sentence transformer integration
- Add vector similarity search
- Update search API to support hybrid queries

Closes #123
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_database.py -v

# Run tests with coverage
pytest --cov=core --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/
```

### Writing Tests

We use pytest with async support:

```python
import pytest
from core.database import DatabaseManager


@pytest.fixture
async def db_manager():
    """Create test database manager."""
    db = DatabaseManager(":memory:")
    await db.create_tables()
    yield db
    # Cleanup happens automatically for in-memory DB


@pytest.mark.asyncio
async def test_document_creation(db_manager):
    """Test document creation and retrieval."""
    from core.database.models import Document
    
    # Create test document
    doc = Document(
        title="Test Document",
        content="Test content",
        source_type="test",
        source_path="/test",
        content_hash="test123"
    )
    
    # Store in database
    created_doc = await db_manager.create_document(doc)
    
    # Verify
    assert created_doc.id is not None
    assert created_doc.title == "Test Document"
    
    # Retrieve and verify
    retrieved_doc = await db_manager.get_document(created_doc.id)
    assert retrieved_doc is not None
    assert retrieved_doc.title == "Test Document"
```

## 🐛 Bug Reports

### Before Submitting

1. **Search existing issues** to avoid duplicates
2. **Update to latest version** to see if bug is already fixed
3. **Test in clean environment** to isolate the issue

### Bug Report Template

```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.5]
- Second Brain Stack: [e.g., 0.1.0]
- Docker: [e.g., 24.0.6] (if applicable)

## Additional Context
- Error messages or logs
- Screenshots (if applicable)
- Configuration files (sanitized)
```

## 💡 Feature Requests

### Before Submitting

1. **Check the roadmap** to see if it's already planned
2. **Search existing requests** to avoid duplicates
3. **Consider the scope** - is it aligned with project goals?

### Feature Request Template

```markdown
## Feature Description
Clear description of the proposed feature

## Use Case
Why is this feature needed? What problem does it solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
Other approaches you've considered

## Additional Context
- Examples from other tools
- Mockups or diagrams
- Implementation ideas
```

## 🎯 Development Focus Areas

### High Priority
- **Vector Search**: Semantic search implementation
- **Knowledge Graph**: Entity extraction and relationships
- **Performance**: Query optimization and caching
- **Documentation**: API docs and user guides

### Medium Priority
- **Web Interface**: Modern FastAPI + HTMX frontend
- **Additional Connectors**: Web scraping, Git analysis
- **Testing**: Increase coverage and add integration tests
- **Monitoring**: Enhanced metrics and alerting

### Help Wanted
- **Mobile Interface**: React Native or Progressive Web App
- **Plugin System**: Architecture for third-party extensions
- **Deployment**: Kubernetes manifests and Helm charts
- **Accessibility**: Screen reader and keyboard navigation support

## 🔄 Pull Request Process

### 1. Preparation

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Update your branch
git checkout your-feature-branch
git rebase main
```

### 2. Pre-submission Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New functionality includes tests
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main branch

### 3. Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Screenshots (if applicable)
Before/after screenshots for UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated and passing
```

### 4. Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Code Review**: Maintainers review code and provide feedback
3. **Discussion**: Address feedback and make requested changes
4. **Approval**: Maintainer approves and merges PR

## 📚 Documentation

### Types of Documentation

- **User Guides**: How to use features from user perspective
- **Developer Guides**: Technical implementation details
- **API Documentation**: Function and endpoint references
- **Tutorials**: Step-by-step learning materials
- **Troubleshooting**: Common issues and solutions

### Documentation Standards

- **Clear Headings**: Use descriptive, hierarchical headings
- **Code Examples**: Include working code examples
- **Screenshots**: Visual aids for UI features
- **Cross-References**: Link related sections
- **Up-to-Date**: Keep docs current with code changes

## 🏆 Recognition

We appreciate all contributors and recognize them in several ways:

- **Contributors File**: All contributors listed in CONTRIBUTORS.md
- **Release Notes**: Significant contributions highlighted in releases
- **GitHub Insights**: Contribution graphs and statistics
- **Community Shoutouts**: Recognition in discussions and social media

## ❓ Questions and Support

### Getting Help

- **GitHub Discussions**: General questions and community support
- **Discord/Slack**: Real-time chat with maintainers and community
- **Documentation**: Check existing guides and API references
- **Stack Overflow**: Tag questions with `second-brain-stack`

### Maintainer Response Time

- **Bug Reports**: 24-48 hours for initial response
- **Feature Requests**: 1 week for initial feedback
- **Pull Requests**: 48-72 hours for review
- **Questions**: 24 hours for community support

## 📄 Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code. Please report unacceptable behavior to the maintainers.

## 📞 Contact

- **Project Maintainer**: [Your GitHub Profile]
- **Email**: [your-email@domain.com]
- **Discord**: [Discord Server Link]
- **Discussions**: [GitHub Discussions Link]

---

Thank you for contributing to Second Brain Stack! Together, we're building the future of knowledge management. 🧠✨