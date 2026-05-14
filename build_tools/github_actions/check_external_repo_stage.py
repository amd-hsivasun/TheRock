#!/usr/bin/env python3
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""Check if a build stage needs an external repo checkout."""

import argparse
import json
import sys

from github_actions_api import gha_set_output


def main():
    parser = argparse.ArgumentParser(description="Check if stage needs external repo")
    parser.add_argument(
        "--external-repo-config",
        default="",
        help="JSON config from detect_external_repo_config.py (empty if no external repo)",
    )
    parser.add_argument(
        "--stage",
        required=True,
        help="Current build stage name",
    )
    args = parser.parse_args()

    # Handle empty config (no external repo)
    if not args.external_repo_config:
        print("No external repo config provided")
        gha_set_output({"needs_checkout": "false"})
        return 0

    config = json.loads(args.external_repo_config)
    stages = config.get("stages", [])
    needs_checkout = args.stage in stages

    print(f"Stage '{args.stage}' needs external repo: {needs_checkout}")
    print(f"Configured stages: {stages}")

    outputs = {"needs_checkout": str(needs_checkout).lower()}
    if needs_checkout:
        outputs["fetch_sources_args"] = config.get("fetch_sources_args", "")
        outputs["repository"] = config.get("repository", "")
        outputs["ref"] = config.get("ref", "")
        outputs["checkout_path"] = config.get("checkout_path", "")
        # Generate cmake_args for the external repo source dir
        source_package = config.get("source_package", "")
        checkout_path = config.get("checkout_path", "")
        if source_package and checkout_path:
            outputs["cmake_args"] = (
                f"-DTHEROCK_{source_package}_SOURCE_DIR={checkout_path}"
            )

    gha_set_output(outputs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
