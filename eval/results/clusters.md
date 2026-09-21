# Phase 5 result: retrieval problem clusters

287 retrieval failures (extractions whose failure mode is not `not_a_search_problem`) grouped into 9 ranked clusters (260 items, 91%) plus 2 residual clusters that were too mixed to rank. Counts are mentions in a sample of public posts, not prevalence, and one thread can contribute many items (see the threads column).

## Ranking rule

Each cluster gets five measures scaled 0 to 1 across the ranked clusters, then a weighted sum: frequency 35%, spread 15%, severity 20%, underserved 20%, recency 10%. *Frequency* is distinct threads; *spread* is the number of sources; *severity* is the mean of inconvenience/unclear 1, time loss 2, emotional or data loss 3; *underserved* is the share of items where the person could not find the photo, times the share with no workaround; *recency* is the share of dated items from the last six months. The weights are a judgment, not a measurement.

| # | Score | Cluster | Items | Threads | Sources | Not found | Workaround | Recent |
|---|---|---|---|---|---|---|---|---|
| 8 | 0.82 | Search returns nothing, wrong or irrelevant results | 59 | 53 | 6 | 73% | 14% | 61% |
| 5 | 0.48 | Update removed or rearranged browsing features | 39 | 32 | 7 | 49% | 8% | 51% |
| 14 | 0.43 | General Difficulty Locating Media | 14 | 14 | 3 | 86% | 0% | 79% |
| 3 | 0.42 | Finding and Ordering Photos by Metadata | 25 | 24 | 7 | 56% | 8% | 44% |
| 12 | 0.39 | Broken Search and Error Messages | 27 | 23 | 6 | 48% | 0% | 81% |
| 1 | 0.35 | People and face recognition, grouping and naming problems | 40 | 29 | 4 | 30% | 10% | 95% |
| 11 | 0.29 | Missing Old Photos and Screenshots | 20 | 17 | 3 | 70% | 0% | 100% |
| 6 | 0.22 | Broken keyword and image search | 13 | 12 | 4 | 46% | 0% | 62% |
| 4 | 0.16 | AI (Gemini) search replaced or worsened classic search | 23 | 15 | 4 | 35% | 9% | 87% |
| 7 | n/a | [residual] Finding Specific Photos in Large Libraries | 13 | 13 | 5 | 31% | 8% | 62% |
| 15 | n/a | [residual] Advanced Filtering and Content Management | 14 | 13 | 7 | 50% | 7% | 50% |

**How much the order depends on the rule** (top three cluster numbers under each weighting): default weights: [8, 5, 14]; equal weights: [8, 14, 5]; frequency only: [8, 5, 1]; underserved and severity: [14, 8, 3].

## Clusters

### 8. Search returns nothing, wrong or irrelevant results

Search finds nothing, misses photos that exist, or returns wrong ones (objects, animals, file names, text in images, descriptions), with no update or change mentioned.

- Items 59 in 53 threads; sources {'appstore': 5, 'google_community': 21, 'hackernews': 11, 'play': 7, 'reddit': 12, 'stackexchange': 3}; products {'google_photos': 36, 'apple_photos': 9, 'unknown': 8, 'amazon_photos': 4}
- Failure modes {'vocabulary_mismatch': 28, 'not_indexed': 15, 'ranking_failure': 12, 'cue_mismatch': 4}; severity {'inconvenience': 48, 'time_loss': 11}; photo types (where stated) {'person_face_related': 8, 'screenshot_functional': 5, 'early_digital': 1, 'received_forwarded': 1}
- Memory cues remembered {'appearance': 21, 'when': 3, 'text_in_photo': 6, 'provenance': 2, 'where': 9, 'who': 4, 'purpose': 2, 'event': 2}; forgotten none
- Quotes:
  - "if I search in Google photos I can find anything eg searched for Nokia phone but in Apple photos can’t find anything." (appstore, `appstore:au:14506956127`)
  - "After uploading all my images and videos over 3 days, the Google photos search by faces doesnt work either." (google_community, `gcomm:430853685`)
  - "I actually couldn't get Photos address search to work right in my testing before writing my previous comment" (hackernews, `hackernews:42540175`)
  - "Photo search is great if you can actually get to it, but all I see is today's memories." (play, `play:28d74cca-0514-46af-83c3-4c70c27f00d2`)
  - "Descriptions added to photos do not show in search results" (reddit, `reddit:1w5exw4`)

