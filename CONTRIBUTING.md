# Contributing / コントリビュート

Thank you for your interest in contributing to this repository! Below are guidelines to help your contribution go smoothly.

## How to contribute

1. Fork the repository and create a feature branch from `main`:

```bash
git checkout -b feature/your-feature
```

2. Make your changes in the feature branch. Keep changes focused and provide tests where appropriate.

3. Run tests and basic checks locally before submitting a Pull Request (see "Testing" section).

4. Push your branch to your fork and open a Pull Request against `featlis/TwitterTranslateBOTforDiscord:main`.

5. In the PR description, include a summary of changes, motivation, relevant issue numbers, and instructions to reproduce if applicable.

## Pull Request checklist

- [ ] The code builds and tests pass locally.
- [ ] New features include tests where applicable.
- [ ] Commit messages are clear and reference related issues (if any).
- [ ] No secrets or credentials are included in the changes.

## Testing

Run unit tests:

```powershell
python -m unittest discover -s tests
```

Run basic syntax checks:

```powershell
python -m compileall src tests
```

## Coding style

- Follow existing project styles. Use meaningful variable and function names.
- Keep changes small and focused per PR.

## Issues

If you find a bug or want to request a feature, please open an Issue with steps to reproduce, the expected behavior, and environment information (Python version, bot version/commit, and relevant logs).

## Security / Secrets

Do not include secrets, tokens, or credentials in commits. Use environment variables, secret managers, or the hosting provider's secrets feature. If you accidentally commit a secret, rotate it immediately and notify maintainers.

---

# コントリビュート（日本語）

ご協力ありがとうございます。以下は貢献のための手順とルールです。

## 貢献の手順

1. リポジトリをForkし、`main` から feature ブランチを作成します:

```bash
git checkout -b feature/your-feature
```

2. ブランチで変更を行い、必要に応じてテストを追加してください。

3. ローカルでテストと簡単なチェックを実行してから Pull Request を作成してください（下記「テスト」参照）。

4. Fork にプッシュして、`featlis/TwitterTranslateBOTforDiscord:main` に対して Pull Request を作成してください。

5. PR の説明には変更内容、理由、関連する Issue 番号、再現手順（ある場合）を記載してください。

## PR チェックリスト

- [ ] コードがビルドされ、テストが通っていること。
- [ ] 新機能にはテストが追加されていること（該当する場合）。
- [ ] コミットメッセージが分かりやすいこと。
- [ ] トークンや資格情報が含まれていないこと。

## テスト

ユニットテストを実行:

```powershell
python -m unittest discover -s tests
```

簡単な構文チェック:

```powershell
python -m compileall src tests
```

## コーディングスタイル

- 既存のスタイルに従ってください。意味のある名前を使い、可読性を保ってください。
- 1 PR は小さく保ち、1つの目的に絞ることを推奨します。

## Issue の作成について

バグ報告や機能要望は Issue を作成してください。再現手順、期待する動作、実行環境（Python バージョン、ボットのバージョン／コミット、関連ログ）を添えてください。

## セキュリティ / シークレット

トークンや資格情報をコミットしないでください。環境変数やホスティングのシークレット機能を使用してください。誤ってコミットした場合はただちにローテーション（再発行）し、担当者に連絡してください。

---

If you'd like, I can also add a simple `CODE_OF_CONDUCT.md` and a `ISSUE_TEMPLATE`/`PULL_REQUEST_TEMPLATE`.