"""VTT cleaning: tags and repeats go, a [mm:ss] marker stays about once a minute."""

from harness.plugins.youtube.transcript import clean_vtt, format_time, parse_time, parse_vtt

CREATOR_VTT = """WEBVTT
Kind: captions
Language: en

NOTE this block is ignored

00:00:01.000 --> 00:00:04.000
Welcome to <b>the</b> video &amp; thanks

00:00:30.000 --> 00:00:33.000
Today: Raft.

00:01:05.000 --> 00:01:08.000
Leader election comes first.
"""

# Real yt-dlp auto-captions, trimmed: each cue repeats the previous line, new words carry
# timing tags, and a line holding one space follows the timing.
AUTO_VTT = (
    "WEBVTT\nKind: captions\nLanguage: en\n\n"
    "00:00:04.280 --> 00:00:06.830 align:start position:0%\n \n"
    "This<00:00:04.760><c> is</c><00:00:04.960><c> a</c><00:00:05.000><c> three.</c>\n\n"
    "00:00:06.830 --> 00:00:06.840 align:start position:0%\nThis is a three.\n \n\n"
    "00:00:06.840 --> 00:00:08.350 align:start position:0%\nThis is a three.\n"
    "and<00:00:07.040><c> rendered</c><00:00:07.360><c> at</c>\n\n"
    "00:00:08.350 --> 00:00:08.360 align:start position:0%\nand rendered at\n \n"
)


def test_creator_captions_lose_tags_and_entities():
    assert [text for _, text in parse_vtt(CREATOR_VTT)] == [
        "Welcome to the video & thanks",
        "Today: Raft.",
        "Leader election comes first.",
    ]


def test_rolling_auto_captions_keep_each_line_once_with_its_own_start():
    assert parse_vtt(AUTO_VTT) == [(4.28, "This is a three."), (6.84, "and rendered at")]


def test_markers_start_a_new_paragraph_each_minute():
    assert clean_vtt(CREATOR_VTT) == (
        "[00:01] Welcome to the video & thanks Today: Raft.\n\n[01:05] Leader election comes first."
    )


def test_hour_long_videos_use_hours_in_markers():
    assert format_time(3725) == "1:02:05"
    assert format_time(190) == "03:10"


def test_parse_time_round_trips_and_rejects_junk():
    assert parse_time("03:10") == 190
    assert parse_time("1:02:05") == 3725
    assert parse_time("about 3 minutes") is None


def test_empty_file_gives_empty_text():
    assert clean_vtt("WEBVTT\n\n") == ""
