---
name: Video notes
description: A hand-picked shelf of saved videos in light red, built like a streaming service's rows.
colors:
  ground: "#fbd9d3"
  surface: "#fff5f3"
  action: "#dc2f35"
  action-deep: "#b81f25"
  brand: "#c8242a"
  ink: "#3a1417"
  soft: "#7b4044"
  line: "#f0b4ab"
  on-action: "#ffffff"
typography:
  display:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  title-card:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.005em"
  body-large:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.45
  body:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.45
  body-small:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.45
  caption:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Bricolage Grotesque, Nanum Gothic, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.25
rounded:
  focus: "4px"
  nested: "6px"
  base: "8px"
  card: "12px"
  round: "50%"
spacing:
  gutter: "clamp(1rem, 3.35vw, 3rem)"
  line-gap: "0.125rem"
  text-gap: "0.375rem"
  head-gap: "0.625rem"
  group-gap: "0.75rem"
  row-gap: "1.375rem"
  row-gap-phone: "0.875rem"
  row-space: "2.5rem"
  row-space-phone: "2rem"
  bar-block: "1.125rem"
  bar-block-phone: "0.875rem"
  page-foot: "4rem"
components:
  press:
    backgroundColor: "{colors.action}"
    textColor: "{colors.on-action}"
    typography: "{typography.label}"
    rounded: "{rounded.base}"
    padding: "0.5625rem 1.125rem"
  press-hover:
    backgroundColor: "{colors.action-deep}"
  press-in-field:
    backgroundColor: "{colors.action}"
    textColor: "{colors.on-action}"
    typography: "{typography.label}"
    rounded: "{rounded.nested}"
    padding: "0.4375rem 0.875rem"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.base}"
    height: "2.625rem"
    padding: "0 1rem"
  video-box:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "0.75rem 0.875rem 0.875rem"
  thumbnail:
    backgroundColor: "{colors.line}"
  progress-fill:
    backgroundColor: "{colors.action}"
    height: "5px"
  arrow:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.round}"
    size: "2.75rem"
  arrow-hover:
    backgroundColor: "{colors.action}"
    textColor: "{colors.on-action}"
  popout-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "1rem 1.25rem 1.25rem"
  popout-media:
    backgroundColor: "{colors.ink}"
  summary-window:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "1.25rem 1.5rem 1.5rem"
    width: "min(52rem, 100vw - 2rem)"
  toast:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.base}"
    padding: "0.75rem 1.125rem"
  toast-problem:
    backgroundColor: "{colors.action-deep}"
    textColor: "{colors.on-action}"
---

# Design System: Video notes

## Overview

**Creative North Star: "The Hand-Picked Shelf"**

A personal shelf that behaves like a streaming service's: rows of thumbnails, and a card that grows out of a thumbnail to bring the video back to mind. The owner chose the streaming standard over more themed directions, so the category's own shelf is the form and it is held to full craft. What makes it this shelf rather than any other is warmth: the owner's light red scheme and Bricolage Grotesque's bold, slightly unruly letters.

The page is dense with pictures and quiet around them. The videos' own thumbnails supply all the strong colour and contrast; the interface stays in one family of warm reds, flat, with no decoration of its own. The real movement is saved for one moment, the pop-out, and everything else answers plainly.

Confirmed rejections come from the chosen direction: a page led by the paste box, and a plain list of status rows. The owner's pinned decisions are the light red scheme, the Netflix-style pop-out with a preview, and the streaming standard set in Bricolage Grotesque.

**Key Characteristics:**
- Light red ground everywhere, with warm near-white for anything raised or typed into.
- One typeface, bold and tightly tracked for titles.
- Flat by decision, with a single shadow on the pop-out card.
- Rows by the month a video was summarized, with unfinished work first.
- Every video in a same-size box, with very brief bullets under each finished title, so a row can be scanned with nothing hovered.
- A pop-out that grows from the thumbnail's exact position and previews the video.
- A flat summary window centred over the dimmed shelf, holding the whole summary.

