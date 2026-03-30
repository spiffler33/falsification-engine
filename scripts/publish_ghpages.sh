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

# Tee all output to log file so failures can be investigated
exec > >(tee -a "$LOG_FILE") 2>&1

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

# 2. Write snapshot into a JS file that sets window.__SNAPSHOT__
SNAPSHOT_FILE="$FRONTEND_DIR/public/snapshot.js"
echo "window.__SNAPSHOT__ = $SNAPSHOT_JSON;" > "$SNAPSHOT_FILE"
echo "[2/5] Snapshot written to $SNAPSHOT_FILE"

# 3. Inject the snapshot script tag into index.html for the build
INDEX_HTML="$FRONTEND_DIR/index.html"
CACHE_BUST=$(date +%s)
if ! grep -q 'snapshot.js' "$INDEX_HTML"; then
  # Add before closing </head> — cache-bust query param forces CDN refresh
  sed -i.bak "s|</head>|<script src=\"/snapshot.js?v=${CACHE_BUST}\"></script></head>|" "$INDEX_HTML"
  echo "  Injected snapshot.js script tag into index.html"
else
  # Update the cache-bust param on existing tag
  sed -i.bak "s|snapshot.js[^\"]*|snapshot.js?v=${CACHE_BUST}|" "$INDEX_HTML"
  echo "  Updated snapshot.js cache-bust param"
fi

# 4. Build the frontend
echo "[3/5] Building frontend ..."
cd "$FRONTEND_DIR"
npx vite build

# Get the repo name for base path (GitHub Pages serves at /repo-name/)
REPO_NAME=$(cd "$PROJECT_ROOT" && basename "$(git remote get-url origin 2>/dev/null | sed 's/\.git$//')" 2>/dev/null || echo "falsification-engine")

# Copy snapshot.js into dist
cp "$SNAPSHOT_FILE" "$FRONTEND_DIR/dist/snapshot.js"

# Add .nojekyll to prevent GitHub Pages from ignoring _-prefixed files
touch "$FRONTEND_DIR/dist/.nojekyll"

# Add a 404.html that redirects to index.html (SPA support)
cp "$FRONTEND_DIR/dist/index.html" "$FRONTEND_DIR/dist/404.html"

# 5. Deploy to gh-pages branch
echo "[4/5] Deploying to gh-pages branch ..."
cd "$PROJECT_ROOT"

DEPLOY_DIR="$FRONTEND_DIR/dist"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
REMOTE_URL=$(git remote get-url origin)

# Use a temporary directory to avoid polluting the working tree.
# The orphan-branch-in-working-tree approach leaks node_modules, __pycache__,
# .env, and other untracked files because the orphan has no .gitignore.
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

cp -r "$DEPLOY_DIR"/* "$TMPDIR/"
cp "$DEPLOY_DIR/.nojekyll" "$TMPDIR/" 2>/dev/null || true

cd "$TMPDIR"
git init
git checkout -b gh-pages
git add -A
git commit -m "Publish snapshot: $TIMESTAMP"
git remote add origin "$REMOTE_URL"
git push origin gh-pages --force

cd "$PROJECT_ROOT"

# Remove the snapshot injection from index.html
cd "$FRONTEND_DIR"
if [ -f "index.html.bak" ]; then
  mv "index.html.bak" "index.html"
fi
rm -f "$SNAPSHOT_FILE"

# 6. Verify the push landed
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
