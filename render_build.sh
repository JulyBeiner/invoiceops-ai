#!/usr/bin/env bash
# Build script for Render (see render.yaml). Runs on every deploy.
set -o errexit   # stop at the first failing command

# 1. Front-end: install the JS dependencies and compile React into dist/
npm install
npm run build

# 2. Back-end: install the Python dependencies pinned in Pipfile.lock
pip install pipenv
pipenv install

# 3. Database: apply the migrations, then load the demo company.
#    The seed does nothing if the company already exists, so it is safe to repeat.
#    Set the SEED_RESET environment variable to 1 in Render to wipe and reload
#    the demo company on the next deploy (then set it back to 0).
pipenv run upgrade
if [ "$SEED_RESET" = "1" ]; then
  pipenv run seed --reset
else
  pipenv run seed
fi