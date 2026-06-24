#!/usr/bin/env bash
# .claude/setup.sh — スキル環境の自動セットアップ
# 手動実行: bash .claude/setup.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OS_TYPE="$(uname -s)"
echo "=== AI ワークフロー環境セットアップ (${OS_TYPE}) ==="

# ─── 0. 前提チェック ───
echo "[0/7] 前提チェック..."
SKIP_NODE=false
SKIP_PYTHON=false

if ! command -v node &>/dev/null; then
  echo "  ⚠ Node.js が見つかりません。Node.js 18+ をインストールしてください"
  SKIP_NODE=true
elif [[ "$(node -v | sed 's/v//' | cut -d. -f1)" -lt 18 ]]; then
  echo "  ⚠ Node.js $(node -v) は古いです。18+ を推奨します"
fi

if ! command -v python3 &>/dev/null; then
  echo "  ⚠ Python3 が見つかりません。Python 3.10+ をインストールしてください"
  SKIP_PYTHON=true
elif [[ "$(python3 -c 'import sys; print(sys.version_info.minor)')" -lt 10 ]]; then
  echo "  ⚠ Python $(python3 --version) は古いです。3.10+ を推奨します"
fi

# ─── 1. AGENTS.md シンボリックリンク ───
echo "[1/7] AGENTS.md シンボリックリンク..."
if [ -L "$REPO_ROOT/AGENTS.md" ]; then
  echo "  - AGENTS.md は既にシンボリックリンク（スキップ）"
elif [ -e "$REPO_ROOT/AGENTS.md" ]; then
  rm -f "$REPO_ROOT/AGENTS.md"
  ln -s .claude/CLAUDE.md "$REPO_ROOT/AGENTS.md"
  echo "  ✓ AGENTS.md を非シンボリックリンクから置換"
else
  ln -s .claude/CLAUDE.md "$REPO_ROOT/AGENTS.md"
  echo "  ✓ AGENTS.md → .claude/CLAUDE.md を作成"
fi

# ─── 2. Python 依存パッケージ ───
echo "[2/7] Python パッケージ..."
if [ "$SKIP_PYTHON" = false ]; then
  pip install --quiet --upgrade openpyxl weasyprint markdown pypdf python-pptx playwright 2>/dev/null || \
    pip3 install --quiet --upgrade openpyxl weasyprint markdown pypdf python-pptx playwright 2>/dev/null || \
    echo "  ⚠ pip install に失敗。手動で openpyxl, weasyprint, markdown, pypdf, python-pptx, playwright をインストールしてください"
else
  echo "  - Python が見つからないためスキップ"
fi

# ─── 3. Node.js 依存パッケージ ───
echo "[3/7] Node.js パッケージ..."
if [ "$SKIP_NODE" = false ]; then
  if ! command -v mmdc &>/dev/null; then
    npm install -g @mermaid-js/mermaid-cli 2>/dev/null || \
      echo "  ⚠ mmdc のインストールに失敗。npm install -g @mermaid-js/mermaid-cli を手動実行してください"
  fi
  if ! command -v marp &>/dev/null; then
    npm install -g @marp-team/marp-cli 2>/dev/null || \
      echo "  ⚠ marp-cli のインストールに失敗。npm install -g @marp-team/marp-cli を手動実行してください"
  fi
  # dom-to-pptx (HTML→編集可能PPTX変換)
  if [ ! -d "${REPO_ROOT}/node_modules/dom-to-pptx" ]; then
    (cd "${REPO_ROOT}" && npm install dom-to-pptx 2>/dev/null) || \
      echo "  ⚠ dom-to-pptx のインストールに失敗。npm install dom-to-pptx を手動実行してください"
  fi
else
  echo "  - Node.js が見つからないためスキップ"
fi

# ─── 4. 日本語フォント & Chrome ───
echo "[4/7] 日本語フォント & Chrome..."

# フォント
if ! fc-list 2>/dev/null | grep -qi "bizud"; then
  if [ "$OS_TYPE" = "Darwin" ]; then
    if command -v brew &>/dev/null; then
      brew install --cask font-bizud-gothic 2>/dev/null || \
        echo "  ⚠ BIZ UDPGothic のインストールに失敗。brew install --cask font-bizud-gothic を手動実行してください"
    else
      echo "  ⚠ BIZ UDPGothic が未インストール。Homebrew で brew install --cask font-bizud-gothic を実行するか、手動でインストールしてください"
    fi
  else
    sudo apt-get update -qq 2>/dev/null && \
      sudo apt-get install -y -qq fonts-morisawa-bizud-gothic 2>/dev/null || \
      echo "  ⚠ BIZ UDPGothic のインストールに失敗。sudo apt install fonts-morisawa-bizud-gothic を手動実行してください"
  fi
  fc-cache -f 2>/dev/null || true
else
  echo "  - BIZ UDPGothic は既にインストール済み"
fi

# Chrome（Marp PDF 生成用）— Puppeteer 経由でインストール
CHROME_FOUND=false
# macOS: /Applications/Google Chrome.app を優先チェック
if [ "$OS_TYPE" = "Darwin" ] && [ -d "/Applications/Google Chrome.app" ]; then
  CHROME_FOUND=true
fi
if [ "$CHROME_FOUND" = false ]; then
  for cmd in chromium google-chrome google-chrome-stable; do
    command -v "$cmd" &>/dev/null && CHROME_FOUND=true && break
  done
