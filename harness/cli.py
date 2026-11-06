"""yt-sum <url>: summarize one video into the vault, in this process, and print the note's path."""

import argparse
import logging
import sys

from dotenv import load_dotenv

from .bootstrap import build
from .core.jobs import run, submit, wait
from .core.llm import ConfigError

EXIT_DONE = 0
EXIT_FAILED = 1
EXIT_NEEDS_TRANSCRIPTION = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="yt-sum", description="Summarize a YouTube video into a note in your Obsidian vault."
    )
    parser.add_argument("url", help="A YouTube link or an 11-character video ID")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show debug logs, including yt-dlp's")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if not args.verbose:
        for noisy in ("yt_dlp", "httpx", "httpx2", "openai"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    load_dotenv()
    try:
        harness = build()
    except ConfigError as error:
        print(f"yt-sum: {error}", file=sys.stderr)
        return EXIT_FAILED

    plugin = harness.plugins["youtube"]
    vault_dir = harness.settings.vault_dir
    try:
        submission = submit(harness.store, plugin, args.url)
    except ValueError as error:
        print(f"yt-sum: {error}", file=sys.stderr)
        return EXIT_FAILED

    if submission.summary is not None:
        print("Already summarized.", file=sys.stderr)
        print(vault_dir / submission.summary.note_path)
        return EXIT_DONE

    job = harness.store.claim(submission.job.id)
    if job is None:
        # The server's worker (or another yt-sum) has it already.
        print(f"Job {submission.job.id} is already running elsewhere; waiting for it.", file=sys.stderr)
        job = wait(harness.store, submission.job.id)
    else:
        job = run(job, store=harness.store, plugin=plugin, llms=harness.llms, vault_dir=vault_dir)

    if job.status == "done":
        print(vault_dir / job.note_path)
        return EXIT_DONE
    print(f"yt-sum: job {job.id} ended as {job.status}: {job.error}", file=sys.stderr)
    return EXIT_NEEDS_TRANSCRIPTION if job.status == "needs_transcription" else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
