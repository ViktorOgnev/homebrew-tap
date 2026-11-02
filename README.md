# ViktorOgnev Homebrew tap

Homebrew formulae maintained by Viktor Ognev. This public tap is independent of
`homebrew/core`; it uses standard Homebrew packaging so the formula can be
proposed for core later.

## Install and upgrade

```sh
brew install ViktorOgnev/tap/kaiten-cli
kaiten --locale ru --version
kaiten --locale ru --help
brew update
brew upgrade kaiten-cli
```

The formula installs an isolated Python environment and Node.js for Kaiten's
temporary Yjs document compatibility transport. No global pip installation or
shell startup changes are made. The initial distribution builds from the
checksummed PyPI source archive; this tap does not publish bottles.

On macOS, source builds require up-to-date Xcode Command Line Tools. If Homebrew
rejects outdated tools, update them through System Settings → General → Software
Update before installing. See [Homebrew installation requirements](https://docs.brew.sh/Installation).

If switching from pipx or uv, uninstall that copy with the original manager first.
For pip, uninstall from the original Python environment. Profiles remain in the
user configuration directory. Check `command -v kaiten` and `type -a kaiten` to
confirm Homebrew owns the executable selected by your shell.

## Updates

The `Update formula` workflow checks PyPI every six hours. It selects stable
`X.Y.Z` releases with a non-yanked sdist, verifies the downloaded SHA-256 and MIT
license, and regenerates pinned Python resources with Homebrew's official helper.
It never downgrades the formula. A single `update/kaiten-cli` branch and PR tracks
the newest release. Maintainers review and merge after all required checks pass.

Use **Actions → Update formula → Run workflow** to request a specific stable
version or check immediately. Re-running an already packaged version is a no-op.
An update failure does not alter PyPI or the formula on `main`.

The private GitHub App `ViktorOgnev Homebrew Updates` is installed only on this
repository, with Contents and Pull requests write permissions and mandatory
Metadata read access. It has no account or organization permissions and no
webhook. It runs entirely in Actions; no server is required.

- Repository variable: `HOMEBREW_APP_ID`.
- Repository secret: `HOMEBREW_APP_PRIVATE_KEY`.
- Rotate the key in the owner's GitHub App settings, update the secret, verify
  automation, then revoke the previous key. Never commit or print private keys.
- Standard runners in this public repository are free. Workflows do not upload
  artifacts or use paid larger runners.

## Validation and recovery

```sh
python3 -m unittest discover -s tests -v
brew style ViktorOgnev/tap/kaiten-cli
brew install --build-from-source ViktorOgnev/tap/kaiten-cli
brew audit --strict --online ViktorOgnev/tap/kaiten-cli
brew test ViktorOgnev/tap/kaiten-cli
```

CI covers Linux x86_64 and macOS Apple Silicon with standard GitHub-hosted
runners. Intel macOS is Homebrew Tier 3 and no longer receives new dependency
bottles; it is not a supported target for this tap. See
[Homebrew support tiers](https://docs.brew.sh/Support-Tiers). For Intel macOS,
use the upstream PyPI distribution in a compatible Python environment. The required aggregate check fails if any platform or
updater test fails. CLI tests use isolated configuration and no Kaiten credentials.
They verify command discovery without API calls, both entry points, the bundled
Yjs helper and exclusion from the Git-only self-update path.

For release acceptance, manually run `Formula checks` with `previous_version`
set to an older stable version (initial baseline: `0.3.4`). On clean runners it
installs that historical version, restores the current formula, upgrades and
checks the selected version and preservation of an isolated configuration file.
Historical license metadata is used only in the temporary runner formula.

If resource generation fails, inspect the workflow log and retry after fixing the
dependency or source problem. The updater restores the original formula on
failure; no partial update reaches `main`. Roll back a merged packaging change
with a reviewed revert PR. Keep published upstream versions and tags immutable.

## Future core migration

Keep the formula name `kaiten-cli`, standard Python resources, MIT licensing and
reproducible JavaScript sources. Before proposing the formula to core, recheck
current popularity, runtime, dependency and platform requirements; tap support
does not guarantee acceptance.

After the core formula is accepted, coordinate removal of the formula here and
add `"kaiten-cli": "homebrew/core"` to `tap_migrations.json`. Disable this formula's
update workflow and update installation documentation. Do not add the migration
before the core destination exists.

See [Homebrew's migration guide](https://docs.brew.sh/Migrating-A-Formula-To-A-Tap).
