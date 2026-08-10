# Contributing

1. Create a branch from `main`.
2. Install the development environment with `pip install -e ".[dev]"`.
3. Add focused tests for behavioral changes and security regressions.
4. Run `ruff check .` and `pytest --cov=aegis_prompt_studio`.
5. Open a pull request describing the behavior, risk, and validation performed.

Security-sensitive findings should follow [SECURITY.md](SECURITY.md) instead of being filed publicly.
