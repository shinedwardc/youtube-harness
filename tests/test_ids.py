"""Every common YouTube link shape resolves to the same 11-character ID; anything else is rejected."""

import pytest

from harness.plugins.youtube.ids import parse_video_id

ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "raw",
    [
        ID,
        f"https://www.youtube.com/watch?v={ID}",
        f"https://youtube.com/watch?v={ID}&t=42s&list=PL123",
        f"https://m.youtube.com/watch?feature=share&v={ID}",
        f"https://music.youtube.com/watch?v={ID}",
        f"https://youtu.be/{ID}?si=abcdef",
        f"https://www.youtube.com/shorts/{ID}",
        f"https://www.youtube.com/embed/{ID}",
        f"https://www.youtube.com/live/{ID}?feature=share",
        f"youtube.com/watch?v={ID}",
        f"  https://youtu.be/{ID}  ",
    ],
)
def test_accepts_known_link_shapes(raw):
    assert parse_video_id(raw) == ID


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not a link",
        "https://vimeo.com/123456",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/@SomeChannel",
        f"https://evil.example/watch?v={ID}",
    ],
)
def test_rejects_anything_else(raw):
    with pytest.raises(ValueError):
        parse_video_id(raw)
