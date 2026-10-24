from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

PACKAGE_NAME = "@openai/codex"
PACKAGE_VERSION = "0.163.0-linux-x64"
PACKAGE_URL = (
    "https://registry.npmjs.org/@openai/codex/-/codex-0.163.0-linux-x64.tgz"
)
PACKAGE_SHA512 = (
    "bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3"
)
MAX_PACKAGE_BYTES = 200 * 1024 * 1024
MAX_UNPACKED_BYTES = 1_000_000_000
CODEX_RELATIVE_PATH = PurePosixPath(
    "package/vendor/x86_64-unknown-linux-musl/bin/codex"
)
BWRAP_RELATIVE_PATH = PurePosixPath(
    "package/vendor/x86_64-unknown-linux-musl/codex-resources/bwrap"
)


class RuntimePreparationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download_package(destination: Path) -> dict[str, Any]:
    digest = hashlib.sha512()
    total = 0
    request = urllib.request.Request(
        PACKAGE_URL,
        headers={"User-Agent": "qa-workflow-skills-runtime-preflight/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response, destination.open(
            "xb"
        ) as target:
            if response.status != 200:
                raise RuntimePreparationError("Codex package download was not HTTP 200")
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > MAX_PACKAGE_BYTES:
                    raise RuntimePreparationError("Codex package exceeds the byte limit")
                digest.update(block)
                target.write(block)
    except (OSError, TimeoutError) as exc:
        raise RuntimePreparationError(
            f"Codex package download failed: {type(exc).__name__}"
        ) from exc
    actual = digest.hexdigest()
    if actual != PACKAGE_SHA512:
        raise RuntimePreparationError("Codex package SHA-512 mismatch")
    return {"url": PACKAGE_URL, "bytes": total, "sha512": actual}


def _safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.parts[0] != "package"
    ):
        raise RuntimePreparationError("Codex package contains an unsafe path")
    return path