### 5. Update removed or rearranged browsing features

After an app update or redesign, layouts, albums, date labels, zoom levels, places or other browsing features were removed or rearranged, making photos harder to find. Includes complaints where the person did not say it used to work.

- Items 39 in 32 threads; sources {'appstore': 12, 'google_community': 10, 'hackernews': 3, 'play': 3, 'reddit': 8, 'stackexchange': 2, 'youtube': 1}; products {'google_photos': 17, 'apple_photos': 14, 'unknown': 5, 'amazon_photos': 3}
- Failure modes {'regression': 31, 'unspecified': 8}; severity {'inconvenience': 37, 'time_loss': 1, 'emotional_loss': 1}; photo types (where stated) {'screenshot_functional': 2, 'received_forwarded': 2, 'person_face_related': 1}
- Memory cues remembered {'when': 2, 'appearance': 4, 'who': 1, 'provenance': 1, 'purpose': 1}; forgotten none
- Quotes:
  - "You removed the grouping by month. Hard to find picture nows." (appstore, `appstore:ca:13755783095`)
  - "When I get a memory suggestion for my photos, why doesn’t it show that to me when I click on it?  It used to, now it takes me to the homepage and I never see the memory’s" (google_community, `gcomm:430794074`)
  - "Additional my mail search and photo search broke with Apple Intelligence/iOS18 integration." (hackernews, `hackernews:44965337`)
  - "When viewing an individual photo from years ago, if I click off that photo then rather than retaining that time view the app goes automatically racing forward in time to resume today's date view!" (play, `play:4ebe787f-657f-4ce3-ace9-d451dc4e18a9`)
  - "I can no longer search for photos by date" (reddit, `reddit:1v3gsds`)

### 14. General Difficulty Locating Media

Posts about struggling to find, filter, or access general photos, videos, hidden folders, or archived items.

- Items 14 in 14 threads; sources {'appstore': 4, 'google_community': 1, 'play': 9}; products {'amazon_photos': 4, 'google_photos': 3, 'ente': 3, 'apple_photos': 2}
- Failure modes {'unspecified': 14}; severity {'time_loss': 2, 'inconvenience': 12}; photo types (where stated) {'early_digital': 1}
- Memory cues remembered none; forgotten none
- Quotes:
  - "it takes me almost 5 minutes to find the picture I really want" (appstore, `appstore:au:13880317298`)
  - "I can't find some of my pictures and videos" (google_community, `gcomm:468696040`)
  - "cant find photo in some folder" (play, `play:28c72136-6fdf-4791-92a3-a165dbfc477c`)
  - "if you think you want to save it, or find it later - good luck. You will NEVER be able to view the video again as it will be lost forever." (appstore, `appstore:ca:13835632545`)
  - "Useless as there is no way to filter or find your videos" (appstore, `appstore:gb:13977758900`)

### 3. Finding and Ordering Photos by Metadata

This cluster includes issues where users cannot locate, sort, or correctly view photos and videos due to problems with dates, locations, captions, albums, or missing library items.

- Items 25 in 24 threads; sources {'appstore': 2, 'google_community': 3, 'hackernews': 2, 'play': 1, 'reddit': 10, 'stackexchange': 5, 'youtube': 2}; products {'google_photos': 17, 'apple_photos': 4, 'ente': 1, 'immich': 1}
- Failure modes {'missing_wrong_metadata': 25}; severity {'inconvenience': 23, 'time_loss': 2}; photo types (where stated) {'migrated': 11, 'received_forwarded': 2, 'scanned_print': 1, 'early_digital': 3}
- Memory cues remembered {'where': 3, 'who': 1, 'when': 3, 'text_in_photo': 1}; forgotten {'when': 1}
- Quotes:
  - "expect about 1% of your pictures to end up with a wrong date (the date of the takeout request) and no other metadata." (appstore, `appstore:us:14387414782`)
  - "While Khulna city is correctly pinpointed on the map, it is not appearing in the main city list." (google_community, `gcomm:435082313`)
  - "No compatible libraries found, says the unhelpful error message." (hackernews, `hackernews:41410411`)
  - "The dates shown on the app are not always correct, for example dated Jan 23rd will be found in Feb 3rd?" (play, `play:63629071-bb5d-439a-805f-1f21c94120ee`)
  - "New phone shows photos in the wrong dates" (reddit, `reddit:11ga051`)

