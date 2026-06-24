---

name: sync
description: SSoTスキルを全リポにコピー・コミット・プッシュ
tier: "infra"
runtime: SSoT root
---

SSoT（`projects/.claude/`）のスキル・設定を全リポにファイルコピーし、コミット＆プッシュしてPRを作成する。

### Step 0: 初期化

| フロー | 適用 | 理由 |
|--------|:---:|------|
| Flow A（コンテキストロック） | **免除** | SSoT → 全リポへの配信。特定リポにロック不可 |
| Flow B（resolve/approve） | **免除** | インフラ操作。要求構造化の対象外 |

### Phase: requirements

事前バリデーション: SSoT ディレクトリの存在確認と repo-registry.md の読み込み。

### Phase: implement

#### Step 1: ファイル同期の実行

`bash .claude/scripts/sync.sh` を実行し、SSoT → 各リポの `.claude/` にファイルをコピーする。

### Phase: review

#### Step 2: 同期結果の検証

`bash .claude/scripts/verify-sync.sh` を実行し、SSoT と各リポの `.claude/` がバイト一致するかを検証する。

- **全リポ OK**: Step 3 に進む
- **FAIL あり**: 不一致の原因を調査・修正してから `sync.sh` を再実行し、再度 `verify-sync.sh` で検証する（全リポ OK になるまで繰り返す）

### Step 3: 各リポの変更確認

`repo-registry.md` のリポジトリ一覧を参照し、各リポで以下を確認：

1. `git -C ./{repo} status --short .claude/ AGENTS.md` で変更有無を確認
2. 変更がないリポはスキップ
3. 変更があるリポを一覧化してユーザーに報告

変更がゼロの場合は「全リポ最新です」と報告して終了。

### Step 4: コミット＆プッシュ（ユーザー承認後）

変更がある各リポについて：

1. 既存の `chore/sync-claude-framework` ブランチの worktree を検索（`git worktree list`）
2. **worktree が見つかった場合**: そのパスで作業を継続
3. **見つからない場合**:
   - **リモートにブランチが存在する場合**: `git -C ./{repo} worktree add .worktrees/chore-sync-claude -B chore/sync-claude-framework origin/chore/sync-claude-framework`（`-B` でローカルブランチをリモート追跡付きで作成。detached HEAD にしないこと）
   - **初回（リモートにブランチなし）**: `git -C ./{repo} worktree add .worktrees/chore-sync-claude -b chore/sync-claude-framework origin/{ベースブランチ}`
4. worktree 内の `.claude/` に SSoT のファイルをコピー（リポメインディレクトリからコピーしてもよい）
5. `git add .claude/ AGENTS.md`
6. `git commit -m "chore: sync .claude/ framework"`
7. `git push -u origin chore/sync-claude-framework`
8. PR が未作成なら `gh pr create --title "chore: sync .claude/ framework" --body "SSoTからスキル・設定を同期"`

### Step 5: マージ後の検証

PRがマージされたら、各リポで `git pull` した後に再度 `bash .claude/scripts/verify-sync.sh` を実行する。全リポ OK を確認してから完了報告する。

### Phase: report

#### Step 6: 完了報告

以下を報告：
- 同期したリポの一覧
- 各リポのPR URL
- verify-sync.sh の検証結果（全リポ OK であること）
- 未追跡だった `.claude/` が初回コミットされたリポ（あれば）

報告は日本語で。

### 注意事項

- **同期方向**: SSoT → 各リポへの一方向のみ。各リポ側で `.claude/` を直接編集しても次回 `/sync` で上書きされる
- **コンテキストロック**: このスキルは全リポを対象とするため、コンテキストロックは適用しない（読み書き対象が `.claude/` に限定されるため安全）
- **`repo-registry.md` の除外**: 各リポに `repo-registry.md` をコピーしないこと（マルチリポ環境と誤判定する原因になる）

$ARGUMENTS
