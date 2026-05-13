#!/usr/bin/env python3
"""
Detect failed build logs and rename them so they appear first in directory listings.

This script is intended for CI/CD systems such as GitHub Actions.

Behavior:
---------
1. Scan all *.log files under:
       $OUTPUT_DIR/build/logs

2. Detect logs containing an END line with a non-zero exit code.
   Expected format:

       END<TAB>duration<TAB>something<TAB>exit_code

   Example success:
       END    12.3    44.1    0

   Example failure:
       END    12.3    44.1    2

3. Rename failed logs:
       build.log
   ->
       0.error.build.log

   The "0.error." prefix ensures failed logs sort first
   alphabetically in file listings and artifacts.

4. Append a Markdown summary to:
       $GITHUB_STEP_SUMMARY

   so the failed logs are easy to find in the GitHub Actions UI.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Regex explanation:
#
# ^END                   -> line must start with "END"
# \t                     -> followed by a tab
# [0-9.]+                -> floating-point-like number
# \t
# [0-9.]+                -> another floating-point-like number
# \t
# [1-9][0-9]*            -> non-zero integer exit code
# $                      -> end of line
#
# This intentionally ignores logs whose exit code is 0.
#
FAILED_END_RE = re.compile(r"^END\t[0-9.]+\t[0-9.]+\t[1-9][0-9]*$")


def find_failed_logs(log_dir: Path) -> list[Path]:
    """
    Scan all .log files and return the ones containing
    a failure END line.

    Parameters
    ----------
    log_dir:
        Directory containing build log files.

    Returns
    -------
    list[Path]
        List of failed log file paths.
    """

    failed: list[Path] = []

    # Iterate over all *.log files in the directory.
    for path in log_dir.glob("*.log"):

        try:
            # Open safely:
            # - utf-8 decoding
            # - replace invalid bytes instead of crashing
            with path.open(
                "r",
                encoding="utf-8",
                errors="replace",
            ) as f:

                # Read line-by-line instead of loading entire file
                # into memory. This scales better for large logs.
                for line in f:

                    # Remove trailing newline before regex matching.
                    if FAILED_END_RE.match(line.rstrip("\n")):

                        # Mark this log as failed.
                        failed.append(path)

                        # Stop scanning this file once a failure
                        # has been detected.
                        break

        except OSError:
            # Ignore unreadable/missing files.
            #
            # Common reasons:
            # - permission issue
            # - file removed during scan
            # - broken symlink
            #
            # CI scripts usually prefer resilience over hard failure.
            continue

    return failed


def main() -> int:
    """
    Main workflow:
      - locate logs
      - find failures
      - rename failed logs
      - update GitHub summary
    """

    # Environment variables provided by GitHub Actions.
    #
    # Example:
    #   OUTPUT_DIR=/tmp/work/output
    #   GITHUB_STEP_SUMMARY=/tmp/github_summary.txt
    #
    logs_dir = Path(os.environ["OUTPUT_DIR"]) / "build" / "logs"

    summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"])

    # Find all logs whose END line reports a failure.
    failed_logs = find_failed_logs(logs_dir)

    # Nothing failed -> exit successfully.
    if not failed_logs:
        print("No failed log found.")
        return 0

    # Open GitHub step summary in append mode.
    #
    # GitHub renders this Markdown nicely in the Actions UI.
    with summary_path.open("a", encoding="utf-8") as summary:

        summary.write("## Build failure\n")
        summary.write(f"**Error logs:** {len(failed_logs)}\n\n")

        # Process each failed log.
        for src in failed_logs:

            # Rename:
            #
            #   build.log
            # -> 0.error.build.log
            #
            # Prefix chosen so failed logs appear first when sorted.
            #
            dst = src.with_name(f"0.error.{src.name}")

            try:
                # Rename file in-place.
                src.rename(dst)

                print(f"Renamed {src.name} -> {dst.name}")

                # Add bullet item to GitHub summary.
                summary.write(f"- `{dst.name}`\n\n")

            except OSError as e:
                # Continue processing remaining logs even if
                # one rename operation fails.
                print(f"Failed to rename {src}: {e}")

    return 0


if __name__ == "__main__":
    # Convert returned integer into process exit code.
    raise SystemExit(main())