### 12. Broken Search and Error Messages

Posts about search functions failing completely, returning no results, or throwing errors when looking up images.

- Items 27 in 23 threads; sources {'youtube': 1, 'reddit': 7, 'appstore': 1, 'google_community': 12, 'hackernews': 3, 'play': 3}; products {'google_photos': 17, 'apple_photos': 6, 'amazon_photos': 2, 'unknown': 2}
- Failure modes {'unspecified': 27}; severity {'inconvenience': 25, 'time_loss': 1, 'unclear': 1}; photo types (where stated) {'screenshot_functional': 1, 'person_face_related': 1}
- Memory cues remembered {'appearance': 1, 'where': 2}; forgotten none
- Quotes:
  - "my searches have come up with nothing" (youtube, `youtube:UgzGKehizToueR_lbQB4AaABAg`)
  - "Search in iphone not working" (reddit, `reddit:1urknr9`)
  - "Every #*%#*ng search does not help either. Trying to locate a photo waste damn time." (appstore, `appstore:in:13969891586`)
  - "How do I perform a search?" (google_community, `gcomm:433667075`)
  - "Also, even the local search inside of Apple Photos doesn't work correctly either." (hackernews, `hackernews:46755195`)

### 1. People and face recognition, grouping and naming problems

Faces are not detected, grouped or recognised correctly, people are mislabeled or merged, or people, places and things sections and names cannot be managed.

- Items 40 in 29 threads; sources {'google_community': 29, 'play': 3, 'reddit': 7, 'stackexchange': 1}; products {'google_photos': 35, 'unknown': 2, 'ente': 1, 'apple_photos': 1}
- Failure modes {'identity_failure': 40}; severity {'emotional_loss': 1, 'inconvenience': 34, 'unclear': 4, 'time_loss': 1}; photo types (where stated) {'person_face_related': 36, 'received_forwarded': 1, 'migrated': 1}
- Memory cues remembered {'who': 3}; forgotten none
- Quotes:
  - "Previously, my photos were automatically organized into face groups for my family members. However, all face groupings have now disappeared, and the feature is no longer functioning as expected." (google_community, `gcomm:430877696`)
  - "Faces are not syncing correctly when I log into the Android app, only a few faces show in the search tab." (play, `play:c0a0fad8-815a-4944-9654-5dd57777ccf8`)
  - "Human face recognition stopped working for months – now fixed" (reddit, `reddit:1q7ghbb`)
  - "on iPhone all pictures available, people search doesn't work (empty) results when selecting people" (stackexchange, `stackexchange:apple:386769`)
  - "Google photos unable to group photo by people faces" (google_community, `gcomm:432622767`)

### 11. Missing Old Photos and Screenshots

Posts about being unable to find specific older photos, screenshots, or media from particular years and dates.

- Items 20 in 17 threads; sources {'google_community': 13, 'play': 4, 'reddit': 3}; products {'google_photos': 17, 'onedrive': 2, 'amazon_photos': 1}
- Failure modes {'unspecified': 20}; severity {'inconvenience': 20}; photo types (where stated) {'early_digital': 2, 'screenshot_functional': 4}
- Memory cues remembered {'when': 4, 'where': 1, 'event': 1, 'appearance': 1}; forgotten none
- Quotes:
  - "My old photos and video of 2013 are not showing" (google_community, `gcomm:437015100`)
  - "What do I need to do to find certain photos?" (play, `play:80bcf2b4-57ae-41fc-8439-2279ba71d9f6`)
  - "Photos missing on main screen" (reddit, `reddit:1tmlbmg`)
  - "how to find photos tken in 2012" (google_community, `gcomm:465289959`)
  - "I can't find my ss in google photos as well as phone gallery they just disappeared and many old photos specially screenshots" (google_community, `gcomm:465416826`)

