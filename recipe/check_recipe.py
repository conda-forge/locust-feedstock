import os
import tarfile
import subprocess
import re
from io import StringIO
from difflib import unified_diff
from urllib.request import urlretrieve
from pathlib import Path
from ruamel.yaml import YAML as YAML_
from typing import Any
from tempfile import TemporaryDirectory

import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

YAML = YAML_(typ="rt")
YAML.width = 4096
YAML.preserve_quotes = True
YAML.default_flow_style = False
YAML.explicit_start = False
YAML.indent(mapping=2, sequence=4, offset=2)

PPT = "pyproject.toml"

UTF8 = dict(encoding="utf-8")
PKG_NAME = "locust"
PKG_MOD = PKG_NAME.replace("-", "_")
PKG_PREFIX = f"{PKG_NAME}-with"
RECIPE_DIR = Path(__file__).parent

RECIPE_YAML = RECIPE_DIR / "recipe.yaml"
RECIPE_TEXT = RECIPE_YAML.read_text(**UTF8).strip()
RECIPE = YAML.load(RECIPE_TEXT)
SKIP_EXTRAS = {}
SUMMARY_VAR = "${{ summary }}"

RE_PYPI_CONDA = {
    r"^(.*?)(?=[=<>])": r"\1 ",
    ", ": ",",
    r"^msgpack": "msgpack-python",
    ";.*$": "",
    r"\[client\]": "",
    "^cryptography.*$": "cryptography",
}
PYTHON_MIN_EXACT = "python ${{ python_min }}.*"
PYTHON_MIN_GTE = "python >=${{ python_min }}"
PIP_INSTALL = (
    "${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation"
    " --disable-pip-version-check"
    " --check-build-dependencies"
)


def get_pyproject_data() -> dict[str, Any]:
    src_dir = os.environ.get("SRC_DIR")
    if src_dir:
        ppt_text = (Path(src_dir) / "pyproject.toml").read_text(**UTF8)
    else:
        url = RECIPE["source"][0]["url"].replace(
            "${{ version }}", RECIPE["context"]["version"]
        )
        with TemporaryDirectory() as td:
            tdp = Path(td)
            tgz = tdp / Path(url).name
            urlretrieve(url, filename=f"{tgz}")
            with tarfile.open(tgz, "r:gz") as tf:
                for member in tf.getmembers():
                    if not member.name.endswith(PPT):
                        continue
                    ppt_text = tf.extractfile(member).read().decode(**UTF8)
                    break

    return tomllib.loads(ppt_text)


def to_conda(all_raw: list[str], extra_conda: list[str] | None = None) -> str:
    conda: list[str] = []
    for raw in all_raw:
        raw = raw.lower()
        for pattern, repl in RE_PYPI_CONDA.items():
            raw = re.sub(pattern, repl, raw)
        conda += [raw]
    return sorted([*conda, *(extra_conda or [])])


def pip_check() -> dict[str, Any]:
    return {
        "python": {
            "imports": PKG_MOD,
            "pip_check": True,
            "python_version": ["${{ python_min }}.*", "${{ python_check_max }}.*"],
        }
    }


def cli_check() -> dict[str, Any]:
    return {
        "requirements": {"run": [PYTHON_MIN_EXACT]},
        "script": ["locust --version", "locust --help"],
    }

def package_contents() -> dict[str, Any]:
    return {
        "package_contents": {
            "strict": True,
            "site_packages": ["locust/**", "locust-${{ version }}.dist-info/**"]
        }
    }

def pin_subpackage(other: str) -> str:
    return """${{ pin_subpackage("%s", exact=True) }}""" % other


def build_core(build_deps: list[str], run_deps: list[str]) -> dict[str, Any]:
    run = [
        r
        for r in to_conda(run_deps, [PYTHON_MIN_GTE])
    ]

    return {
        "package": {"name": PKG_NAME},
        "build": {
            "noarch": "python",
            "script": {
                "env": {
                    "SKIP_PRE_BUILD": "true",
                },
                "content": [
                    "cd dist",
                    PIP_INSTALL,
                ],
            },
            "python": {"entry_points": ["locust = locust.main:main"]},
        },
        "requirements": {
            "host": to_conda(build_deps, [PYTHON_MIN_EXACT, "pip"]),
            "run": run,
        },
        "tests": [
            package_contents(),
            pip_check(),
            cli_check()
        ],
        "about": {
            "description": RECIPE["outputs"][0]["about"]["description"]
        }
    }


def build_extra(extra: str, run_deps: list[str]) -> dict[str, Any]:
    return {
        "package": {"name": f"{PKG_PREFIX}-{extra}"},
        "build": {"noarch": "generic"},
        "requirements": {"run": to_conda(run_deps, [pin_subpackage(PKG_NAME)])},
        "tests": [pip_check()],
        "about": {
            "summary": f"""{SUMMARY_VAR} (with [{extra}])""",
        },
    }


def build_all(
    outputs: list[dict[str, str]],
    test_deps: list[str],
) -> dict[str, Any]:
    output_name = f"{PKG_PREFIX}-all"
    with_outputs = [
        pin_subpackage(output["package"]["name"])
        for output in outputs
        if output["package"]["name"] not in [output_name]
    ]

    return {
        "package": {"name": output_name},
        "build": {"noarch": "generic"},
        "requirements": {"run": sorted(with_outputs)},
        "tests": [
            pip_check(),
            {
                "files": {"source": ["src/locust/test/"]},
                "requirements": {
                    "run": to_conda(test_deps, [PYTHON_MIN_EXACT, "pytest-cov"])
                },
                "script": {"file": "run_test.py"},
            },
        ],
        "about": {
            "summary": f"""{SUMMARY_VAR} (with [all])""",
        },
    }


def diff_no_whitespace(old: str, new: str) -> str:
    old_lines, new_lines = [
        [line for line in text.splitlines() if line]
        for text in [old, new]
    ]
    return "\n".join(unified_diff(old_lines, new_lines))

def main(*, write: bool = False, lint: bool = False, build: bool = False) -> int:
    ppt = get_pyproject_data()
    proj = ppt["project"]
    RECIPE["about"]["license"] = f"""{ppt["project"]["license"]["text"]}"""
    extras = {
        k: v for k, v in proj["optional-dependencies"].items() if k not in SKIP_EXTRAS
    }

    outputs = [
        build_core(ppt["build-system"]["requires"], proj["dependencies"]),
        *[build_extra(extra, deps) for extra, deps in extras.items()],
    ]

    RECIPE["outputs"] = [
        *outputs,
        build_all([*outputs], ppt["dependency-groups"]["test"]),
    ]

    io = StringIO()
    YAML.dump(RECIPE, io)
    new_text = io.getvalue().strip()

    diff = diff_no_whitespace(RECIPE_TEXT, new_text)

    rc = 1
    if not diff:
        print("... no change")
        rc = 0
    else:
        print(diff)

        if write:
            RECIPE_YAML.write_text(new_text + "\n", **UTF8)
            print("... wrote", RECIPE_YAML)
        else:
            print("\n!!! run again with --write to update recipe.yaml")
            return 1

    if not rc and lint:
        rc = subprocess.call(["pixi", "run", "lint"])

    if not rc and build:
        rc = subprocess.call(["pixi", "run", "build-linux", "linux64"])

    return rc


if __name__ == "__main__":
    sys.exit(
        main(
            write="--write" in sys.argv,
            lint="--lint" in sys.argv,
            build="--build" in sys.argv,
        )
    )
