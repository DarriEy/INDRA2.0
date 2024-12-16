# Contributing to INDRA2.0

First off, thank you for considering contributing to INDRA2.0! This document provides guidelines and steps for contributing.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:
- Be respectful and inclusive
- Exercise consideration and empathy
- Focus on what is best for the community
- Gracefully accept constructive criticism

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:
- A clear and descriptive title
- Detailed steps to reproduce the issue
- Expected behavior vs actual behavior
- Code samples and error messages if applicable
- Your environment details (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:
- A clear and descriptive title
- Detailed explanation of the proposed functionality
- Any possible drawbacks or challenges
- If applicable, examples from other similar projects

### Pull Requests

1. Fork the repository and create your branch from `main`
2. If you've added code that should be tested, add tests
3. Ensure your code follows our style guidelines
4. Update the documentation if needed
5. Issue the pull request

## Development Process

1. Clone the repository
```bash
git clone https://github.com/DarriEy/INDRA2.0.git
cd INDRA2.0
```

2. Create a branching naming convention:
- `feature/your-feature-name` for new features
- `bugfix/issue-description` for bug fixes
- `docs/what-you-changed` for documentation changes

3. Make your changes in your branch and commit with clear, descriptive messages

4. Push to your fork and submit a pull request

## Style Guidelines

### Python Code Style

- Follow PEP 8 standards
- Use type hints for function parameters and return values
- Write docstrings for classes and functions
- Keep functions focused and concise
- Use meaningful variable names

Example:
```python
def analyze_streamflow(data: pd.DataFrame, threshold: float) -> Dict[str, Any]:
    """
    Analyze streamflow data against a threshold.
    
    Args:
        data: DataFrame containing streamflow data
        threshold: Threshold value for analysis
        
    Returns:
        Dictionary containing analysis results
    """
    # Implementation here
```

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters
- Reference issues and pull requests liberally after the first line

## Testing

- Write tests for new functionality
- Ensure all tests pass before submitting PR
- Include both unit tests and integration tests where appropriate
- Use pytest as the testing framework

## Documentation

- Update the README.md if needed
- Add docstrings to new functions and classes
- Update any relevant documentation in the docs folder
- Include code examples for new features

## Need Help?

Don't hesitate to ask for help! You can:
- Open an issue with the "question" label
- Contact the maintainers directly
- Join our discussions section on GitHub

## Acknowledgments

Your contributions are valued and appreciated. All contributors will be acknowledged in our documentation.

## Additional Notes

### For Expert System Development
- If modifying AI prompts, test thoroughly with various inputs
- Document any changes to expert system behavior
- Consider edge cases in hydrological modeling

### For CONFLUENCE Integration
- Test integration with different CONFLUENCE versions
- Document any changes to configuration handling
- Ensure backward compatibility

Thank you for contributing to INDRA2.0!
