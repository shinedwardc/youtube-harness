"""The web page in a real headless browser, served by the real app from a temporary database.

One-time setup:  uv run playwright install chromium --only-shell
Only these:      uv run pytest -m browser
Skip these:      uv run pytest -m "not browser"

Every run uses the same videos, window size and fallback fonts, because nothing is loaded from
the internet. So a failure means the page changed, not YouTube or Google Fonts.
"""

import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import Page, expect

from harness.api import create_app
from harness.bootstrap import Harness
from harness.core.config import Settings
from tests.conftest import FakeLLM

pytestmark = pytest.mark.browser

LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
HIGHLIGHTS = ["Leaders win by majority vote", "Leaders replicate the log", "Followers stay in sync"]
KEY_POINTS = ["A leader is elected by majority vote.", "Logs are replicated.", "Clients talk to the leader.", "A fourth."]
LONG_TITLE = "A hundred character title that is as long as YouTube allows for any video, so it has to wrap a lot!!"

ALL_BOXES_MATCH = """() => {
    const heights = [...document.querySelectorAll('.tile')].map((tile) => tile.getBoundingClientRect().height);
    return Math.max(...heights) - Math.min(...heights) < 0.1;
}"""


def save_video(store, video_id, **fields):
    job = store.create_job("youtube", video_id, f"https://youtu.be/{video_id}")
    store.claim(job.id)
    data = {
        "video_id": video_id,
        "title": "How Raft Works",
        "channel": "Example Channel",
        "category": "Education",
        "tldr": "Raft elects a leader and replicates a log to its followers.",
        "highlights": HIGHLIGHTS,
        "key_points": KEY_POINTS,
        "timestamps": [{"time": "01:00", "label": "Leader election"}],
        "tags": ["consensus"],
        "summarized": "2026-11-06",
    }
    store.finish(job, f"youtube/{video_id}.md", data | fields)


@pytest.fixture
def browser_context_args(browser_context_args):
    return {**browser_context_args, "permissions": ["clipboard-read", "clipboard-write"]}