## Colors

A single warm red family from pale ground to oxblood ink, with no second hue; colour variety comes only from the video pictures.

### Primary
- **Action Red** (#dc2f35): The fill on pressable buttons (Add, Open note, Try again in the card), on an arrow or the window's close button under the pointer, and on the job progress bar. Also the text caret and the selection highlight.
- **Action Deep** (#b81f25): Action Red's darker step. The hover fill on buttons, every piece of red text (category, timestamp times, failed and no-captions states, text-sized actions such as Try again and Clear search), the 2px focus ring, and the problem toast.
- **Brand Red** (#c8242a): The "Video notes" title in the bar, and nothing else.

### Neutral
- **Light Red Ground** (#fbd9d3): The page, the sticky bar, and the browser theme colour.
- **Warm Near-White** (#fff5f3): Raised or typed-into surfaces: the two fields, the video boxes, the pop-out card, the summary window, and the row arrows and close button at rest. Also the toast's text.
- **Oxblood Ink** (#3a1417): Headings and body text. Also the toast background and the card's picture frame before a picture loads.
- **Soft Ink** (#7b4044): Secondary text: channel, counts, job states, tags, placeholders, the search icon, and Watch links. Also the dots on a tile's bullets.
- **Blush Line** (#f0b4ab): The bar's hairline once the page has scrolled, the hairline above the window's buttons, the arrow's and close button's border, and the stand-in behind a thumbnail with no picture.
- **Pure White** (#ffffff): Text and chevrons on Action Red and Action Deep fills, where it holds 4.67:1 and 6.44:1, and the toast's link.

### Named Rules
**The Light Red Rule.** The page is light red, by the owner's decision. Raised surfaces warm toward near-white; they never go gray or pure white.

**The Fill Or Deep Rule.** Action Red is a fill, never text. When red has to be read as words, it is Action Deep, which holds 4.90:1 on the ground and 6.01:1 on the near-white surface.

## Typography

**Display Font:** Bricolage Grotesque (with Nanum Gothic, system-ui, sans-serif)
**Body Font:** Bricolage Grotesque
**Label/Mono Font:** Bricolage Grotesque; there is no mono

**Character:** A warm, slightly irregular grotesque that keeps a utilitarian streaming layout from feeling generic. Loaded with its optical size axis (12..96) and weights 400, 600 and 700, so large titles draw in a tighter cut than body text. Nanum Gothic is in the stack only to carry Korean titles, and downloads only when a page contains Hangul.

### Hierarchy
- **Display** (700, 1.875rem, line-height 1, -0.015em; 1.5rem on phones): The "Video notes" title in the bar.
- **Headline** (700, 1.75rem, line-height 1.15, -0.015em; 1.3125rem on phones): Row headings such as "November 2026".
- **Title Card** (700, 1.625rem, line-height 1.08, -0.015em): The video title in the pop-out, balanced and clamped to three lines, and in the summary window, balanced and never clamped.
- **Title** (700, 1.125rem, line-height 1.2, -0.005em): The video title under a thumbnail, wrapping as far as it needs and never clamped, and the window's Key points and Timestamps headings.
- **Body Large** (400, 1.125rem, line-height 1.45): The TL;DR in the summary window, and empty and no-match notices, limited to 34rem.
- **Body** (400, 1rem, line-height 1.45): Channel, TL;DR in the card, key points and timestamp labels in the window, counts and timestamp times with tabular figures, and field text.
- **Body Small** (400, 0.9375rem, line-height 1.45): The failure reason under a tile, and a tile's bullets, which tighten to line-height 1.3.
- **Caption** (400, 0.875rem, line-height 1.45): Tags, in Soft Ink, as a plain spaced run of words with no chips.
- **Label** (600, 1rem, line-height 1.25): Button text. Job states, the category and text-sized actions use the same weight at the body line-height.

### Named Rules
**The One Family Rule.** Every role is Bricolage Grotesque. Hierarchy comes from size and weight, and Nanum Gothic only ever stands in for Hangul.

**The Three Weights Rule.** 700 for titles, 600 for labels and states, 400 for everything else. Only these three are loaded.

## Layout

No page container: the shelf runs the full width of the window, with a fluid gutter (clamp(1rem, 3.35vw, 3rem)) that aligns the bar, row headings and first thumbnails on one left edge. Rows bleed off the right edge rather than ending at the gutter.

A sticky bar sits on top, on the same ground as the page, with the title, then search (up to 28.75rem), then the paste field pushed to the right (up to 24rem). Its 1px hairline appears only once the page has scrolled. Below it, rows stack with 2.5rem between them.

Each row is a heading with a quiet count, then a horizontally scrolling line of 16:9 thumbnails. Between roughly 1180px and 1800px wide a row shows four thumbnails and a peek of the next (one tile plus its 1.375rem gap is the available width divided by 4.2). Below that range the tile holds at 15rem and shows fewer; above it the tile caps at 24rem and shows more. Scrolling snaps gently (proximity), and the rows' scrollbars are hidden.

At 40rem and under, the bar stops being sticky, the paste field takes its own full-width line, tiles become min(72vw, 18rem) wide with a 0.875rem gap, and rows sit 2rem apart. Devices without a fine hovering pointer lose the arrows and the pop-out: a tap opens the summary window, with the TL;DR below the picture and title, and a Watch on YouTube link sits under the bullets. Phones only need to work.

### Named Rules
**The Month Row Rule.** Rows are by the month a video was summarized, newest first, headed like "November 2026". Videos without a summary date go in one "Not summarized yet" row above all of them.

**The Peek Rule.** A row with more to show leaves a thumbnail cut at the window's edge. That cut is what says the row carries on.

**The Equal Box Rule.** Every video's box on the shelf is the same size, across all rows, by the owner's decision. The height comes from measuring the tallest box, so text is never cut to fit: it runs from the top, and whatever a box doesn't need stays empty at its bottom.

## Elevation & Depth

Flat by decision, with one exception. Only the pop-out card carries a shadow; the bar, fields, video boxes, arrows, summary window and toast are all flat, and separate from what is behind them by tone, a hairline or plain stacking order. The shadow is tinted oxblood rather than black, so it reads as part of the red page.

### Shadow Vocabulary
- **Pop-out lift** (`box-shadow: 0 24px 48px rgba(90, 20, 26, 0.34), 0 4px 12px rgba(90, 20, 26, 0.16)`): The pop-out card only. A wide soft layer for lift and a tight layer for contact.

### Named Rules
**The One Lift Rule.** If it isn't the pop-out card, it has no shadow. The fixed toast, the sticky bar and the summary window are not exceptions. The window stands out through the dimmed page around it.

## Shapes

Gently rounded and consistent: 8px on fields, standard buttons, and the toast, and 12px on the video boxes, the pop-out card and the summary window, the larger objects. A button nested inside a field steps down to 6px so its corners sit concentric with the field's. Row arrows and the panel's close button are the only full circles. Focus rings on elements without their own radius round to 4px. Pictures are always clipped to their frame with cover-fit cropping, and a box's or card's picture is clipped by the box or card itself, with no radius of its own. Borders are rare: only the arrow and the close button have one.

## Components

### Buttons
Solid, plain and quick.
- **Shape:** Gently rounded (8px); inside a field, slightly tighter (6px).
- **Primary:** Action Red fill, white Label text, 0.5625rem by 1.125rem padding. The compact Add button uses 0.4375rem by 0.875rem.
- **Hover / Focus:** The fill darkens to Action Deep in 0.12s, with no movement. Focus is a 2px Action Deep ring offset 2px.
- **Disabled:** 60% opacity while a request is in flight.
- **Text action:** Try again under a tile and Clear search are Action Deep, weight 600, underlined. Watch links are Soft Ink, turning Oxblood Ink on hover.

### Inputs / Fields
- **Style:** Warm Near-White fill, no stroke, 8px corners, 2.625rem tall, Soft Ink placeholder.
- **Focus:** The field, not the input, takes a 2px Action Deep ring offset 1px.
- **Composition:** Search leads with an 18px stroked icon. The paste field holds the Add button inside its right edge, 0.25rem from it.
- **Errors:** Reported in the toast, never by restyling the field.

### Navigation
The bar is the only navigation: title, search and paste field. Row arrows are 2.75rem circles of Warm Near-White with a Blush Line border and an Oxblood Ink stroked chevron. They fade in over 0.14s while the pointer is on the row, centred on the thumbnails and straddling the gutter, and turn Action Red with a white chevron under the pointer. An arrow is removed at the row's end. They page by 80% of the row's width and are pointer-only, since keyboards reach every tile by tabbing.

### Thumbnail Tile
- **Box:** A flat Warm Near-White box with 12px corners holds the picture and the text, the same size as every other box on the shelf. The text has 0.75rem by 0.875rem by 0.875rem padding, and unfinished videos get the same box, so nothing jumps when a job finishes.
- **Picture:** 16:9, filling the top of the box edge to edge, with a Blush Line stand-in when YouTube has no real picture. The image scales to 1.04 under the pointer in 0.28s, answering during the moment before the card opens.
- **Text:** Title beneath, then the channel in Soft Ink. An unfinished video shows its job state instead, in Soft Ink at weight 600, or Action Deep when it is stuck, with the reason clamped to one line.
- **Bullets:** A finished video shows its three highlights in Oxblood Ink under the channel, 0.5rem below it, with small Soft Ink dots. A summary with no highlights falls back to its first three key points, each clamped to two lines. The TL;DR stays out of the tile: it belongs to the pop-out and the panel.
- **Progress:** A running job shows a 5px Action Red bar along the thumbnail's bottom edge on a 55% near-white track, the way a streaming service shows watch progress. Stages fill it to 6%, 30%, 65% and 92%, easing over 0.9s.
- **Clicking:** A finished video's picture and title, on the tile or in the pop-out, open the summary window. With a modifier key they follow the link to the note. An unfinished video's links go to YouTube.

### Pop-out Card
The signature, pinned by the owner: the thumbnail itself grows into a card.
- **Size:** 1.35 times the thumbnail's width, at least 320px and at most 440px, always within a 16px margin of the window.
- **Contents:** The 16:9 preview, then Title Card, category in Action Deep with channel and date in Soft Ink, the TL;DR, tags, and the Open note button with a Watch link. Padding is 1rem by 1.25rem by 1.25rem.
- **Opening:** After 280ms of hover intent, or at once on keyboard focus. It starts laid exactly over the thumbnail, scaled to match, and grows over 0.26s on a strong ease-out (cubic-bezier(0.16, 1, 0.3, 1)), with a very quick 0.08s fade so the swap can't be seen. A 120ms grace period lets the pointer travel from thumbnail to card.
- **Placement:** With no room below, the details go above, so the picture stays on its thumbnail. If neither side has room, the card keeps its details below and slides up to fit. It stays below the bar, and its top edge never cuts through a row heading's letters.
- **Focus:** The card covers the focused link beneath it, so the card shows the 2px focus ring instead.

### Preview
- **Stills first:** YouTube's stills cycle every 1.1s from the moment the card opens, each new one fading in over the last in 0.22s, so what's behind them never shows through.
- **Then video:** The muted video starts hidden 0.3s in, with no controls. It stays hidden for 4s after it begins playing, until YouTube's title and icons have cleared, then fades in over 0.4s and the stills stop. Videos over two minutes skip their first 15%.
- **If it can't play:** A channel that blocks embedding, or a player that won't load, leaves the stills running with no message.
- **Reduced motion:** Stops all of it. The card opens at once with its first still and plays nothing, and the card's growth, the thumbnail zoom and smooth row scrolling go too.

### Summary Window
The rest of the summary, for remembering a video properly without leaving the page. Chosen by the owner to work like clicking a title on Netflix. Quiet on purpose: it has no video of its own, and the pop-out keeps the page's one real moment of movement.
- **Placement:** A modal window centred on the screen, up to 52rem wide and 4rem shorter than the window, over the page dimmed with 62% Oxblood Ink. The page behind it can't be reached or scrolled and doesn't move. At 40rem and under it takes the whole screen.
- **Contents:** A 16:9 still filling the top edge to edge and linking to YouTube, using YouTube's sharpest picture where there is one. It is capped at 42% of the screen's height and cropped mostly from the bottom, since thumbnails carry their words near the top. Then the Title Card with category, channel and date. Below that, the TL;DR in Body Large and Key points sit in a wide column, with Timestamps and tags in a narrower one beside it, stacking when there's no room for both. A section with nothing in it is left out, and with no timestamps or tags the summary takes the full width. Open note and Watch on YouTube stay pinned to the bottom, above a Blush Line hairline.
- **Timestamps:** Times in Action Deep with tabular figures, in one column, each row linking to that second on YouTube. A time that can't be read stays plain text, as it does in the note.
- **Text:** Korean wraps between words (`word-break: keep-all`), and only something too long to fit is broken.
- **Close button:** A 2.75rem Warm Near-White circle with a Blush Line border, styled like the row arrows, fixed to the top-right corner while the window scrolls.
- **Opening:** Fades in over 0.14s while rising 1rem and growing from 98% over 0.26s, as the page dims over 0.2s. It closes at once. Reduced motion removes all of it.
- **Closing and focus:** The close button, Escape, the browser's Back, or a click on the dimmed page, though not a text selection that ends out there. Opening moves focus to the close button, and closing returns it to the video's title without reopening the pop-out. Checking for new jobs never resets what's being read.

### Toast
Bottom-centre and flat, with 8px corners and 0.75rem by 1.125rem padding. Oxblood Ink with Warm Near-White text for news, Action Deep with white text for a problem, and an optional Open note link at weight 600.

## Do's and Don'ts

### Do:
- **Do** keep the page on Light Red Ground and raised surfaces on Warm Near-White; the light red scheme is the owner's decision.
- **Do** group videos into rows by the month they were summarized, with the "Not summarized yet" row first.
- **Do** open the pop-out from the thumbnail's exact position, with its picture staying on the thumbnail wherever room allows.
- **Do** show stills first and hold the muted video hidden until YouTube's overlay has cleared.
- **Do** stop every preview and growth animation under reduced motion, while still letting the card open.
- **Do** keep every video's box the same size across the whole shelf, and let the text decide how much of it stays empty.
- **Do** keep a thumbnail to its picture and, while a job runs, the 5px progress bar.
- **Do** keep a tile's bullets to fragments that can be scanned, and save the TL;DR paragraph for the pop-out and the window.
- **Do** use Action Deep for any red that has to be read as text.

### Don't:
- **Don't** put a shadow on anything except the pop-out card.
- **Don't** let the pop-out's top edge cut through a row heading.
- **Don't** reveal the video while YouTube's title and icons are still drawn over it.
- **Don't** add a second typeface beyond Nanum Gothic's Hangul fallback, or a weight beyond 400, 600 and 700.
- **Don't** add a second hue to the interface; the pictures carry all the other colour.
- **Don't** let the paste box lead the page, or reduce the shelf to a plain list of status rows.
- **Don't** add a logo or marketing name; the page is titled "Video notes".
