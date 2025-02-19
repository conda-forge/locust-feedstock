from __future__ import annotations
import os
import sys
from pathlib import Path
from subprocess import check_call
import site
import shutil

os.environ.update(
    SETUPTOOLS_SCM_PRETEND_VERSION=os.environ["PKG_VERSION"], SKIP_PRE_BUILD="true"
)

SITE_PACKAGES = Path(site.getsitepackages()[0])
UI = "locust/webui"

PIP_INSTALL = [
    sys.executable,
    "-m",
    "pip",
    "install",
    ".",
    "-vv",
    "--no-deps",
    "--no-build-isolation",
    "--disable-pip-version-check",
]


def do(*args, cwd: str | None = None) -> None:
    print(">>>", *args)
    check_call(args, cwd=cwd)


def main() -> int:
    Path("package.json").unlink()
    do(["yarn"], cwd=UI)
    do(["yarn", "build"], cwd=UI)
    do(PIP_INSTALL)
    for path in [*(SITE_PACKAGES / UI).glob("*"), SITE_PACKAGES / "uv.lock"]:
        if path.name == "dist":
            continue
        print("... removing", path)
        if path.is_dir():
            shutil.rmtree(path)
        if path.is_file():
            path.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
