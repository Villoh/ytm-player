# Releasing ytm-player

The release flow is **tag-driven**. Pushing a `vX.Y.Z` tag triggers PyPI publish, which in turn triggers AUR publish.

## Quick checklist

1. **Bump version** — `src/ytm_player/__init__.py` → `__version__ = "X.Y.Z"`
2. **Update PKGBUILD** — `aur/PKGBUILD` → `pkgver=X.Y.Z`
3. **Fold CHANGELOG** — collapse all `### Unreleased` blocks into one `### vX.Y.Z (YYYY-MM-DD)` entry
4. **Lint + test**:
   ```bash
   .venv/bin/ruff format src/ tests/
   .venv/bin/ruff check src/ tests/
   .venv/bin/pytest -x -q
   ```
5. **Commit + tag + push**:
   ```bash
   git add -A
   git commit -m "chore(release): vX.Y.Z"
   git tag vX.Y.Z
   git push origin master --tags
   ```
6. **Watch the workflows**:
   ```bash
   gh run watch --exit-status
   ```

## What automation handles

### `Publish` workflow (`.github/workflows/publish.yml`)

Triggered on tag push. Builds wheel + sdist, smoke-tests against `ytm --version` in a fresh venv, uploads to PyPI via OIDC trusted publishing, creates a GitHub Release with the matching CHANGELOG section attached.

No API tokens — auth is via OIDC trusted-publisher entries at PyPI and TestPyPI.

### `Publish AUR` workflow (`.github/workflows/aur-publish.yml`)

Triggered after `Publish` succeeds. Reads `pkgver` from `aur/PKGBUILD`, clones `ssh://aur@aur.archlinux.org/ytm-player-git.git` via SSH key, copies `PKGBUILD`, regenerates `.SRCINFO` via `scripts/regenerate_srcinfo.py` (pure Python — no Arch dependency on Ubuntu CI runners), commits and pushes.

The `regenerate_srcinfo.py` script handles shell variable expansion (`${url}`, `$pkgname`) so PKGBUILD constructs like `source=("git+${url}.git")` resolve correctly in the emitted `.SRCINFO`.

## Manual fallback (if AUR action fails)

```bash
git clone ssh://aur@aur.archlinux.org/ytm-player-git.git /tmp/ytm-player-aur
cp aur/PKGBUILD /tmp/ytm-player-aur/
python3 scripts/regenerate_srcinfo.py /tmp/ytm-player-aur/PKGBUILD /tmp/ytm-player-aur/.SRCINFO
cd /tmp/ytm-player-aur
git add PKGBUILD .SRCINFO
git commit -m "Update to vX.Y.Z"
git push
rm -rf /tmp/ytm-player-aur
```

## First-time setup (one-time, already done — for reference)

### 1. AUR SSH key

Generate a dedicated key for GitHub Actions (separate from your personal AUR key):

```bash
ssh-keygen -t ed25519 -C "github-actions-aur-publish" -f ~/.ssh/aur_publish_key -N ""
```

Add the **public** key (`~/.ssh/aur_publish_key.pub`) to your AUR account at https://aur.archlinux.org/account/. AUR supports multiple SSH public keys per account — add it alongside your existing one, do not replace.

### 2. GitHub repo secrets

```bash
gh secret set AUR_SSH_PRIVATE_KEY --repo peternaame-boop/ytm-player < ~/.ssh/aur_publish_key
ssh-keyscan -t ed25519 aur.archlinux.org 2>/dev/null | gh secret set AUR_KNOWN_HOSTS --repo peternaame-boop/ytm-player
```

Verify both exist:

```bash
gh secret list --repo peternaame-boop/ytm-player | grep AUR
```

### 3. PyPI trusted publishing

Both PyPI and TestPyPI have a trusted-publisher entry pointing at this repo's `publish.yml`. No tokens stored anywhere — auth is via OIDC at workflow runtime.

| Field | Value |
|-------|-------|
| Owner | `peternaame-boop` |
| Repository | `ytm-player` |
| Workflow | `publish.yml` |
| Environment | `pypi` (or `testpypi` on TestPyPI) |

Configured at https://pypi.org/manage/account/publishing/ and https://test.pypi.org/manage/account/publishing/.

## Dry-run via TestPyPI

Trigger `Publish` manually from Actions → **Run workflow** → target `testpypi`. Builds + uploads to https://test.pypi.org/project/ytm-player/ without touching production.

The AUR workflow does NOT trigger on TestPyPI dry-runs — it gates on the Publish workflow's `event=push` condition (i.e., real tag pushes only).

## Distribution channels

| Channel | Maintained by | Update mechanism |
|---------|---------------|------------------|
| PyPI | Us | Automated via `publish.yml` on tag push |
| AUR (`ytm-player-git`) | Us | Automated via `aur-publish.yml` after PyPI succeeds |
| GitHub Release | Us | Automated via `publish.yml` on tag push |
| NixOS (`flake.nix`) | Us | Manual — bump in repo on release |
| Gentoo (GURU overlay) | @dsafxP (community) | Out of our hands — community maintainer updates the ebuild on their schedule |

## After the release

- Verify PyPI: https://pypi.org/project/ytm-player/
- Verify AUR: `curl -s https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=ytm-player-git | grep '^pkgver='`
- Verify GitHub Release: `gh release view vX.Y.Z`
- (Optional) Mention `@dsafxP` in the GitHub Release body so they know there's a new version to package for Gentoo.