@pytest.fixture
def site(store, plugin, vault):
    """The real app on a free port, with the worker off, so a submitted link just stays queued."""
    save_video(store, "aaaaaaaaaaa", title="Short", highlights=["One thing"])
    save_video(store, "bbbbbbbbbbb", title=LONG_TITLE)
    save_video(store, "ccccccccccc", title="An older summary", highlights=[])
    save_video(store, "ddddddddddd", title="From another month", summarized="2026-10-02")
    failed = store.create_job("youtube", "eeeeeeeeeee", "https://youtu.be/eeeeeeeeeee")
    store.set_status(failed.id, "failed", error="HTTP Error 429: Too Many Requests")

    harness = Harness(
        settings=Settings(vault_dir=vault, db_path=store.path, summary_language="auto", poll_interval=0.1),
        store=store,
        plugins={"youtube": plugin},
        llms=[FakeLLM()],
    )
    server = uvicorn.Server(uvicorn.Config(create_app(harness, start_worker=False), log_level="warning"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        while not server.started:
            time.sleep(0.01)
        yield f"http://127.0.0.1:{sock.getsockname()[1]}/"
        server.should_exit = True
        thread.join()


@pytest.fixture
def open_shelf(page: Page, site):
    """Opens the page at a given window size, and fails the test on any uncaught script error."""
    errors = []
    page.on("pageerror", lambda error: errors.append(error.message))
    # Anything from the internet is refused, which is what keeps every run the same.
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(site) else route.abort())

    def opener(width=1440, height=900):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(site)
        page.wait_for_selector(".tile")
        page.evaluate("document.fonts.ready.then(() => null)")
        return page

    yield opener
    assert errors == []


def tile(page: Page, video_id: str):
    return page.locator(f'.tile[data-video="{video_id}"]')


# --- Equal boxes ---


@pytest.mark.parametrize("width", [1900, 1440, 1024, 390])
def test_every_box_is_the_same_size_and_no_text_is_cut(open_shelf, width):
    page = open_shelf(width=width)
    boxes = page.evaluate("""() => [...document.querySelectorAll('.tile')].map((tile) => {
        const { width, height } = tile.getBoundingClientRect();
        const part = (selector) => tile.querySelector(selector).getBoundingClientRect().height;
        const title = tile.querySelector('.title');
        return { width, height, content: part('.thumb') + part('.text'), titleCut: title.scrollHeight - title.clientHeight };
    })""")

    assert len(boxes) == 5
    # Exact to well under a pixel, since text heights are rarely whole numbers.
    assert max(box["height"] for box in boxes) - min(box["height"] for box in boxes) < 0.1
    assert len({box["width"] for box in boxes}) == 1
    assert all(box["content"] <= box["height"] + 0.1 for box in boxes), boxes
    # scrollHeight rounds up, so a title that fits can still read one pixel over.
    assert all(box["titleCut"] <= 1 for box in boxes), boxes
    # The boxes span more than one row, or the match would prove nothing beyond plain CSS.
    assert page.locator(".row").count() == 3


def test_a_short_box_leaves_its_spare_room_at_the_bottom(open_shelf):
    page = open_shelf()
    short = tile(page, "aaaaaaaaaaa").locator(".text").bounding_box()
    long = tile(page, "bbbbbbbbbbb").locator(".text").bounding_box()
    assert short["y"] == long["y"]
    assert short["height"] < long["height"]


def test_boxes_match_again_after_the_window_changes_size(open_shelf):
    page = open_shelf()
    before = tile(page, "aaaaaaaaaaa").bounding_box()["height"]
    page.set_viewport_size({"width": 1024, "height": 700})
    # The long title wraps further in the narrower box, and every box has to follow it.
    page.wait_for_function(f"document.querySelector('.tile').getBoundingClientRect().height > {before}")
    assert page.evaluate(ALL_BOXES_MATCH)


def test_searching_does_not_resize_the_boxes(open_shelf):
    page = open_shelf()
    before = tile(page, "aaaaaaaaaaa").bounding_box()["height"]
    page.fill("#search", "Short")
    expect(tile(page, "bbbbbbbbbbb")).to_be_hidden()
    assert tile(page, "aaaaaaaaaaa").bounding_box()["height"] == before


# --- Bullets at rest, the TL;DR on hover ---


def test_bullets_show_without_hovering(open_shelf):
    page = open_shelf()
    expect(tile(page, "bbbbbbbbbbb").locator(".brief li")).to_have_text(HIGHLIGHTS)
    expect(tile(page, "bbbbbbbbbbb").locator(".tldr")).to_be_hidden()


def test_a_summary_with_no_highlights_shows_its_first_key_points(open_shelf):
    page = open_shelf()
    expect(tile(page, "ccccccccccc").locator(".brief li")).to_have_text(KEY_POINTS[:3])


def test_an_unfinished_video_has_no_bullets(open_shelf):
    page = open_shelf()
    expect(tile(page, "eeeeeeeeeee").locator(".brief")).to_be_hidden()
    expect(tile(page, "eeeeeeeeeee").locator(".state-line .state")).to_have_text("Couldn't summarize")


def test_hovering_the_thumbnail_shows_the_tldr(open_shelf):
    page = open_shelf()
    video = tile(page, "bbbbbbbbbbb")
    video.locator(".thumb").hover()
    expect(video.locator(".tldr")).to_be_visible()
    expect(video.locator(".tldr")).to_have_text("Raft elects a leader and replicates a log to its followers.")


# --- The summary window ---


def long_row(store, open_shelf):
    """A row wide enough to scroll, with the pointer resting on its next arrow."""
    for number in range(8):
        save_video(store, f"video{number:06}", title=f"Video {number}")
    page = open_shelf()
    row = page.locator(".row", has=tile(page, "video000000"))
    arrow = row.locator(".arrow.next")
    # The arrow now sits halfway down a tall box, so the whole box has to be on screen.
    row.locator(".rail").evaluate("(rail) => rail.scrollIntoView({ block: 'center' })")
    box = row.locator(".rail").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + 50)
    expect(arrow).to_be_visible()
    return page, row, arrow


def test_an_arrow_sits_halfway_down_the_boxes(store, open_shelf):
    page, row, arrow = long_row(store, open_shelf)
    box = row.locator(".tile").first.bounding_box()
    circle = arrow.locator("svg").bounding_box()
    assert abs((circle["y"] + circle["height"] / 2) - (box["y"] + box["height"] / 2)) < 1
    assert circle["width"] == circle["height"] == 52


