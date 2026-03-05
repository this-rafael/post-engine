#!/usr/bin/env fish

set -l script_dir (path dirname (status -f))
set -l project_root (path normalize "$script_dir/..")

cd "$project_root" || exit 1

rm -rf src/gui/static/dist frontend/node_modules/.cache
cd frontend && pnpm install --frozen-lockfile && pnpm run build
cd "$project_root" || exit 1
uv sync
uv run -- python -m content_engine --gui $argv