fi
# Puppeteer キャッシュも確認（macOS: chrome-mac-arm64/chrome-mac-x64, Linux: chrome-linux64）
if [ "$CHROME_FOUND" = false ]; then
  for chrome in ~/.cache/puppeteer/chrome/*/chrome-*/chrome ~/.cache/puppeteer/chrome/*/chrome-*/"Google Chrome for Testing"; do
    [ -x "$chrome" ] && CHROME_FOUND=true && break
  done
fi

if [ "$CHROME_FOUND" = false ] && [ "$SKIP_NODE" = false ]; then
  echo "  Chrome をインストール中（Puppeteer 経由）..."
  npx puppeteer browsers install chrome 2>/dev/null || \
    echo "  ⚠ Chrome のインストールに失敗。npx puppeteer browsers install chrome を手動実行してください"
else
  echo "  - Chrome は既にインストール済み"
fi
# Playwright Chromium（HTML→PDF/PPTX エクスポート用）
if [ "$SKIP_PYTHON" = false ]; then
  python3 -m playwright install chromium 2>/dev/null || \
    echo "  ⚠ Playwright Chromium のインストールに失敗。python3 -m playwright install chromium を手動実行してください"
fi

# ─── 5. Codex スキル同期 & グローバル設定 ───
echo "[5/7] Codex スキル同期..."
bash "$REPO_ROOT/.claude/scripts/sync_codex_skills.sh"

# Codex グローバル AGENTS.md（~/.codex/AGENTS.md → マスター CLAUDE.md）
codex_home="${CODEX_HOME:-$HOME/.codex}"
if [ -d "$codex_home" ]; then
  codex_agents="$codex_home/AGENTS.md"
  master_claude="$REPO_ROOT/.claude/CLAUDE.md"
  if [ ! -e "$codex_agents" ] || [ -L "$codex_agents" ]; then
    ln -sfn "$master_claude" "$codex_agents"
    echo "  ✓ ~/.codex/AGENTS.md → $master_claude"
  else
    echo "  - ~/.codex/AGENTS.md は既に存在（非シンボリックリンク、スキップ）"
  fi

  # config.toml に developer_instructions と project_doc_fallback_filenames を追記（未設定の場合のみ）
  codex_config="$codex_home/config.toml"
  if [ -f "$codex_config" ]; then
    if ! grep -qF 'developer_instructions' "$codex_config" 2>/dev/null; then
      cat >> "$codex_config" << 'TOML'

# スキル実行時の手順遵守を強制
developer_instructions = """
スキル実行時はSKILL.mdの全ステップをStep 0から厳密に遵守すること。手順をスキップしてはならない。
出力は日本語で行うこと。
"""
TOML
      echo "  ✓ config.toml に developer_instructions を追加"
    fi
    if ! grep -qF 'project_doc_fallback_filenames' "$codex_config" 2>/dev/null; then
      cat >> "$codex_config" << 'TOML'

# AGENTS.mdがないリポでもCLAUDE.mdをフォールバックで読む
project_doc_fallback_filenames = ["CLAUDE.md"]
TOML
      echo "  ✓ config.toml に project_doc_fallback_filenames を追加"
    fi
  fi
else
  echo "  - ~/.codex/ が見つかりません（Codex未インストール、スキップ）"
fi

# ─── 6. リポジトリ同期（マルチリポ環境のみ） ───
REGISTRY="$REPO_ROOT/.claude/references/repo-registry.md"
if [ -f "$REGISTRY" ]; then
  echo "[6/7] リポジトリ同期..."
  bash "$REPO_ROOT/.claude/scripts/sync.sh"
else
  echo "[6/7] リポジトリ同期... スキップ（単一リポ環境 — repo-registry.md なし）"
fi

# ─── 検証 ───
echo ""
echo "=== セットアップ検証 ==="
PASS=true

check() {
  if eval "$2" &>/dev/null; then
    echo "  ✓ $1"
  else
    echo "  ✗ $1"
    PASS=false
  fi
}

check "Python 3.10+"      "python3 -c 'import sys; assert sys.version_info >= (3,10)'"
check "openpyxl"           "python3 -c 'import openpyxl'"
check "weasyprint"         "python3 -c 'import weasyprint'"
check "markdown"           "python3 -c 'import markdown'"
check "pypdf"              "python3 -c 'import pypdf'"
check "python-pptx"        "python3 -c 'import pptx'"
check "playwright"         "python3 -c 'import playwright'"
check "Node.js 18+"        "node -v"
check "dom-to-pptx"        "test -d '${REPO_ROOT}/node_modules/dom-to-pptx'"
check "mmdc (mermaid)"     "command -v mmdc"
check "marp-cli"           "command -v marp"
check "BIZ UDPGothic"     "fc-list 2>/dev/null | grep -qi bizud"
check "Chrome"             "test -d '/Applications/Google Chrome.app' || command -v chromium || command -v google-chrome || command -v google-chrome-stable || ls ~/.cache/puppeteer/chrome/*/chrome-*/chrome 2>/dev/null"
check "AGENTS.md"          "test -e '$REPO_ROOT/AGENTS.md'"
check "Codex AGENTS.md"    "test -L '$HOME/.codex/AGENTS.md'"
check "Codex dev_instructions" "grep -qF 'developer_instructions' '$HOME/.codex/config.toml' 2>/dev/null"

if [ "$PASS" = true ]; then
  echo ""
  echo "=== セットアップ完了（全チェック OK）==="
else
  echo ""
  echo "=== セットアップ完了（一部未解決あり — 上記 ✗ を確認）==="
fi