def test_aiming_for_an_arrow_never_opens_the_video_under_it(store, open_shelf):
    page, row, arrow = long_row(store, open_shelf)
    box = arrow.bounding_box()
    page.mouse.move(box["x"] + 2, box["y"] + 2)
    page.wait_for_timeout(450)  # Well past the wait before a card opens.
    expect(page.locator(".tile.open")).to_have_count(0)

    # Anywhere on the strip counts, not just on the circle in the middle of it.
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] - 2)
    page.wait_for_function("(list) => list.scrollLeft > 0", arg=row.locator(".scroller").element_handle())


def test_a_card_opens_clear_of_the_arrows(store, open_shelf):
    page, row, arrow = long_row(store, open_shelf)
    arrow_box = arrow.bounding_box()
    # The row's last visible video, right beside the arrow, is the one most likely to land on it.
    thumbs = row.locator(".thumb")
    index = thumbs.evaluate_all(
        "(all, edge) => all.findIndex((thumb) => thumb.getBoundingClientRect().right > edge)", arrow_box["x"]
    )
    box = thumbs.nth(index).bounding_box()
    page.mouse.move(arrow_box["x"] - 4, box["y"] + box["height"] / 2)
    card = page.locator(".tile.shown .card")
    expect(card).to_be_visible()
    # The card grows out of the thumbnail, and it's where it ends up that counts.
    card.evaluate("(card) => Promise.all(card.getAnimations().map((animation) => animation.finished))")
    card_box = card.bounding_box()
    assert card_box["x"] + card_box["width"] <= arrow_box["x"] + 1
    # The pointer can still get from the card straight onto the arrow.
    page.mouse.move(arrow_box["x"] + arrow_box["width"] / 2, arrow_box["y"] + arrow_box["height"] / 2)
    assert arrow.evaluate("(button) => button.matches(':hover')")


def test_an_arrow_stays_under_the_pointer_at_the_end_of_the_row(store, open_shelf):
    page, row, arrow = long_row(store, open_shelf)
    box = arrow.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    row.locator(".scroller").evaluate("(list) => { list.scrollLeft = list.scrollWidth; }")
    page.wait_for_timeout(450)
    expect(arrow).to_be_visible()
    expect(page.locator(".tile.open")).to_have_count(0)

    page.mouse.move(box["x"] + box["width"] / 2, box["y"] - 60)
    expect(arrow).to_be_hidden()


def open_summary(page: Page, video_id="bbbbbbbbbbb"):
    tile(page, video_id).locator(".title-link").click()
    details = page.locator("#details")
    expect(details).to_be_visible()
    # Let the opening movement finish, so measurements aren't taken halfway through it.
    details.evaluate("(window) => Promise.all(window.getAnimations().map((animation) => animation.finished))")
    return details


def test_clicking_a_video_opens_its_whole_summary_in_a_centred_window(open_shelf):
    page = open_shelf()
    details = open_summary(page)
    expect(details.locator(".details-tldr")).to_be_visible()
    expect(details.locator(".points li")).to_have_text(KEY_POINTS)
    expect(details.locator(".time-label")).to_have_text(["Leader election"])
    assert details.evaluate("(window) => window.matches(':modal')")
    box = details.bounding_box()
    assert abs(box["x"] + box["width"] / 2 - 720) <= 1
    assert abs(box["y"] + box["height"] / 2 - 450) <= 1
    # The two columns start on one line.
    assert details.locator(".details-tldr").bounding_box()["y"] == details.locator(".details-times h3").bounding_box()["y"]


def test_the_window_leaves_the_shelf_where_it_was(open_shelf):
    page = open_shelf(height=500)
    page.evaluate("scrollTo(0, 200)")
    # Clicking scrolls the title into view first, so measure after that has happened.
    tile(page, "bbbbbbbbbbb").locator(".title-link").scroll_into_view_if_needed()
    before = tile(page, "bbbbbbbbbbb").bounding_box()
    scrolled = page.evaluate("scrollY")
    assert scrolled > 0
    open_summary(page)
    assert tile(page, "bbbbbbbbbbb").bounding_box() == before
    page.mouse.move(5, 5)
    page.mouse.wheel(0, 400)
    page.wait_for_timeout(100)
    assert page.evaluate("scrollY") == scrolled


