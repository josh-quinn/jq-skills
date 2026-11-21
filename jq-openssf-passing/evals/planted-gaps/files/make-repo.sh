#!/bin/sh
# Build the "weatherline" test repo in the current folder, with gaps planted on purpose:
# nothing directly in docs/, SECURITY.md says to open a public issue, CI lints but doesn't run
# the tests, `permissions: read-all`, HTTPS through requests (so crypto isn't blanket N/A),
# and the latest feature landed without tests.
set -eu
git init -q -b main weatherline
cd weatherline
git config user.name "Sam Rivera"
git config user.email "sam@example.com"
c() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -q -m "$2"; }

cat > LICENSE <<'EOF'
MIT License

Copyright (c) 2026 Sam Rivera

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
EOF
cat > pyproject.toml <<'EOF'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "weatherline"
version = "0.2.0"
description = "One-line weather forecasts in your terminal"
license = "MIT"
requires-python = ">=3.10"
dependencies = ["requests>=2.31"]

[project.scripts]
weatherline = "weatherline.cli:main"

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[tool.ruff]
line-length = 100
EOF
cat > .gitignore <<'EOF'
__pycache__/
dist/
.venv/
EOF
mkdir -p src/weatherline tests
cat > src/weatherline/__init__.py <<'EOF'
__version__ = "0.2.0"
EOF
cat > src/weatherline/cli.py <<'EOF'
"""weatherline: a one-line forecast for a place, from the Open-Meteo API."""

import argparse
import json
import sys

import requests

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"


def locate(place: str) -> tuple[float, float, str]:
    r = requests.get(GEOCODE, params={"name": place, "count": 1}, timeout=10)
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        raise LookupError(f"no place called {place!r}")
    top = results[0]
    return top["latitude"], top["longitude"], top["name"]


def forecast(lat: float, lon: float) -> dict:
    r = requests.get(FORECAST, params={"latitude": lat, "longitude": lon, "current_weather": "true"}, timeout=10)
    r.raise_for_status()
    return r.json()["current_weather"]


def line(name: str, weather: dict, units: str = "c") -> str:
    t = weather["temperature"]
    if units == "f":
        t = t * 9 / 5 + 32
    return f"{name}: {t:.0f}°{units.upper()}, wind {weather['windspeed']:.0f} km/h"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="weatherline", description=__doc__)
    ap.add_argument("place")
    ap.add_argument("--units", choices=["c", "f"], default="c")
    ap.add_argument("--json", action="store_true", help="print the raw current weather as JSON")
    args = ap.parse_args(argv)
    try:
        lat, lon, name = locate(args.place)
        weather = forecast(lat, lon)
    except (LookupError, requests.RequestException) as e:
        print(f"weatherline: {e}", file=sys.stderr)
        return 1
    print(json.dumps(weather) if args.json else line(name, weather, args.units))
    return 0
EOF
# The first version has no --json; it arrives later without tests.
cp src/weatherline/cli.py ../cli-final.py
python3 - <<'EOF'
p = "src/weatherline/cli.py"
s = open(p).read()
s = s.replace("import json\n", "")
s = s.replace('    ap.add_argument("--json", action="store_true", help="print the raw current weather as JSON")\n', "")
s = s.replace("json.dumps(weather) if args.json else line(", "line(")
open(p, "w").write(s)
EOF
cat > tests/test_cli.py <<'EOF'
from weatherline.cli import line


def test_line_in_celsius():
    assert line("Oslo", {"temperature": 3.4, "windspeed": 12.2}) == "Oslo: 3°C, wind 12 km/h"
EOF
cat > README.md <<'EOF'
# weatherline

One-line weather forecasts in your terminal, from the free Open-Meteo API.

## Install

    pip install weatherline

## Use

    weatherline Oslo
    weatherline "New York" --units f

Run the tests with `pytest`.
EOF
cat > CONTRIBUTING.md <<'EOF'
# Contributing

Pull requests are welcome. Fork the repository, make your change on a branch, run `ruff check .`,
and open a pull request against `main`.
EOF
cat > SECURITY.md <<'EOF'
# Security

If you find a security problem, please open a GitHub issue describing it.
EOF
mkdir -p .github/workflows
cat > .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
permissions: read-all
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .
EOF
git add -A
c "2026-05-02T10:00:00Z" "Initial version of weatherline"

mkdir -p docs/guide
cat > docs/guide/usage.md <<'EOF'
# Using weatherline

`weatherline PLACE` prints the current temperature and wind for the best match for PLACE.
`--units f` gives Fahrenheit. `--json` prints the raw data.
EOF
cat > CHANGELOG.md <<'EOF'
# Changelog

## 0.1.0 - 2026-05-20

- First release: current weather for a place, Celsius or Fahrenheit.
EOF
git add -A
c "2026-05-20T10:00:00Z" "Add usage guide and changelog"
git tag v0.1.0

# A feature that landed without tests.
mv ../cli-final.py src/weatherline/cli.py
python3 - <<'EOF'
p = "CHANGELOG.md"
s = open(p).read().replace("# Changelog\n", "# Changelog\n\n## 0.2.0 - 2026-09-14\n\n- Add --json output.\n", 1)
open(p, "w").write(s)
EOF
git add -A
c "2026-09-14T10:00:00Z" "Add --json output"
git tag v0.2.0
