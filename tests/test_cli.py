"""yt-sum: the note's path alone on stdout, readable progress on stderr, and an exit code per outcome."""

from datetime import date

import pytest

from harness import cli
from harness.bootstrap import Harness
from harness.core.config import Settings
from harness.core.llm import ConfigError
from harness.core.plugin import Unprocessable
from harness.plugins.youtube import YouTubePlugin
from tests.conftest import FakeLLM, abandon

URL = "https://youtu.be/dQw4w9WgXcQ"


@pytest.fixture
def use_harness(monkeypatch, store, vault):
    """Point yt-sum at a harness built from fakes instead of the real environment."""

    def install(plugin):
        harness = Harness(
            settings=Settings(vault_dir=vault, db_path=store.path, summary_language="auto", poll_interval=0.1),
            store=store,
            plugins={"youtube": plugin},
            llms=[FakeLLM()],
        )
        monkeypatch.setattr(cli, "build", lambda: harness)
        monkeypatch.setattr(cli, "load_dotenv", lambda: None)

    return install


def test_done_prints_steps_then_only_the_path_on_stdout(use_harness, plugin, vault, capsys):
    use_harness(plugin)

    assert cli.main([URL]) == cli.EXIT_DONE

    out, err = capsys.readouterr()
    month = date.today().strftime("%Y-%m")
    assert out.strip() == str(vault / f"youtube/{month}/how-raft-works-dQw4w9WgXcQ.md")
    assert "▸ Fetching youtube dQw4w9WgXcQ" in err
    assert "▸ Summarizing with fake:model" in err
    assert "✓ Done in" in err
    assert "INFO" not in err
    # Captured output isn't a terminal, so no colour codes.
    assert "\033[" not in err


def test_second_run_says_already_summarized(use_harness, plugin, capsys):
    use_harness(plugin)
    cli.main([URL])
    capsys.readouterr()

    assert cli.main([URL]) == cli.EXIT_DONE

    out, err = capsys.readouterr()
    assert out.strip().endswith("dQw4w9WgXcQ.md")
    assert "✓ Already summarized" in err
    assert "Fetching" not in err


def test_no_captions_exits_2_and_says_so_once(use_harness, capsys):
    def fetcher(video_id):
        raise Unprocessable("needs_transcription", "The video has no creator captions or auto-captions")

    use_harness(YouTubePlugin(fetcher=fetcher))

    assert cli.main([URL]) == cli.EXIT_NEEDS_TRANSCRIPTION

    out, err = capsys.readouterr()
    assert out == ""
    assert "! Needs transcription (job 1)" in err
    assert err.count("no creator captions") == 1


def test_failure_exits_1_without_a_traceback_unless_verbose(use_harness, capsys):
    def fetcher(video_id):
        raise RuntimeError("yt-dlp exploded")

    use_harness(YouTubePlugin(fetcher=fetcher))

    assert cli.main([URL]) == cli.EXIT_FAILED

    err = capsys.readouterr().err
    assert "✗ Failed (job 1)" in err
    assert "RuntimeError: yt-dlp exploded" in err
    assert "Traceback" not in err
    assert "-v" in err


def test_verbose_failure_shows_the_traceback(use_harness, capsys):
    use_harness(YouTubePlugin(fetcher=lambda video_id: (_ for _ in ()).throw(RuntimeError("boom"))))

    cli.main(["-v", URL])

    assert "Traceback" in capsys.readouterr().err


def test_takes_over_a_job_abandoned_by_a_dead_process(use_harness, plugin, store, capsys):
    use_harness(plugin)
    job = store.create_job("youtube", "dQw4w9WgXcQ", URL)
    store.claim(job.id)
    abandon(store, job.id)

    assert cli.main([URL]) == cli.EXIT_DONE

    assert store.get_job(job.id).status == "done"
    assert "already running elsewhere" in capsys.readouterr().err


def test_ctrl_c_exits_cleanly_and_the_link_can_be_sent_again(use_harness, plugin, capsys):
    def fetcher(video_id):
        raise KeyboardInterrupt

    use_harness(YouTubePlugin(fetcher=fetcher))

    assert cli.main([URL]) == cli.EXIT_INTERRUPTED

    out, err = capsys.readouterr()
    assert out == ""
    assert "✗ Interrupted" in err
    assert "Traceback" not in err

    use_harness(plugin)
    assert cli.main([URL]) == cli.EXIT_DONE


def test_backfill_stores_transcripts_and_prints_nothing_on_stdout(use_harness, plugin, store, capsys):
    use_harness(plugin)
    job = store.claim(store.create_job("youtube", "dQw4w9WgXcQ", URL).id)
    store.finish(job, "youtube/note.md", {"title": "Old video"})

    assert cli.main(["--backfill-transcripts"]) == cli.EXIT_DONE

    out, err = capsys.readouterr()
    assert out == ""
    assert "✓ Stored 1 transcript(s)" in err
    assert store.get_source_text("youtube", "dQw4w9WgXcQ")


def test_backfill_exits_1_when_a_video_fails(use_harness, store, capsys):
    use_harness(YouTubePlugin(fetcher=lambda video_id: (_ for _ in ()).throw(RuntimeError("gone"))))
    job = store.claim(store.create_job("youtube", "dQw4w9WgXcQ", URL).id)
    store.finish(job, "youtube/note.md", {"title": "Old video"})

    assert cli.main(["--backfill-transcripts"]) == cli.EXIT_FAILED

    err = capsys.readouterr().err
    assert "gone" in err
    assert "1 failed" in err


@pytest.mark.parametrize("argv", [[], [URL, "--backfill-transcripts"]])
def test_needs_exactly_one_of_a_link_or_the_backfill(argv, capsys):
    with pytest.raises(SystemExit):
        cli.main(argv)
    assert "either a link or --backfill-transcripts" in capsys.readouterr().err


def test_invalid_link_exits_1(use_harness, plugin, capsys):
    use_harness(plugin)

    assert cli.main(["https://vimeo.com/1"]) == cli.EXIT_FAILED
    assert "✗ Not a YouTube video link" in capsys.readouterr().err


def test_missing_key_exits_1(monkeypatch, capsys):
    def build():
        raise ConfigError("No API key for provider 'gemini'. Set GEMINI_API_KEY in .env.")

    monkeypatch.setattr(cli, "build", build)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)

    assert cli.main([URL]) == cli.EXIT_FAILED
    assert "✗ No API key" in capsys.readouterr().err


def test_colour_only_on_a_terminal(monkeypatch):
    class Terminal:
        def isatty(self):
            return True

    monkeypatch.delenv("NO_COLOR", raising=False)
    assert cli.Paint(Terminal())("ok", cli.GREEN) == "\033[32mok\033[0m"
    monkeypatch.setenv("NO_COLOR", "1")
    assert cli.Paint(Terminal())("ok", cli.GREEN) == "ok"
