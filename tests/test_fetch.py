"""Caption track choice: creator captions first, then the original-language auto-captions only."""

from harness.plugins.youtube.fetch import choose_track


def formats(lang):
    return [{"ext": "json3", "url": f"json3-{lang}"}, {"ext": "vtt", "url": f"vtt-{lang}"}]


def test_prefers_creator_captions_in_the_video_language():
    info = {
        "language": "ko",
        "subtitles": {"en": formats("en"), "ko": formats("ko")},
        "automatic_captions": {"ko-orig": formats("ko-orig")},
    }
    track = choose_track(info)
    assert (track.kind, track.language, track.url) == ("creator", "ko", "vtt-ko")


def test_matches_regional_creator_tracks_by_base_language():
    info = {"language": "en", "subtitles": {"en-US": formats("en-US")}}
    assert choose_track(info).language == "en"


def test_ignores_live_chat_replay():
    info = {"language": "en", "subtitles": {"live_chat": formats("live_chat")}, "automatic_captions": {}}
    assert choose_track(info) is None


def test_falls_back_to_original_auto_captions_not_translations():
    info = {
        "language": "ko",
        "subtitles": {},
        # Translations are listed first on purpose.
        "automatic_captions": {"en": formats("en"), "ko-orig": formats("ko-orig"), "ko": formats("ko")},
    }
    track = choose_track(info)
    assert (track.kind, track.language, track.url) == ("auto", "ko", "vtt-ko-orig")


def test_finds_the_orig_track_when_the_video_language_is_unknown():
    info = {"automatic_captions": {"de": formats("de"), "ja-orig": formats("ja-orig")}}
    assert choose_track(info).language == "ja"


def test_no_captions_at_all():
    assert choose_track({"language": "en", "subtitles": {}, "automatic_captions": {}}) is None


def test_skips_tracks_without_vtt():
    info = {"language": "en", "subtitles": {"en": [{"ext": "srv3", "url": "x"}]}, "automatic_captions": {}}
    assert choose_track(info) is None