### 6. Broken keyword and image search

Posts reporting that general keyword search, text search within screenshots, or internet image search functions have completely stopped working or return inaccurate results.

- Items 13 in 12 threads; sources {'appstore': 2, 'google_community': 4, 'play': 3, 'reddit': 4}; products {'google_photos': 7, 'apple_photos': 3, 'amazon_photos': 2, 'unknown': 1}
- Failure modes {'regression': 13}; severity {'inconvenience': 12, 'time_loss': 1}; photo types (where stated) {'screenshot_functional': 2}
- Memory cues remembered {'appearance': 1}; forgotten none
- Quotes:
  - "Now, the search function no longer works!" (appstore, `appstore:ca:12686933450`)
  - "What the heck happened to image search? Where you could search the Internet for a specific image." (google_community, `gcomm:441998886`)
  - "can't search photos. suddenly happened" (play, `play:845be447-2f28-49a5-902c-fdc30559531c`)
  - "idk why but i try to find a screenshot with a certain screenname or word but it never comes up" (reddit, `reddit:1iaob2b`)
  - "The new update ruined my favourite feature.. Image search!" (appstore, `appstore:ca:13746457879`)

### 4. AI (Gemini) search replaced or worsened classic search

Since Gemini or AI search was introduced or updated, the classic search that worked before is gone or gives worse results, including object, location and keyword search.

- Items 23 in 15 threads; sources {'appstore': 1, 'google_community': 6, 'play': 5, 'reddit': 11}; products {'google_photos': 12, 'unknown': 7, 'amazon_photos': 3, 'apple_photos': 1}
- Failure modes {'regression': 23}; severity {'inconvenience': 22, 'unclear': 1}; photo types (where stated) {'person_face_related': 5}
- Memory cues remembered {'appearance': 1}; forgotten none
- Quotes:
  - "After updating to 26.5, trips have disappeared across all devices! Now already named people get UNRECOGNISED!!" (appstore, `appstore:gb:14544646523`)
  - "Search in Google photos has been replaced by a ridiculous 'hammer' called Gemini AI" (google_community, `gcomm:432527747`)
  - "in particular search functions now terrible I can't find any photos of looking for" (play, `play:a063c498-e373-40ef-8576-598daab29f0d`)
  - "Search has complete stopped working for me." (reddit, `reddit:1qbt12z`)
  - "Why can’t I search by location anymore??" (google_community, `gcomm:435285118`)

### 7. [residual] Finding Specific Photos in Large Libraries

The user struggles to locate, filter, or browse specific photos and videos within a massive, unorganized, or slow-loading library.

- Items 13 in 13 threads; sources {'appstore': 4, 'hackernews': 4, 'play': 2, 'reddit': 1, 'stackexchange': 2}; products {'google_photos': 4, 'apple_photos': 3, 'onedrive': 3, 'unknown': 3}
- Failure modes {'content_type_gap': 5, 'scale_or_speed': 8}; severity {'inconvenience': 6, 'time_loss': 7}; photo types (where stated) {'screenshot_functional': 3, 'received_forwarded': 1}
- Memory cues remembered {'appearance': 2, 'where': 1}; forgotten none
- Quotes:
  - "It is not as easy to filter and find photos that you haven’t taken with your iPhone." (appstore, `appstore:au:13434514362`)
  - "I have too many pictures to sort through now. I've tried multiple times; I don't have enough time to go through them all." (hackernews, `hackernews:38069278`)
  - "Only thing I'm missing is 1) Contextual search and 2) Sharing albums with people it only shows their email." (play, `play:34b2a5eb-23c3-4691-ac33-d6f6de18ade0`)
  - "photos, I cant find the latest screenshots at all" (stackexchange, `stackexchange:android:229184`)
  - "Finding specific photo in a large album" (reddit, `reddit:1vcu3cs`)

### 15. [residual] Advanced Filtering and Content Management

