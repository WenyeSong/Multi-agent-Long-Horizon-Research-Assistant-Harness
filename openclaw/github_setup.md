# GitHub Setup

The OpenClaw main/planner may maintain GitHub repositories, but only for
repository lifecycle work. It must not use GitHub as a general web browser or
literature-search tool.

## Current WSL Status

- `git` is installed.
- `gh` is not currently installed.
- Global Git identity is already configured.

## Install GitHub CLI

Use the official GitHub CLI APT repository on Debian/Ubuntu/WSL:

```bash
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && sudo mkdir -p -m 755 /etc/apt/sources.list.d \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && sudo apt update \
  && sudo apt install gh -y
```

Verify:

```bash
gh --version
```

## Log In

For normal interactive login:

```bash
gh auth login
```

Recommended answers:

- Account: `GitHub.com`
- Protocol: `SSH` if you use SSH keys, otherwise `HTTPS`
- Authenticate: browser/device-code flow

Verify:

```bash
gh auth status
```

## Common Repository Commands

Create a private repo from the current folder:

```bash
gh repo create REPO_NAME --private --source=. --remote=origin --push
```

Create a public repo only after explicit confirmation:

```bash
gh repo create REPO_NAME --public --source=. --remote=origin --push
```

Push an existing remote:

```bash
git remote add origin git@github.com:OWNER/REPO_NAME.git
git push -u origin main
```

## Planner Safety Rules

- Default to `--private`
- Confirm before public repo creation
- Confirm before delete, transfer, force-push, or release publication
- Run `git status --short --ignored`
- Run a tracked-file secret scan before push
- Never publish `.env`, API keys, local OpenClaw state, ignored task workspaces,
  or generated scratch files
