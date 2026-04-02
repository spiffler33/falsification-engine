#!/usr/bin/env bash
# publish_ghpages.sh — Build a static snapshot and deploy to GitHub Pages.
#
# Prerequisites:
#   1. Backend must be running (uvicorn backend.main:app)
#   2. gh CLI must be installed and authenticated
#
# What it does:
#   1. Fetches /api/snapshot from the running backend
#   2. Builds the Vite frontend with the snapshot embedded
#   3. Pushes the built output to the gh-pages branch
#
# Usage:
#   ./scripts/publish_ghpages.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
LOG_FILE="$PROJECT_ROOT/logs/publish.log"

# Ensure logs directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Rotate log if it exceeds ~44 publishes (~2000 lines)
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt 2000 ]; then
  tail -500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

# Tee all output to log file so failures can be investigated
exec > >(tee -a "$LOG_FILE") 2>&1

# Prevent concurrent publishes from corrupting the build
LOCKFILE="$PROJECT_ROOT/.publish.lock"
if [ -f "$LOCKFILE" ]; then
  echo "ERROR: Another publish is already in progress"
  exit 1
fi
touch "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

echo ""
echo "=========================================="
echo "=== Publish started: $(date) ==="
echo "=========================================="
echo ""

# Pre-flight: verify git can reach the remote
echo "[pre-flight] Checking git remote connectivity ..."
REMOTE_URL_CHECK=$(git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null) || {
  echo "ERROR: No git remote 'origin' configured"
  exit 1
}
git -C "$PROJECT_ROOT" ls-remote --exit-code origin gh-pages >/dev/null 2>&1 || {
  echo "WARNING: Could not reach remote or gh-pages branch does not exist yet (will create)"
}
echo "  Remote OK: $REMOTE_URL_CHECK"

# Pre-flight: verify backend is running
echo "[pre-flight] Checking backend at $API_BASE ..."
curl -sf "$API_BASE/api/snapshot" -o /dev/null || {
  echo "ERROR: Could not reach backend at $API_BASE"
  echo "Make sure the backend is running: uvicorn backend.main:app"
  exit 1
}
echo "  Backend OK"

# 1. Fetch snapshot from running backend
echo ""
echo "[1/5] Fetching snapshot from $API_BASE/api/snapshot ..."
SNAPSHOT_JSON=$(curl -sf "$API_BASE/api/snapshot") || {
  echo "ERROR: Could not reach backend at $API_BASE"
  echo "Make sure the backend is running: uvicorn backend.main:app"
  exit 1
}

echo "  Snapshot fetched. $(echo "$SNAPSHOT_JSON" | wc -c | tr -d ' ') bytes."

# 2. Build the frontend FIRST — before touching any source files
#    (Modifying index.html or public/ while Vite dev server is running kills it)
echo "[2/5] Building frontend ..."
cd "$FRONTEND_DIR"
npx vite build

# 3. Inject snapshot into the BUILT output (dist/), not source files
CACHE_BUST=$(date +%s)
# Sanitize </ sequences to prevent script context injection in the HTML page.
# <\/ is valid in JS string literals but prevents the HTML parser from seeing a closing tag.
SAFE_JSON=$(echo "$SNAPSHOT_JSON" | sed 's|</|<\\/|g')
echo "window.__SNAPSHOT__ = $SAFE_JSON;" > "$FRONTEND_DIR/dist/snapshot.js"
echo "[3/5] Snapshot written to dist/snapshot.js"

# Inject the snapshot script tag into dist/index.html (not the source index.html)
DIST_INDEX="$FRONTEND_DIR/dist/index.html"
sed -i.bak "s|</head>|<script defer src=\"./snapshot.js?v=${CACHE_BUST}\"></script></head>|" "$DIST_INDEX"
rm -f "$DIST_INDEX.bak"
echo "  Injected snapshot.js script tag into dist/index.html"

# Add .nojekyll to prevent GitHub Pages from ignoring _-prefixed files
touch "$FRONTEND_DIR/dist/.nojekyll"

# 404.html is a safety net — HashRouter means it rarely triggers, but
# direct deep links (e.g. shared /hypothesis/X URLs) would 404 without it.
cp "$FRONTEND_DIR/dist/index.html" "$FRONTEND_DIR/dist/404.html"

# 4. Deploy to gh-pages branch
echo "[4/5] Deploying to gh-pages branch ..."
cd "$PROJECT_ROOT"

DEPLOY_DIR="$FRONTEND_DIR/dist"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
REMOTE_URL=$(git remote get-url origin)

# Use a temporary directory to avoid polluting the working tree.
# The orphan-branch-in-working-tree approach leaks node_modules, __pycache__,
# .env, and other untracked files because the orphan has no .gitignore.
DEPLOY_TMPDIR=$(mktemp -d)
trap 'rm -f "$LOCKFILE"; rm -rf "$DEPLOY_TMPDIR"' EXIT

cp -r "$DEPLOY_DIR"/* "$DEPLOY_TMPDIR/"
cp "$DEPLOY_DIR/.nojekyll" "$DEPLOY_TMPDIR/" 2>/dev/null || true

cd "$DEPLOY_TMPDIR"
git init
git checkout -b gh-pages
git add -A
git commit -m "Publish snapshot: $TIMESTAMP"
git remote add origin "$REMOTE_URL"
git push origin gh-pages --force

cd "$PROJECT_ROOT"

# No source-file cleanup needed — we only modified dist/

# 5. Verify the push landed
echo "[5/5] Verifying deployment ..."
cd "$PROJECT_ROOT"
REMOTE_SHA=$(git ls-remote origin gh-pages 2>/dev/null | awk '{print $1}')
if [ -z "$REMOTE_SHA" ]; then
  echo "ERROR: Verification failed — gh-pages branch not found on remote after push"
  echo "The push may have silently failed. Check git credentials and network."
  exit 1
fi
echo "  Verified: gh-pages remote ref is $REMOTE_SHA"

echo ""
echo "=== Published successfully at $(date) ==="
REPO_NAME=$(basename "$REMOTE_URL" .git)
OWNER=$(echo "$REMOTE_URL" | sed 's|.*github.com[:/]||;s|/.*||')
echo "Your site will be available at:"
echo "  https://$OWNER.github.io/$REPO_NAME/"
echo ""
