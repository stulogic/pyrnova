#!/bin/bash
# Pyrnova Workstream Control - double-click launcher (macOS).
# Isolated developer tooling. Does not touch the Pyrnova product runtime.
cd "$(dirname "$0")" || exit 1
exec /usr/bin/env python3 server.py
