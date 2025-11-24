from pathlib import Path
import sys
import os

SRC_DIR = os.environ["SRC_DIR"]
LOCUST_CLOUD_MIN = os.environ["LOCUST_CLOUD_MIN"]

UTF8 = {"encoding": "utf-8"}

PPT = Path(SRC_DIR) / "dist/pyproject.toml"


def patch_locust_cloud() -> int:
    lc_spec = f'"locust-cloud>={LOCUST_CLOUD_MIN}"'
    text = PPT.read_text(**UTF8)
    if lc_spec not in text:
        print(
            f""" {text}

            !!! {lc_spec} not in {PPT}
                
                please update recipe.yaml#/context/locust_cloud_min
            """
        )
        return 1
    text = text.replace(lc_spec, f"# {lc_spec}")
    PPT.write_text(text, **UTF8)
    return 0


if __name__ == "__main__":
    sys.exit(patch_locust_cloud())
