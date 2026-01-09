# Contributing to Epic Games Status Monitor

Thanks for your interest in contributing! 🎉

## Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes

```bash
git checkout -b feature/your-feature-name
```

## Development Setup

### Python (GitHub Actions version)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy config
cp config.example.json config.json

# Run locally (without Telegram)
python poll_status.py
```

### Cloudflare Worker

```bash
cd worker
npm install

# Start local dev server
wrangler dev
```

## Making Changes

1. **Code style**: Follow existing patterns in the codebase
2. **Test locally**: Make sure your changes work before submitting
3. **Keep it focused**: One feature/fix per PR

## Submitting a Pull Request

1. **Push** your branch to your fork
2. **Open a PR** against the `main` branch
3. **Describe** what your changes do and why

## Reporting Issues

When reporting bugs, please include:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (Python version, OS, etc.)

## Questions?

Open an issue with your question - we're happy to help!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
