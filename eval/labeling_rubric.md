# Labeling rubric

You are filling in one column, `problem_family`, in `labeling_sheet.csv`. Open it in Excel or Google Sheets.
Read the `title` and `text`; use the `url` only if you cannot tell what a short comment is replying to.
Roughly 20 seconds per row. Don't look for a "right" answer beyond what the text says; if unsure, use `other`.

## Values (type exactly one, lowercase)

| Value | Use it when the text is about... |
|---|---|
| `search_or_retrieval` | Trying to find or re-find photos or videos that exist: search returns nothing or wrong results, can't locate a photo, browsing or scrolling can't get there, can't find a photo by person, date or place, photos in the wrong place or with the wrong date so they can't be found. |
| `backup_or_sync` | Photos not uploading, not syncing between devices, or unsure whether they were backed up. |
| `account_or_access_loss` | Photos exist but the person can't get into the account or device that holds them (password, phone lost or stolen, account closed). |
| `deletion_or_corruption` | Photos deleted, vanished, or damaged, and the person wants them recovered from trash or backup, or a file is broken or unreadable. |
| `quality_or_editing` | Picture quality, compression, editing tools, camera behaviour. |
| `billing_or_storage` | Plans, storage limits or prices, with no finding problem. |
| `other` | Not about photos, praise with no problem, a question you can't classify, too vague, or a reply that gives no clue. |
| `not_english` | The text is mostly not English (including Hindi or Telugu written in English letters). |

## Rules for tricky cases

- "Can't find my photos after the update" is `search_or_retrieval`. "Photos are gone and I want them back from trash" is `deletion_or_corruption`.
- If both apply, pick the one the person is mainly asking about.
- A reply in a forum thread (source `google_community`, or a Reddit or YouTube comment) is labeled by what the reply itself is about, using the title for context. A helper explaining how to search is `search_or_retrieval`; a helper explaining how to restore deleted items is `deletion_or_corruption`; a greeting like "Welcome to the community" is `other`.
- Praise ("great app") and complaints about the app in general are `other` unless a photo problem is stated.
- Judge only the text. Do not guess the source or whether a keyword filter would have picked it.

## `notes` column
Optional. Use it for anything odd, or when you were torn between two values (write both).
