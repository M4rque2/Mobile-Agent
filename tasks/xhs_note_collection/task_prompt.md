# XHS Note Crawling Prompt

Collect note detail information from the 小红书 app's home feed. Open individual note detail pages one by one, extract visible metadata, then record everything in a structured JSON output.

Work only inside the app UI. The account is already logged in. Do not post, comment, like, follow, send DMs, make payments, change account settings, or perform any irreversible action. If the app asks for a non-destructive permission (e.g., notification), allow it once and continue.

Navigation goal:
- Start from the currently open 小红书 app home feed (the "发现" or "推荐" tab with a waterfall of note cards).
- Stay on the main feed; do not enter the search page, profile page, messages, or shop.
- For each note card visible in the feed, tap to enter its detail page.
- On the detail page, scroll down slowly to reveal all visible text and metadata before extracting fields.
- After extracting one note's data, go back to the feed and scroll to find fresh notes.
- If you encounter a video note instead of a text/image note, still collect whatever metadata is visible (title, author, etc.) and note that it is a video note.
- Avoid ads (marked with 广告/赞助) and live-stream cards — skip these.
- Collect exactly 10 distinct notes. Avoid duplicates by tracking author name + title (or first sentence if no title).

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
- When 10 distinct notes have been collected, finish with action `answer`, not `terminate`.
- Put a single JSON object in the `text` field of the answer action.
- The JSON object must use this schema:

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

Use this exact action shape for the final step:

```text
Action: Return collected note data.
<tool_call>
{"name":"mobile_use","arguments":{"action":"answer","text":"{\"task\":\"xhs_note_crawler\",\"app\":\"小红书\",\"page\":\"推荐\",\"notes_collected\":0,\"notes\":[],\"warnings\":[]}"}}
</tool_call>
```