Posts about finding specific items among thousands, extracting photos from auto-generated slideshows, or poor AI search.

- Items 14 in 13 threads; sources {'appstore': 1, 'google_community': 3, 'hackernews': 4, 'play': 1, 'reddit': 2, 'stackexchange': 2, 'youtube': 1}; products {'apple_photos': 6, 'google_photos': 6, 'ente': 1, 'unknown': 1}
- Failure modes {'unspecified': 14}; severity {'inconvenience': 14}; photo types (where stated) {'person_face_related': 2, 'early_digital': 1}
- Memory cues remembered {'who': 1}; forgotten none
- Quotes:
  - "couldn’t find pics properly" (appstore, `appstore:in:13790630342`)
  - "how do I filter for photos that are not part of any albums?" (google_community, `gcomm:444388254`)
  - "Apple Photos search is just bad, very bad." (hackernews, `hackernews:39088387`)
  - "It detects the thousands upon thousands of album art on my microSD, so I can never find the camera's photos folder as there is no option to search by folder name" (play, `play:8052831c-22e8-4255-ada1-c23a350c2cde`)
  - "Is there a search term for finding photos I have edited?" (reddit, `reddit:1uinuct`)

## What people remember and forget

Over retrieval failures only. These counts are small and include example searches, not just memories of one specific photo.

| Cue type | Remembered | Forgotten | Unknown |
|---|---|---|---|
| appearance | 31 | 0 | 0 |
| event | 3 | 0 | 0 |
| provenance | 3 | 0 | 0 |
| purpose | 3 | 0 | 0 |
| text_in_photo | 7 | 0 | 0 |
| when | 12 | 1 | 0 |
| where | 16 | 0 | 0 |
| who | 10 | 0 | 0 |

Photo type `early_digital`:

| Cue type | Remembered | Forgotten | Unknown |
|---|---|---|---|
| text_in_photo | 1 | 0 | 0 |
| when | 2 | 0 | 0 |

Photo type `migrated`:

| Cue type | Remembered | Forgotten | Unknown |
|---|---|---|---|
| text_in_photo | 1 | 0 | 0 |
| when | 1 | 0 | 0 |
| where | 1 | 0 | 0 |

Photo type `person_face_related`:

| Cue type | Remembered | Forgotten | Unknown |
|---|---|---|---|
| appearance | 10 | 0 | 0 |
| event | 1 | 0 | 0 |
| where | 4 | 0 | 0 |
| who | 8 | 0 | 0 |

Photo type `received_forwarded`:

| Cue type | Remembered | Forgotten | Unknown |
|---|---|---|---|
| appearance | 1 | 0 | 0 |
| provenance | 2 | 0 | 0 |
| when | 3 | 0 | 0 |
| who | 2 | 0 | 0 |

Photo type `scanned_print`:

| Cue type | Remembered | Forgotten | Unknown |
|---|---|---|---|
| when | 0 | 1 | 0 |
| where | 1 | 0 | 0 |

Photo type `screenshot_functional`:

| Cue type | Remembered | Forgotten | Unknown |
|---|---|---|---|
| appearance | 3 | 0 | 0 |
| purpose | 3 | 0 | 0 |
| text_in_photo | 2 | 0 | 0 |
| where | 2 | 0 | 0 |

## Limitations

- Clusters were checked by a single model rater on 10 items each; six of fifteen first-pass clusters failed the 8-of-10 rule and were merged, renamed or set aside (`eval/cluster_audit.json`).
- After the merges, a fresh 10-item re-check gave cluster 1 10/10, cluster 4 10/10, cluster 8 8/10 and cluster 5 7/10. Cluster 5 is a borderline fail: two of its ten items are off-topic Hacker News and Stack Exchange comments the extractor should have set aside. Treat its rank with caution.
- Failure-mode groups came from the extractor, which agreed with my labels about 75% of the time on 100 items; 'unspecified' clusters may hide regressions the extractor did not call.
- Threads, not items, are the fair unit for frequency; a single popular thread can inflate an item count.
- Sources skew: Google Photos is about half of the items and most non-Google clusters rest on very few threads.
