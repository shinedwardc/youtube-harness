# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One person: the owner, on a home setup. They watch YouTube and only keep the videos they want to recall later, such as educational ones. They mostly use this page on a desktop browser; on a phone it only needs to work, with a tap opening the video's details.

## Product Purpose

Turn a YouTube link into a summary note in the owner's Obsidian vault, and never summarize the same video twice. The web page's main job is recall: seeing what has been saved and remembering a video without having to open it. Adding a new link is a smaller, always-available second job.

Success: a glance at the page brings back what a video was about, one click shows the whole summary, and its note is never more than one click from there.

## Positioning

A personal shelf of videos worth remembering, chosen by hand. It is deliberately not a watch history and summarizes nothing automatically.

## Operating Context

- The page is served by the same FastAPI app as the API and worker, as one HTML file with no framework or build step.
- Runs in Docker on the owner's own machine, with phone access planned over Tailscale. There is no login, so the port must never be public.
- Notes live in an Obsidian vault and sync through Obsidian Sync. Obsidian is where notes are kept and edited; this page shows a summary read-only and points to its note.
- Jobs take about a minute and move through queued, fetching, summarizing, writing, then done, needs_transcription or failed.

## Capabilities and Constraints

- Each video has a thumbnail from YouTube, plus YouTube's three stills from within the video. YouTube offers no public animated previews.
- A finished video has a title, channel, category, TL;DR, key points, timestamps, tags and an `obsidian://` link. An unfinished one has only its video ID and thumbnail.
- Clicking a finished video opens a centred summary window over the dimmed shelf, as clicking a title on Netflix does, with its picture, TL;DR, key points and timestamps, and buttons to open its note or watch it on YouTube (owner's direction). The pop-out's Open note button goes straight to the note.
- A failed video can be sent again. A video with no captions can't be summarized yet.
- The page polls `GET /jobs`. Titles and errors come from YouTube and yt-dlp, so they are untrusted text.

## Brand Commitments

- The overall colour scheme is light red (owner's direction).
- Each video is its own clickable thumbnail that pops out a little on hover, as on Netflix, and plays a preview: stills cycling at once, then the real muted video where YouTube allows it (owner's direction).
- The product has no logo or marketing name. The page has been titled "Video notes".

## Evidence on Hand

- Real saved videos in the owner's database (`data/harness.db`, not committed).
- No testimonials, users or metrics exist, and none should be invented.

## Product Principles

- Recall comes first: what a video was about is visible before any click.
- Hand-picked, never automatic: nothing suggests or summarizes on its own.
- The note is the home: the page helps you recall a video and gets you to Obsidian, rather than becoming a second place to keep notes.
- Say plainly what went wrong and what to do next.
