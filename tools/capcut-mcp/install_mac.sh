#!/bin/bash
# Cài CapCut MCP trên macOS. Chạy: bash install_mac.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="$HOME/.capcut-mcp"
VENV="$HOME_DIR/venv"

if ! command -v brew >/dev/null 2>&1; then
  echo "Chưa có Homebrew. Cài theo hướng dẫn tại https://brew.sh rồi chạy lại script này."
  exit 1
fi
echo "==> Cài Python 3.12 và ffmpeg (nếu chưa có)"
brew list python@3.12 >/dev/null 2>&1 || brew install python@3.12
command -v ffmpeg >/dev/null 2>&1 || brew install ffmpeg
PY="$(brew --prefix python@3.12)/bin/python3.12"

echo "==> Tạo môi trường Python tại $VENV"
mkdir -p "$HOME_DIR"
"$PY" -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -e "$DIR[mcp]"  # editable: code edits here apply without reinstall
mkdir -p "$HOME/Movies/CapCut-MCP"

echo "==> Đăng ký MCP với Claude Desktop"
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
mkdir -p "$(dirname "$CFG")"
"$VENV/bin/python" - "$CFG" "$VENV/bin/capcut-mcp" <<'PYEOF'
import json, sys, os
cfg_path, cmd = sys.argv[1], sys.argv[2]
cfg = {}
if os.path.exists(cfg_path):
    with open(cfg_path) as f:
        try: cfg = json.load(f)
        except Exception: cfg = {}
cfg.setdefault("mcpServers", {})["capcut"] = {"command": cmd, "args": []}
with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print("   Đã ghi", cfg_path)
PYEOF

if command -v claude >/dev/null 2>&1; then
  echo "==> Đăng ký MCP với Claude Code"
  claude mcp add capcut --scope user -- "$VENV/bin/capcut-mcp" || true
fi

echo "==> Kiểm tra"
"$VENV/bin/python" -c "from capcut_mcp.server import capcut_status; import json; print(json.dumps(capcut_status(), indent=2, ensure_ascii=False))"
echo
echo "Xong! Thoát hẳn Claude Desktop (Cmd+Q) rồi mở lại để thấy công cụ 'capcut'."
