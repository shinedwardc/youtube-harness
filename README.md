# YouTube Harness

## Why this exists
With the infinite amount of content available to consume on social media apps like YouTube, the opportunities to get more exposure in different area of domains and to learn new topics have never been so abundant before. However, even with the ease of access to information through video consumption it's hard to recall what you watch, at least it was for me. For example, I was getting really frustrated with how I would watch educational videos and not being able to recall what I watched, especially as I mostly watch content passively on my free time.
Existing summarizers exist everywhere, but I wanted the summarizer to be relevant to what I actually watch, and to store that information for my reference later. Learning something requires repetition and you need the ability to be able to describe what you learned by yourself - the true test for actual proof of knowledge retention. I believe having a personal list of videos that seem educational and useful to you will help you learn the material through repetition of exposure. The summarized videos can also be used as context and memory for other agents.
I want the user to be directly in charge of which videos they want to save later.
Now that this exists - I am able to save YouTube videos but with summaries and notes along with them without having to manually add them to a separate notes or documents file, or watch the video(s) again, reducing clutter.


## Features

- **You choose the videos.** Nothing is summarized unless you paste a link and press Add.
- **Notes in your personal vault.** Each video becomes a Markdown note with a short summary, key points and tags.
- **Timestamps that link to the video.** Click one to jump to that moment.
- **Never summarized twice.** Send the same video again and you get the saved note.
- **A shelf for recall.** Browse saved videos at a glance, then open the full summary with one click.
- **Works on long videos.** Hour-long videos are handled the same way as short ones.
- **Your language.** Summaries match the video's language, or the one you set.
- **Free or local AI.** Use Gemini or Groq on their free tiers, or run a model on your own machine with Ollama.
- **Everything stays on your machine.** Notes are plain Markdown, and each video's full transcript is saved locally.

## Getting started (running locally)

- Prerequisites: Docker, a free Gemini API key, and optionally Obsidian
- Steps to cover, in one copy-pasteable block:
  - `cp .env.example .env`, then set `GEMINI_API_KEY`
  - `docker compose up -d --build`
  - Open http://localhost:8000
- What success looks like: paste a link, press Add, and a note appears in about a minute
- Warning: there is no login, so never expose the port publicly. Compose binds it to `127.0.0.1` for this reason
- Mention `HARNESS_VAULT_DIR` and `HARNESS_VAULT_NAME`, or "open in Obsidian" links can break

## Usage

- Web page: adding a link, recalling a video, opening its note
- CLI:
  - `docker compose exec harness yt-sum <url>`
  - Stdout is only the note's path, so it can be piped
  - Exit codes: `0` done, `1` failed, `2` needs transcription, `130` interrupted
  - `yt-sum --backfill-transcripts` fetches transcripts for videos saved before they were kept
- HTTP API: `POST /videos`, `GET /jobs`, `GET /jobs/{id}`
- Include one screenshot of the shelf and one example note

## Configuration

- Table with columns: Variable | Required | Default | Notes
- Copy the variables from `.env.example`, grouped as keys, providers, and harness settings
- Say which key is required: the one for your primary provider (Gemini by default; Ollama needs none)
- Mention `HARNESS_SUMMARY_LANGUAGE` (`auto` matches the captions) and `TZ` (the container defaults to UTC, which can misdate notes)
- Mention what people can customize without code: `prompts/` and `templates/note.md`

## How it works

- ASCII flow from link to note, labeling each stage with the file that owns it:
  - `parse`: `harness/plugins/youtube/ids.py`
  - queue and worker: `harness/core/jobs.py`
  - `fetch`: `harness/plugins/youtube/fetch.py` and `transcript.py`
  - `summarize`: `harness/plugins/youtube/summarize.py` and `harness/core/llm.py`
  - `write`: `harness/plugins/youtube/render.py`
  - storage: `harness/core/db.py`
- Explain the plugin idea: `harness/core/plugin.py` defines the steps, and YouTube is the only plugin so far
- Explain why SQLite, why one worker thread, and why transcripts have their own table
- Link to `PRODUCT.md` and `DESIGN.md` for the product and design reasoning

## Limitations

- Videos with no captions can't be summarized yet (`needs_transcription`)
- Live and upcoming streams have to wait until they've ended
- Built for one person on their own machine, with no accounts or login
- Hand-picked by design: it won't follow channels or summarize automatically

## Roadmap

- Only include what you actually intend to build, and give each item a reason
- Candidates: full-text search, phone capture, library Q&A with citations, MCP access for AI tools, transcription for videos with no captions, and articles as a second source

## Development

- Install dependencies and run without Docker: `uv sync`, then `uv run uvicorn harness.api:app --host 0.0.0.0 --port 8000`
- Run tests with `uv run pytest`. Nothing in the suite goes online; the browser tests need Playwright's Chromium
- How to add a new plugin, once there's a second one to point to
- Commit style: Conventional Commits

## License

MIT. See [LICENSE](LICENSE).