def _extract_package(archive_path: Path, destination: Path) -> None:
    total = 0
    destination.mkdir(mode=0o700, exist_ok=True)
    if any(destination.iterdir()):
        raise RuntimePreparationError("Codex extraction destination is not empty")
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive.getmembers():
                relative = _safe_member_path(member.name)
                if member.isdir():
                    target_dir = destination.joinpath(*relative.parts)
                    target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                    continue
                if not member.isfile():
                    raise RuntimePreparationError(
                        "Codex package contains a non-regular entry"
                    )
                total += member.size
                if total > MAX_UNPACKED_BYTES:
                    raise RuntimePreparationError(
                        "Codex package exceeds the unpacked byte limit"
                    )
                target = destination.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimePreparationError(
                        "Codex package file could not be read"
                    )
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                descriptor = os.open(target, flags, 0o600)
                with os.fdopen(descriptor, "wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                mode = 0o700 if member.mode & 0o111 else 0o600
                os.chmod(target, mode, follow_symlinks=False)
    except (OSError, tarfile.TarError) as exc:
        raise RuntimePreparationError(
            f"Codex package extraction failed: {type(exc).__name__}"
        ) from exc


def _read_package_metadata(package_root: Path) -> dict[str, Any]:
    metadata_path = package_root / "package" / "package.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimePreparationError("Codex package metadata is missing or invalid") from exc
    if metadata.get("name") != PACKAGE_NAME or metadata.get("version") != PACKAGE_VERSION:
        raise RuntimePreparationError("Codex package name or version mismatch")
    return metadata


def _verify_executable(path: Path, *, version_args: list[str], expected: str) -> str:
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimePreparationError("Codex runtime binary is missing or not executable")
    try:
        result = subprocess.run(
            [str(path), *version_args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
            shell=False,
            close_fds=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimePreparationError(
            f"Codex runtime binary probe failed: {type(exc).__name__}"
        ) from exc
    text = (result.stdout + result.stderr).decode("utf-8", errors="replace")[:500]
    if result.returncode != 0 or expected.lower() not in text.lower():
        raise RuntimePreparationError("Codex runtime binary version probe mismatch")
    return text.strip()


def prepare_runtime(install_root: Path) -> dict[str, Any]:
    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        raise RuntimePreparationError("Codex runtime preparation requires Linux x86_64")
    install_root = install_root.expanduser().absolute()
    if install_root.exists():
        manifest_path = install_root / "runtime-manifest.json"
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimePreparationError(
                "runtime destination exists without a valid manifest"
            ) from exc
        if (
            existing.get("package_sha512") != PACKAGE_SHA512
            or existing.get("codex_sha256")
            != _sha256(install_root.joinpath(*CODEX_RELATIVE_PATH.parts))
            or existing.get("bwrap_sha256")
            != _sha256(install_root.joinpath(*BWRAP_RELATIVE_PATH.parts))
        ):
            raise RuntimePreparationError("existing Codex runtime digest mismatch")
        return existing

    install_root.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    staging = Path(
        tempfile.mkdtemp(prefix="codex-runtime-prepare-", dir=install_root.parent)
    )
    published = False
    try:
        with tempfile.TemporaryDirectory(
            prefix="codex-runtime-download-", dir=install_root.parent
        ) as download_directory:
            archive_path = Path(download_directory) / "codex-linux-x64.tgz"
            package_record = _download_package(archive_path)
            _extract_package(archive_path, staging)
        extracted = staging
        package_metadata = _read_package_metadata(extracted)
        codex_path = extracted.joinpath(*CODEX_RELATIVE_PATH.parts)
        bwrap_path = extracted.joinpath(*BWRAP_RELATIVE_PATH.parts)
        codex_version = _verify_executable(
            codex_path, version_args=["--version"], expected="0.163.0"
        )
        bwrap_version = _verify_executable(
            bwrap_path, version_args=["--version"], expected="bubblewrap"
        )
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "package_name": package_metadata["name"],
            "package_version": package_metadata["version"],
            "package_url": package_record["url"],
            "package_bytes": package_record["bytes"],
            "package_sha512": package_record["sha512"],
            "codex_relative_path": CODEX_RELATIVE_PATH.as_posix(),
            "codex_sha256": _sha256(codex_path),
            "codex_version_output": codex_version,
            "bwrap_relative_path": BWRAP_RELATIVE_PATH.as_posix(),
            "bwrap_sha256": _sha256(bwrap_path),
            "bwrap_version_output": bwrap_version,
            "machine": platform.machine(),
            "kernel": platform.release(),
            "prepared_at_epoch": int(time.time()),
        }
        manifest_path = extracted / "runtime-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        os.chmod(manifest_path, 0o600)
        for current, directories, files in os.walk(extracted):
            os.chmod(current, 0o500)
            for filename in files:
                path = Path(current) / filename
                if stat.S_ISREG(path.lstat().st_mode):
                    os.chmod(path, 0o500 if os.access(path, os.X_OK) else 0o400)
        if install_root.exists():
            raise RuntimePreparationError("runtime destination appeared during install")
        # Keep the staging directory beside the destination so restricted WSL2
        # filesystems do not need to rename a directory across parent directories.
        os.replace(staging, install_root)
        published = True
        return manifest
    finally:
        if not published and staging.exists():
            for current, directories, _files in os.walk(staging, topdown=False):
                os.chmod(current, 0o700)
            shutil.rmtree(staging)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare the verified Codex CLI 0.163.0 Linux runtime."
    )
    default_root = (
        Path.home()
        / ".cache"
        / "qa-workflow-skills"
        / f"codex-{PACKAGE_VERSION}-{PACKAGE_SHA512[:12]}"
    )
    parser.add_argument("--install-root", type=Path, default=default_root)
    args = parser.parse_args(argv)
    try:
        manifest = prepare_runtime(args.install_root)
    except RuntimePreparationError as exc:
        print(f"runtime preparation failed: {exc}", file=__import__("sys").stderr)
        return 2
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
