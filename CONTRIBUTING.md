# Contributing

1. Create a branch from `main`.
2. Install the development environment with `pip install -e ".[dev]"`.
3. Add focused tests for behavioral changes and security regressions.
4. Run `make quality`.
5. For scanner changes, add both adversarial and nearby benign cases to the versioned evaluation corpus.
6. Open a pull request describing the behavior, risk, and validation performed.

Security-sensitive findings should follow [SECURITY.md](SECURITY.md) instead of being filed publicly.
