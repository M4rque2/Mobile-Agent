# XHS Note Crawling Prompt

Collect note detail information from the 小红书 app's home feed. Open individual note detail screens one by one, extract visible metadata, then record everything in a structured JSON output.

Work only inside the app UI. The account is already logged in. Do not post, comment, like, follow, send DMs, make payments, change account settings, or perform any irreversible action. If the app asks for a non-destructive permission (e.g., notification), allow it once and continue.

Navigation goal:
1. Open 小红书 app.
2. On the home feed screen, tap each visible note card to enter its detail screen.
3. First identify whether the detail screen is a text/image note or a video note.
4. For a text/image note detail screen, scroll down slowly only if needed to reveal more note text, comments, or metadata before extracting fields.
5. For a video note detail screen, do not scroll down to reveal more metadata. In 小红书 video detail screens, vertical swiping moves to the next video instead of revealing more content for the current note.
6. When the current screenshot is already a note detail screen with enough visible information to record, choose `extract` and put only the current note's structured JSON in the `data.notes` array. Do not repeat notes that were extracted in previous turns.
7. After the screen is extracted, go back to the home feed screen (step 2), and navigate to the next unseen detail screen.
8. For both text/image notes and video notes, the only reliable way to move to another note is to go back to the home feed screen and manually select a different note card. Do not use vertical swipes inside a detail screen as a "next note" action.
9. If the mission is complete or the UI becomes stuck in a way you cannot overcome safely, choose `quit`.
10. If you encounter a video note instead of a text/image note, still collect whatever metadata is visible (title, author, etc.) and note that it is a video note.
11. Avoid ads (marked with 广告/赞助) and live-stream cards — skip these.
12. Collect exactly 10 distinct notes. Avoid duplicates by tracking author name + title (or first sentence if no title).
13. Use the previous actions and prior extracted notes in the chat history as your working memory. Before entering a note card, compare it against notes already opened or extracted; if the author + title/first sentence matches a prior note, do not enter it again.
14. After returning to the feed, do not tap the same visible card again just because it is still in the same position. Deliberately choose a different unseen card.
15. If you accidentally re-enter a note that was already extracted, do not extract it again. Immediately navigate back and continue with a different note.
16. When deciding the next card, prefer cards whose author/title are clearly different from previously extracted notes, even if that means skipping an ambiguous card for now.

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

Output rules:
- On each `extract`, `data.notes` must contain exactly one note: the current note visible on this detail screen.
- Do not include previously extracted notes in an `extract` response. The local runner appends each extracted note to `output.jsonl`.
- If the immediately previous assistant turn was an `extract` for the same visible note, do not choose `extract` again. Choose `navigate` and go back to the home feed screen.
- Use `notes_collected` as the total count including the current note, but keep `data.notes` limited to the current note only.

Completion:
- When 10 distinct notes have been collected, choose `quit` with `status` = `success` and include the final JSON object in the `data` field.
- If the mission cannot continue safely or the UI is irrecoverably stuck, choose `quit` with `status` = `failure`.
- The JSON object in `data` must use this schema:

```json
{
  "task": "xhs_note_crawler",
  "app": "小红书",
  "screen": "推荐",
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
