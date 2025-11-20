import shutil
from pathlib import Path
import site
import subprocess

import sys

SRC_DIR = Path.cwd()
TEST_STEM = "locust/test"
TEST_SRC = SRC_DIR / "src" / TEST_STEM
TEST_DEST = Path(site.getsitepackages()[0]) / TEST_STEM
SKIPS = [
    "autostart_w_load_shape",
    "custom_arguments",
    "custom_exit_code",
    "default_headless_spawn_options_with_shape",
    "from_relative_path",
    "headless_spawn_options_wo_run_time",
    "no_content_length_streaming",
    "skip_logging",
    "web_options",
    "webserver",
    # added on https://github.com/conda-forge/locust-feedstock/pull/82
    "autostart_mutliple_locustfiles_with_shape",
    "graceful_exit_when_keyboard_interrupt",
    "percentile_parameter",
    "run_autostart_with_multiple_locustfiles",
    "run_with_userclass_picker",
    "worker_indexes",
    # added on https://github.com/conda-forge/locust-feedstock/pull/83
    "autostart_w_run_time",
    "autostart_wo_run_time",
    "run_headless_with_multiple_locustfiles",
    # added on https://github.com/conda-forge/locust-feedstock/pull/87
    "workers_shut_down_if_master_is_gone",
    # added on https://github.com/conda-forge/locust-feedstock/pull/88
    "processes_ctrl_c",
    "processes_workers_quit_unexpected"
    # added on https://github.com/conda-forge/locust-feedstock/pull/90
    "client_recv",
    "client_send",
    # added on https://github.com/conda-forge/locust-feedstock/pull/94
    "locustfile_from_url",
    # added on https://github.com/conda-forge/locust-feedstock/pull/103
    "(ZMQRPC_tests and constructor)",
    # added on https://github.com/conda-forge/locust-feedstock/pull/119
    "format_utc_timestamp",
    # added on https://github.com/conda-forge/locust-feedstock/pull/145
    "test_client_pool_concurrency",
    # added on https://github.com/conda-forge/locust-feedstock/pull/171
    "processes_workers_quit_unexpected",
    # added on https://github.com/conda-forge/uv-feedstock/pull/265
    "unknown_command_line_arg",
    "warning_with_lower_user_count_than_fixed_count",
    # hotfix after https://github.com/conda-forge/locust-feedstock/pull/185
    "json_file",
    # added on https://github.com/conda-forge/locust-feedstock/pull/187
    "json_schema"
]


def main():
    print("... copying tests into site packages (ick)", flush=True)
    shutil.copytree(TEST_SRC, TEST_DEST)
    args = [
        "pytest",
        "-vv",
        "--color=yes",
        "--tb=long",
        "--pyargs",
        "locust",
        "-k",
        f"""not ({" or ".join(SKIPS)})""",
    ]
    print(">>>", *args, flush=True)
    return subprocess.call(args)


if __name__ == "__main__":
    sys.exit(main())
