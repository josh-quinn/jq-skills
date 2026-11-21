#!/bin/sh
# Restore fu at 306759c (v0.1.0, before the badge work) from the bundle, with no remote.
set -eu
git clone -q "$(dirname "$0")/fu-306759c.bundle" fu
git -C fu remote remove origin