@pytest.mark.parametrize("how", ["Escape", "close button", "outside", "Back"])
def test_every_way_of_closing_returns_to_the_shelf(open_shelf, site, how):
    page = open_shelf()
    details = open_summary(page)
    if how == "Escape":
        page.keyboard.press("Escape")
    elif how == "close button":
        page.click("#details-close")
    elif how == "outside":
        page.mouse.click(5, 450)
    else:
        page.go_back()
    expect(details).to_be_hidden()
    expect(tile(page, "bbbbbbbbbbb").locator(".title-link")).to_be_focused()
    # It came off the history once and only once, so the page itself is still here.
    page.wait_for_function("history.state === null")
    assert page.url == site
    # And it opens again as normal.
    open_summary(page, "aaaaaaaaaaa")


def test_selecting_text_past_the_edge_does_not_close_the_window(open_shelf):
    page = open_shelf()
    details = open_summary(page)
    box = details.locator(".details-tldr").bounding_box()
    page.mouse.move(box["x"] + 5, box["y"] + 5)
    page.mouse.down()
    page.mouse.move(5, box["y"] + 5)
    page.mouse.up()
    expect(details).to_be_visible()


def test_the_page_behind_cannot_be_reached_while_the_window_is_open(open_shelf):
    page = open_shelf()
    open_summary(page)
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.closest('#details') !== null")
    # The pop-out doesn't open underneath, and comes back once the window is gone.
    tile(page, "aaaaaaaaaaa").locator(".thumb").hover(force=True)
    page.wait_for_timeout(450)
    expect(page.locator(".tile.open")).to_have_count(0)
    page.keyboard.press("Escape")
    tile(page, "ddddddddddd").locator(".thumb").hover()
    expect(tile(page, "ddddddddddd").locator(".tldr")).to_be_visible()


def test_a_summary_with_no_timestamps_or_tags_uses_the_full_width(store, open_shelf):
    save_video(store, "fffffffffff", title="Just a summary", timestamps=[], tags=[])
    page = open_shelf()
    details = open_summary(page, "fffffffffff")
    expect(details.locator(".details-side")).to_be_hidden()
    assert details.locator(".details-main").bounding_box()["width"] > 700


def test_a_phone_gets_the_whole_screen(open_shelf):
    page = open_shelf(width=390, height=844)
    box = open_summary(page).bounding_box()
    assert (box["x"], box["y"], box["width"], box["height"]) == (0, 0, 390, 844)
    expect(page.locator("#details .open-note")).to_be_in_viewport()


def test_checking_for_jobs_with_the_window_open_reports_no_problem(open_shelf):
    """render() once reused the name of the page's job map, and every check reported a dead server."""
    page = open_shelf()
    details = open_summary(page)
    page.evaluate("refresh()")
    expect(page.locator("#message")).to_have_text("")
    expect(details).to_be_visible()


# --- Search ---


def test_search_reaches_key_points_and_timestamp_labels(open_shelf):
    page = open_shelf()
    for words, count in [("Clients talk", 4), ("Leader election", 4), ("no such words", 0)]:
        page.fill("#search", words)
        expect(page.locator(".tile:visible")).to_have_count(count)


# --- Adding a link ---


def test_pasting_submits_nothing_until_add_is_pressed(open_shelf, store):
    page = open_shelf()
    posts = []
    page.on("request", lambda request: posts.append(request.url) if request.method == "POST" else None)
    page.evaluate("(link) => navigator.clipboard.writeText(link)", LINK)

    page.mouse.click(700, 850)
    page.keyboard.press("Control+V")
    expect(page.locator("#url")).to_have_value("")

    page.click("#url")
    page.keyboard.press("Control+V")
    expect(page.locator("#url")).to_have_value(LINK)
    # A round trip to the server, so anything a paste had sent would have shown up by now.
    page.evaluate("refresh()")
    assert posts == []
    assert store.active_job("youtube", "dQw4w9WgXcQ") is None

    with page.expect_response("**/videos"):
        page.click("#submit")
    assert len(posts) == 1
    assert store.active_job("youtube", "dQw4w9WgXcQ") is not None
    expect(page.locator("#url")).to_have_value("")
