"""Verify an explicit historical-version upgrade on a clean Homebrew runner."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

from update_formula import (
    FORMULA,
    current_version,
    get_json,
    replace_source,
    version_tuple,
)


def verify(previous: str) -> None:
    original = FORMULA.read_text()
    current = current_version(original)
    if version_tuple(previous) >= version_tuple(current):
        raise ValueError("Upgrade verification needs an older stable release")
    installed = subprocess.run(
        ["brew", "list", "--versions", "kaiten-cli"], capture_output=True, text=True
    )
    if installed.stdout.strip():
        raise ValueError(
            "Use a clean runner; an existing kaiten-cli install will not be removed"
        )
    metadata = get_json(f"https://pypi.org/pypi/kaiten-cli/{previous}/json")
    sources = [
        f
        for f in metadata["urls"]
        if f["packagetype"] == "sdist" and not f.get("yanked")
    ]
    if len(sources) != 1 or sources[0]["filename"] != f"kaiten_cli-{previous}.tar.gz":
        raise ValueError("Expected one historical kaiten-cli sdist")
    source = sources[0]
    if not source["url"].startswith("https://files.pythonhosted.org/"):
        raise ValueError("Unexpected source host")
    historical = replace_source(original, source)
    # 0.3.4 predates the project's MIT license. Never publish this local test formula.
    if metadata["info"].get("license_expression") != "MIT":
        historical = historical.replace(
            '  license "MIT"', "  license :cannot_represent", 1
        )
    prefix = subprocess.check_output(["brew", "--prefix"], text=True).strip()
    binary = str(Path(prefix) / "bin/kaiten")
    env = dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_INSTALL_CLEANUP="1")
    env.update(KAITEN_DOMAIN="", KAITEN_TOKEN="")
    with tempfile.TemporaryDirectory(prefix="kaiten-upgrade-") as directory:
        config = Path(directory) / "config.json"
        config.write_text('{"profiles":{},"active_profile":null}\n')
        digest = hashlib.sha256(config.read_bytes()).hexdigest()
        env["KAITEN_CLI_CONFIG_PATH"] = str(config)
        try:
            FORMULA.write_text(historical)
            subprocess.run(
                [
                    "brew",
                    "install",
                    "--build-from-source",
                    "ViktorOgnev/tap/kaiten-cli",
                ],
                check=True,
                env=env,
            )
            output = subprocess.check_output(
                [binary, "--locale", "ru", "--version"], text=True, env=env
            )
            if previous not in output:
                raise ValueError("Historical version was not installed")
        finally:
            FORMULA.write_text(original)
        subprocess.run(
            ["brew", "upgrade", "--build-from-source", "ViktorOgnev/tap/kaiten-cli"],
            check=True,
            env=env,
        )
        output = subprocess.check_output(
            [binary, "--locale", "ru", "--version"], text=True, env=env
        )
        if (
            current not in output
            or hashlib.sha256(config.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Upgrade version/configuration invariant failed")
    print(f"Verified Homebrew upgrade {previous} -> {current}; configuration unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-version", required=True)
    verify(parser.parse_args().from_version)
