"""yt-sum <url>: summarize one video into the vault, in this process, and print the note's path.

Progress goes to stderr; stdout gets only the note's path, so `yt-sum <url> | xargs ...` works.
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

from .bootstrap import build
from .core.jobs import STALE_AFTER, run, submit, wait
from .core.llm import ConfigError

EXIT_DONE = 0
EXIT_FAILED = 1
EXIT_NEEDS_TRANSCRIPTION = 2
# The shell convention for a process stopped by Ctrl+C (128 + SIGINT).
EXIT_INTERRUPTED = 130

# ANSI colour codes.
RED, GREEN, YELLOW, CYAN, DIM = "31", "32", "33", "36", "2"


class Paint:
    """Colours text when stderr is a terminal, and leaves it plain otherwise or under NO_COLOR."""

    def __init__(self, stream):
        self.enabled = stream.isatty() and "NO_COLOR" not in os.environ

    def __call__(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text


class ProgressFormatter(logging.Formatter):
    """Turns log records into progress lines: ▸ for job steps, ! for warnings, ✗ for errors."""

    def __init__(self, paint: Paint, verbose: bool):
        super().__init__()
        self.paint = paint
        self.verbose = verbose

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.levelno >= logging.ERROR:
            line = f"{self.paint('✗', RED)} {message}"
        elif record.levelno >= logging.WARNING or record.name.startswith("openai"):
            # The OpenAI SDK reports its retries ("Retrying request in 0.5 seconds") at INFO.
            line = f"{self.paint('!', YELLOW)} {message}"
        elif record.levelno >= logging.INFO and record.name == "harness.core.jobs":
            # The job's own steps: fetching, summarizing, wrote.
            line = f"{self.paint('▸', CYAN)} {message}"
        elif record.levelno >= logging.INFO:
            # Details from inside a step, such as which captions were used.
            line = "  " + self.paint(message, DIM)
        else:
            line = "  " + self.paint(f"{record.name}: {message}", DIM)

        if self.verbose and record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging(verbose: bool) -> Paint:
    paint = Paint(sys.stderr)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ProgressFormatter(paint, verbose))
    if not verbose:
        # The summary printed at the end already says how the job ended.
        handler.addFilter(lambda record: not getattr(record, "outcome", False))
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, handlers=[handler], force=True)
    if not verbose:
        for noisy in ("yt_dlp", "httpx", "httpx2"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
        # INFO, not WARNING, so retries show; its per-request DEBUG lines stay hidden.
        logging.getLogger("openai").setLevel(logging.INFO)
    return paint


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="yt-sum", description="Summarize a YouTube video into a note in your Obsidian vault."
    )
    parser.add_argument("url", help="A YouTube link or an 11-character video ID")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show debug logs, including yt-dlp's")
    args = parser.parse_args(argv)

    paint = setup_logging(args.verbose)

    def say(symbol: str, code: str, text: str) -> None:
        print(f"{paint(symbol, code)} {text}", file=sys.stderr)

    started = time.monotonic()
    load_dotenv()
    try:
        harness = build()
    except ConfigError as error:
        say("✗", RED, str(error))
        return EXIT_FAILED

    plugin = harness.plugins["youtube"]
    vault_dir = harness.settings.vault_dir
    try:
        submission = submit(harness.store, plugin, args.url)
    except ValueError as error:
        say("✗", RED, str(error))
        return EXIT_FAILED

    if submission.summary is not None:
        say("✓", GREEN, paint("Already summarized", GREEN))
        print(vault_dir / submission.summary.note_path)
        return EXIT_DONE

    job_id = submission.job.id
    try:
        while True:
            job = harness.store.claim(job_id)
            if job is not None:
                job = run(job, store=harness.store, plugin=plugin, llms=harness.llms, vault_dir=vault_dir)
                break
            # The server's worker (or another yt-sum) has it already. If that process died,
            # wait() puts the job back in the queue and this loop claims it.
            minutes = int(STALE_AFTER.total_seconds() // 60)
            say("…", CYAN, f"Job {job_id} is already running elsewhere; waiting for it")
            print("  " + paint(f"If that process died, this run takes over within {minutes} minutes.", DIM), file=sys.stderr)
            job = wait(harness.store, job_id)
            if job.finished:
                break
    except KeyboardInterrupt:
        say("✗", RED, paint("Interrupted", RED))
        return EXIT_INTERRUPTED

    elapsed = time.monotonic() - started
    if job.status == "done":
        say("✓", GREEN, paint(f"Done in {elapsed:.1f}s", GREEN))
        print(vault_dir / job.note_path)
        return EXIT_DONE
    if job.status == "needs_transcription":
        say("!", YELLOW, paint(f"Needs transcription (job {job.id})", YELLOW))
        print("  " + paint(job.error, DIM), file=sys.stderr)
        return EXIT_NEEDS_TRANSCRIPTION

    say("✗", RED, paint(f"Failed (job {job.id})", RED))
    print("  " + paint(job.error, DIM), file=sys.stderr)
    if not args.verbose:
        print("  " + paint("Run again with -v for the full traceback.", DIM), file=sys.stderr)
    return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
