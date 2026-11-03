# Contributing

Issues and pull requests are welcome. The carrier lookup is the Apify Actor in `apify-actor/`. Behavior, input, and dataset fields are documented in `apify-actor/README.md`.

## Where to change code

- `apify-actor/fmcsa_actor/` calls the official FMCSA QCMobile API at `https://mobile.fmcsa.dot.gov/qc/services/` and maps the response into dataset rows.
- `run.py` checks an INDUS license (`indus-license*.json`) and prints a message. It does not look up a carrier.
- `tests/test_no_license_gate.py` fails if `apify-actor/fmcsa_actor/` references `selenium`, `safer.fmcsa.dot.gov`, `indus_license`, `require_license`, or `license_token`. Keep the Actor on the official API.

## Tests

From a checkout, on the Python version CI uses (3.12):

```bash
cd apify-actor
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The tests mock QCMobile HTTP responses. They do not call FMCSA. Do not add a test that sends a real WebKey.

`.github/workflows/ci.yml` runs the same `unittest` command on every pull request to `main`.

## Pull requests

1. Fork the repository and create a feature branch.
2. Keep the change focused, with a commit message that says what changed.
3. Run the unit tests above before opening the pull request.
4. Describe what changed and why.
5. Do not commit secrets, API keys, or credentials. That includes FMCSA WebKeys, `apify-actor/INPUT.json`, `indus-license*.json`, `.env`, and anything under `apify-actor/storage/`.

## Issues

Use the bug report or feature request template. Include the command you ran (`python -m fmcsa_actor`, `python -m unittest ...`, or `python run.py`) and what you expected. Leave out the WebKey and any license token.

## Security

Do not open a public issue for a security-sensitive problem. Follow [SECURITY.md](SECURITY.md).

## Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
