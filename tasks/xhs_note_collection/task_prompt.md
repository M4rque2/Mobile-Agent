# XHS Note Crawling Prompt

Collect note detail information from the 小红书 app's home feed. Open individual note detail pages one by one, extract visible metadata, then record everything in a structured JSON output.

Work only inside the app UI. The account is already logged in. Do not post, comment, like, follow, send DMs, make payments, change account settings, or perform any irreversible action. If the app asks for a non-destructive permission (e.g., notification), allow it once and continue.

Navigation goal:
1. Open 小红书 app or Start from the currently open 小红书 app home feed (the "发现" or "推荐" tab with a waterfall of note cards).
2. For each note card visible in the feed, tap to enter its detail page.
3. On the detail page, scroll down slowly to reveal all visible text and metadata before extracting fields.
4. When the current screenshot is already a note detail page with enough visible information to record, choose `extract` and put the structured note JSON in the `data` field.
5. After the page is extracted, go back the home feed(step 2), and navigate to the next unseen detail page.
6. If the mission is complete or the UI becomes stuck in a way you cannot overcome safely, choose `quit`.
7. If you encounter a video note instead of a text/image note, still collect whatever metadata is visible (title, author, etc.) and note that it is a video note.
8. Avoid ads (marked with 广告/赞助) and live-stream cards — skip these.
9. Collect exactly 10 distinct notes. Avoid duplicates by tracking author name + title (or first sentence if no title).
10. Use the previous actions and prior extracted notes in the chat history as your working memory. Before entering a note card, compare it against notes already opened or extracted; if the author + title/first sentence matches a prior note, do not enter it again.
11. After returning to the feed, do not tap the same visible card again just because it is still in the same position. Deliberately choose a different unseen card.
12. If you accidentally re-enter a note that was already extracted, do not extract it again. Immediately navigate back and continue with a different note.
13. When deciding the next card, prefer cards whose author/title are clearly different from previously extracted notes, even if that means skipping an ambiguous card for now.

Data collection goal — for each note, collect as many of these fields as visible:

- `note_title`: the title or first line of the note body
- `author_name`: the author's display name
- `author_id`: the author's 小红书号 if visible
- `publish_time`: the relative or absolute timestamp shown (e.g. "3小时前", "昨天", "2025-03-15")
- `like_count`: number of likes/点赞
- `collect_count`: number of saves/收藏
- `comment_count`: number of comments/评论
- `share_count`: number of shares/分享
- `note_text`: the full body text of the note (truncated after ~500 chars)
- `tags`: any hashtags or topic tags visible on the note (list of strings)
- `location`: location/POI tag if the note has one
- `images_count`: number of images in the note (estimate from the dot indicator or swipe count)
- `is_video`: true if the note is a video note, false otherwise
- `notes`: any other noteworthy info

If a field is not visible or not applicable, use `null`. Do not invent data.

Completion:
- When 10 distinct notes have been collected, choose `quit` with `status` = `success` and include the final JSON object in the `data` field.
- If the mission cannot continue safely or the UI is irrecoverably stuck, choose `quit` with `status` = `failure`.
- The JSON object in `data` must use this schema:

```json
{
  "task": "xhs_note_crawler",
  "app": "小红书",
  "page": "推荐",
  "notes_collected": 0,
  "notes": [
    {
      "note_title": null,
      "author_name": null,
      "author_id": null,
      "publish_time": null,
      "like_count": null,
      "collect_count": null,
      "comment_count": null,
      "share_count": null,
      "note_text": null,
      "tags": [],
      "location": null,
      "images_count": null,
      "is_video": false,
      "notes": null
    }
  ],
  "warnings": []
}
```

