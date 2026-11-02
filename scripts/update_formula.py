"""Verify a stable PyPI sdist, then update the Homebrew formula and resources."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "Formula/kaiten-cli.rb"
STABLE = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", re.ASCII)
MAX_SOURCE_BYTES = 50 * 1024 * 1024


def version_tuple(value: str) -> tuple[int, int, int]:
    match = STABLE.fullmatch(value)
    if not match:
        raise ValueError(f"Not a stable X.Y.Z version: {value!r}")
    return tuple(map(int, match.groups()))


def select_version(payload: dict, requested: str | None) -> str:
    if requested:
        version_tuple(requested)
        return requested
    versions = [
        value
        for value, files in payload["releases"].items()
        if STABLE.fullmatch(value)
        and any(f["packagetype"] == "sdist" and not f.get("yanked") for f in files)
    ]
    if not versions:
        raise ValueError("PyPI contains no stable, non-yanked sdist")
    return max(versions, key=version_tuple)


def current_version(text: str) -> str:
    match = re.search(r'^  url "[^"\n]*/kaiten_cli-([0-9.]+)\.tar\.gz"$', text, re.M)
    if not match:
        raise ValueError("Cannot identify the current formula version")
    value = match.group(1)
    version_tuple(value)
    return value


def sdist_metadata(payload: dict, version: str) -> dict:
    if payload["info"]["version"] != version:
        raise ValueError("PyPI version does not match the requested release")
    if payload["info"].get("license_expression") != "MIT":
        raise ValueError("The release must declare License-Expression: MIT")
    files = [
        f
        for f in payload["urls"]
        if f["packagetype"] == "sdist" and not f.get("yanked")
    ]
    if len(files) != 1:
        raise ValueError("Expected exactly one non-yanked sdist")
    source = files[0]
    url = urlsplit(source["url"])
    if url.scheme != "https" or url.netloc != "files.pythonhosted.org":
        raise ValueError("Unexpected sdist download host")
    if url.query or url.fragment or not re.fullmatch(r"/[A-Za-z0-9/_.-]+", url.path):
        raise ValueError("Unexpected characters in the sdist URL")
    if source["filename"] != f"kaiten_cli-{version}.tar.gz":
        raise ValueError("Unexpected sdist filename")
    if not re.fullmatch(r"[0-9a-f]{64}", source["digests"]["sha256"]):
        raise ValueError("Invalid sdist SHA-256")
    return source


def verify_source(data: bytes, source: dict, version: str) -> None:
    if hashlib.sha256(data).hexdigest() != source["digests"]["sha256"]:
        raise ValueError("Downloaded sdist SHA-256 mismatch")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        prefix = f"kaiten_cli-{version}/"
        for name in (
            "LICENSE",
            "js/document-yjs/package-lock.json",
            "js/document-yjs/build.mjs",
        ):
            member = archive.getmember(prefix + name)
            if not member.isfile() or member.size == 0:
                raise ValueError(f"Missing required source file: {name}")
        license_file = archive.extractfile(prefix + "LICENSE")
        if license_file is None or b"MIT License" not in license_file.read():
            raise ValueError("Missing MIT license text")


def replace_source(text: str, source: dict) -> str:
    text, urls = re.subn(
        r'^  url "[^"\n]+"$', f'  url "{source["url"]}"', text, count=1, flags=re.M
    )
    text, hashes = re.subn(
        r'^  sha256 "[0-9a-f]{64}"$',
        f'  sha256 "{source["digests"]["sha256"]}"',
        text,
        count=1,
        flags=re.M,
    )
    if urls != 1 or hashes != 1:
        raise ValueError("Cannot locate formula source URL/SHA-256")
    return text


def get_json(url: str) -> dict:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def update(requested: str | None, *, bootstrap: bool = False) -> None:
    original = FORMULA.read_text()
    installed = current_version(original)
    selected = select_version(
        get_json("https://pypi.org/pypi/kaiten-cli/json"), requested
    )
    if version_tuple(selected) < version_tuple(installed):
        raise ValueError("Refusing to downgrade the formula")
    if selected == installed and not bootstrap:
        print(f"kaiten-cli {installed} is already current")
        return
    source = sdist_metadata(
        get_json(f"https://pypi.org/pypi/kaiten-cli/{selected}/json"), selected
    )
    with urlopen(source["url"], timeout=60) as response:
        data = response.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Source archive exceeds the size limit")
    verify_source(data, source, selected)
    try:
        FORMULA.write_text(replace_source(original, source))
        subprocess.run(
            [
                "brew",
                "update-python-resources",
                "ViktorOgnev/tap/kaiten-cli",
                "--version",
                selected,
                "--ignore-main-package-cooldown",
                "--install-dependencies",
            ],
            check=True,
            timeout=900,
        )
        subprocess.run(
            ["brew", "style", "--fix", "ViktorOgnev/tap/kaiten-cli"],
            check=True,
            timeout=300,
        )
    except BaseException:
        FORMULA.write_text(original)
        raise
    print(f"Prepared kaiten-cli {selected}; merge only after formula checks pass")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=os.environ.get("RELEASE_VERSION") or None)
    parser.add_argument(
        "--bootstrap", action="store_true", help="Populate a newly created formula"
    )
    args = parser.parse_args()
    update(args.version, bootstrap=args.bootstrap)
