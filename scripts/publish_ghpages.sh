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

echo "=== Falsification Engine: Publish to GitHub Pages ==="
echo ""

# 1. Fetch snapshot from running backend
echo "[1/4] Fetching snapshot from $API_BASE/api/snapshot ..."
SNAPSHOT_JSON=$(curl -sf "$API_BASE/api/snapshot") || {
  echo "ERROR: Could not reach backend at $API_BASE"
  echo "Make sure the backend is running: uvicorn backend.main:app"
  exit 1
}

echo "  Snapshot fetched. $(echo "$SNAPSHOT_JSON" | wc -c | tr -d ' ') bytes."

# 2. Write snapshot into a JS file that sets window.__SNAPSHOT__
SNAPSHOT_FILE="$FRONTEND_DIR/public/snapshot.js"
echo "window.__SNAPSHOT__ = $SNAPSHOT_JSON;" > "$SNAPSHOT_FILE"
echo "[2/4] Snapshot written to $SNAPSHOT_FILE"

# 3. Inject the snapshot script tag into index.html for the build
INDEX_HTML="$FRONTEND_DIR/index.html"
if ! grep -q 'snapshot.js' "$INDEX_HTML"; then
  # Add before closing </head>
  sed -i.bak 's|</head>|<script src="/snapshot.js"></script></head>|' "$INDEX_HTML"
  echo "  Injected snapshot.js script tag into index.html"
fi

# 4. Build the frontend
echo "[3/4] Building frontend ..."
cd "$FRONTEND_DIR"
npm run build

# Get the repo name for base path (GitHub Pages serves at /repo-name/)
REPO_NAME=$(cd "$PROJECT_ROOT" && basename "$(git remote get-url origin 2>/dev/null | sed 's/\.git$//')" 2>/dev/null || echo "falsification-engine")

# Copy snapshot.js into dist
cp "$SNAPSHOT_FILE" "$FRONTEND_DIR/dist/snapshot.js"

# Add .nojekyll to prevent GitHub Pages from ignoring _-prefixed files
touch "$FRONTEND_DIR/dist/.nojekyll"

# Add a 404.html that redirects to index.html (SPA support)
cp "$FRONTEND_DIR/dist/index.html" "$FRONTEND_DIR/dist/404.html"

# 5. Deploy to gh-pages branch
echo "[4/4] Deploying to gh-pages branch ..."
cd "$PROJECT_ROOT"

# Use git subtree or manual push
DEPLOY_DIR="$FRONTEND_DIR/dist"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")

# Create a temporary orphan branch, copy dist contents, push
TEMP_BRANCH="ghpages-deploy-$(date +%s)"
git checkout --orphan "$TEMP_BRANCH"
git rm -rf . > /dev/null 2>&1 || true

cp -r "$DEPLOY_DIR"/* .
cp "$DEPLOY_DIR/.nojekyll" . 2>/dev/null || true

git add -A
git commit -m "Publish snapshot: $TIMESTAMP"
git push origin "$TEMP_BRANCH:gh-pages" --force

# Clean up: go back to original branch
git checkout master
git branch -D "$TEMP_BRANCH"

# Remove the snapshot injection from index.html
cd "$FRONTEND_DIR"
if [ -f "index.html.bak" ]; then
  mv "index.html.bak" "index.html"
fi
rm -f "$SNAPSHOT_FILE"

echo ""
echo "=== Published successfully ==="
echo "Your site will be available at:"
echo "  https://$(git -C "$PROJECT_ROOT" remote get-url origin | sed 's|.*github.com[:/]||;s|\.git$||' | tr '/' '\n' | head -1).github.io/$REPO_NAME/"
echo ""
