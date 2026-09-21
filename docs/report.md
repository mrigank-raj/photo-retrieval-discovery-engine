# Photo retrieval: what public feedback shows

Findings from the Discovery Engine, run on public reviews, forum threads and comments collected in September 2026. Every quote below is verbatim from the linked post. Numbers are as of 2026-09-21 and can be regenerated from `data/engine.db` (see the appendix).

## In brief

- **The biggest, most consistent problem is search that returns nothing or the wrong thing.** The top cluster (59 items in 53 threads across 6 sources) has a high not-found rate (73%), and only 14% mention any workaround. It ranks first under three of four ways of weighting the score.
- **Most "I can't find my photos" complaints are not search problems.** Two thirds of the extracted items (585 of 872) were, on a closer read, about deletion, backup, sync, account access, app bugs or praise. Of the 740 items the first-pass classifier called retrieval, 61% turned out not to be a failure to find a photo.
- **Updates that remove or rearrange ways of browsing are the second theme** (39 items, 7 sources), and Gemini/AI search replacing classic search is a smaller, very recent one (23 items, 87% from the last six months). Fewer than one in five of the AI-search complaints asks for the old search back; most describe worse or wrong results.
- **Old photos are almost invisible in this data.** Only 34% of the 287 retrieval failures name a photo type and only 6% give a photo's age. The old-photo cases that do appear are dominated by lost or wrong dates after scanning or migration.
- **This data cannot say what people remember or forget.** Across 872 extracted items there are 138 remembered-cue mentions (many are example searches, not memories) and three "forgotten" cues, of which one is a clear first-person statement.

<!-- insights:start -->
## Key insights

Written by the engine from measured contrasts in the data, then checked in code: every number must appear in the facts behind it, confidence is set from sample size and source spread, and wording that overstates a minority is rejected. Read the evidence links before relying on any of them.

### 1. 61% of complaints that first looked like search problems were not about finding photos.

**Confidence: high** (740 items, 7 sources).
- "When i try this all the photos come up and what's app photos and screenshorts didn't come up what should i do😢" (youtube, [link](https://www.youtube.com/watch?v=7X63jxS8ewE&lc=Ugzo1vfeTy9ICPpzCb54AaABAg))
- "The locations of photos not known and cannot be known for easily access , resulting photos duplicated everywhere." (appstore, [link](https://itunes.apple.com/ca/review?id=1584215428&type=Purple%20Software))
- "Select recents. Select a folder. It doesn’t open the folder." (appstore, [link](https://itunes.apple.com/us/review?id=327630330&type=Purple%20Software))

### 2. Although 14 percent of posts about incorrect search results mention a workaround, posts regarding general difficulty locating media and missing old photos have a zero percent workaround rate.

**Interpretation (a hypothesis to test, not a finding).** This indicates that certain types of media location failures leave posts completely without solutions, making these areas critical to investigate. Understanding why these specific categories lack workarounds could help address the most severe finding failures.

**Confidence: medium** (34 items, 4 sources). **Caveat.** The analysis is limited by the small sample size of 14 posts for general difficulty locating media and 20 posts for missing old photos and screenshots.
- "it takes me almost 5 minutes to find the picture I really want" (appstore, [link](https://itunes.apple.com/au/review?id=1584215428&type=Purple%20Software))
- "My old photos and video of 2013 are not showing" (google_community, [link](https://support.google.com/photos/thread/437015100))
- "cant find photo in some folder" (play, [link](https://play.google.com/store/apps/details?id=io.ente.photos&reviewId=28c72136-6fdf-4791-92a3-a165dbfc477c))

### 3. Only 20 percent of the 287 failure posts use wording signaling that something changed, though this rises to 56 percent for posts about updates removing or rearranging browsing features.

**Interpretation (a hypothesis to test, not a finding).** This suggests that finding failures are commonly related to long-standing issues rather than recent updates or changes. Investigating persistent, unchanged system behaviors may yield more improvement than focusing solely on recent updates.

**Confidence: medium** (58 items, 7 sources). **Caveat.** This finding is limited because some clusters, such as general difficulty locating media, had zero percent of posts using change-related wording.
- "Now, the search function no longer works!" (appstore, [link](https://itunes.apple.com/ca/review?id=1584215428&type=Purple%20Software))
- "When I get a memory suggestion for my photos, why doesn’t it show that to me when I click on it?  It used to, now it takes me to the homepage and I never see the memory’s" (google_community, [link](https://support.google.com/photos/thread/430794074))
- "Now it returns fewer matches on the same search. I tend to search the same things a few times a year as a supplement to some story and it's been frustrating to see in real time, a picture that used to come up when searching "car" or "guitar" is missing and instead unrelated pictures returned." (hackernews, [link](https://news.ycombinator.com/item?id=46165697))

### 4. Forum and Reddit posts provide more diagnostic detail than store reviews, with 23 percent stating a cue and 15 percent quoting a query compared to just 7 percent and 3 percent in store reviews.

**Interpretation (a hypothesis to test, not a finding).** This suggests that analysts looking to understand the specific context of finding failures should focus on forum discussions rather than store reviews. Investigating forums will provide more concrete examples of what posts were searching for when they failed.

**Confidence: high** (282 items, 6 sources). **Caveat.** The comparison is limited because both sources share the exact same median length of 45 words per post.
- "it takes me almost 5 minutes to find the picture I really want" (appstore, [link](https://itunes.apple.com/au/review?id=1584215428&type=Purple%20Software))
- "cant find photo in some folder" (play, [link](https://play.google.com/store/apps/details?id=io.ente.photos&reviewId=28c72136-6fdf-4791-92a3-a165dbfc477c))
- "After an update, searches only look for people, not things." (google_community, [link](https://support.google.com/photos/thread/437393828))

### 5. Apple Photos posts complain about updates removing or rearranging browsing features 24 percentage points more than Google Photos posts, while Google Photos posts complain about people and face recognition 20 percentage points more than Apple Photos posts.

**Interpretation (a hypothesis to test, not a finding).** This suggests that the two platforms suffer from distinct types of finding failures, with one struggling more with interface changes and the other with recognition features. Investigating these platform-specific pain points can help target platform-specific fixes.

**Confidence: medium** (40 items, 4 sources). **Caveat.** This comparison is limited by the unequal sample sizes of 161 Google Photos failures compared to only 40 Apple Photos failures.
- "Search in iphone not working" (reddit, [link](https://www.reddit.com/r/iphone/comments/1urknr9/search_in_iphone_not_working/))
- "I saved a png file to camera role 3 times today. Only the third one came up in the photos." (appstore, [link](https://itunes.apple.com/au/review?id=1584215428&type=Purple%20Software))

### 6. While 70 percent of all failure posts occurred in the last six months, 100 percent of posts about missing old photos and screenshots were from this recent period.

**Interpretation (a hypothesis to test, not a finding).** This suggests that certain finding issues are highly concentrated in recent months, pointing to recent system changes or updates as potential areas of concern. Investigating why these specific issues have suddenly emerged can help resolve recent regressions.

**Confidence: high** (83 items, 5 sources). **Caveat.** This finding is limited because some issues, such as finding and ordering photos by metadata, had only 44 percent of posts occurring in the last six months.
- "After updating to 26.5, trips have disappeared across all devices! Now already named people get UNRECOGNISED!!" (appstore, [link](https://itunes.apple.com/gb/review?id=1584215428&type=Purple%20Software))
- "Previously, my photos were automatically organized into face groups for my family members. However, all face groupings have now disappeared, and the feature is no longer functioning as expected." (google_community, [link](https://support.google.com/photos/thread/430877696))
- "Search needs better options for names of people, which currently requires creating an album of each person, with multiple versions created of individuals all too frequently." (play, [link](https://play.google.com/store/apps/details?id=com.amazon.clouddrive.photos&reviewId=37c17711-6778-4c9b-a9c2-3a13f895ecb9))

### 7. Out of 70 posts stating how they searched, 38 posts used a descriptive keyword while only 12 posts searched by a year or date.

**Interpretation (a hypothesis to test, not a finding).** This suggests that posts rely heavily on descriptive nouns rather than temporal cues when trying to locate photos. Investigating how well systems index and retrieve specific objects or nouns is therefore a high-priority area.

**Confidence: high** (70 items, 5 sources). **Caveat.** This finding is limited because only 70 posts explicitly stated how they searched.
- "if I search in Google photos I can find anything eg searched for Nokia phone but in Apple photos can’t find anything." (appstore, [link](https://itunes.apple.com/au/review?id=1584215428&type=Purple%20Software))
- "After an update, searches only look for people, not things." (google_community, [link](https://support.google.com/photos/thread/437393828))
- "Google photos search doesn't work well at all for me." (hackernews, [link](https://news.ycombinator.com/item?id=41947777))


### Weaker signals and blind spots

### 1. Data or emotional loss is mentioned in 2 of 287 failures (1%) against 15 of 585 non-search posts (3%).

**Interpretation (a hypothesis to test, not a finding).** Explicit stakes language is rare in both groups but about three times more common in recovery, sync and other non-search posts than in search failures.

**Confidence: low** (17 items, 5 sources). **Caveat.** Severity is assigned by the extraction model and most posts do not state stakes, so this counts only explicit loss language.
- "my important photos have been permanently deleted from Google Photos and the Bin is also empty" (google_community, [link](https://support.google.com/photos/thread/468717478))
- "Where are my missing album pictures that I uploaded from my Galaxy phone !Still missing!!! Also all the pictures I purchased from you in your photo book Gone!" (play, [link](https://play.google.com/store/apps/details?id=com.google.android.apps.photos&reviewId=08146e97-2c71-4eb5-859f-e95bc0eba14a))
- "I tried everything from recovery software to clearing data to searching in my files. NOTHING" (reddit, [link](https://www.reddit.com/r/googlephotos/comments/1gz0pm1/i_cant_find_the_photos_i_took_today/))

### 2. 8 posts say people or face search still works while other search does not.

**Confidence: low** (8 items, 3 sources). **Caveat.** A small group matched by keywords; read the quotes before drawing conclusions.
- "After an update, searches only look for people, not things." (google_community, [link](https://support.google.com/photos/thread/437393828))
- "Faces are not syncing correctly when I log into the Android app, only a few faces show in the search tab." (play, [link](https://play.google.com/store/apps/details?id=io.ente.photos&reviewId=c0a0fad8-815a-4944-9654-5dd57777ccf8))
- "It is not even functional for me anymore, other than for people search. All object recognition is completely gone." (reddit, [link](https://www.reddit.com/r/googlephotos/comments/1tbymyw/why_does_gp_search_suck_so_bad/olkax6r/))

### 3. Only 34% of failures state a photo type, 6% a photo age and 24% how they searched; the whole corpus holds 3 forgotten cues.

**Interpretation (a hypothesis to test, not a finding).** What people remember and forget, and anything specific to old photos, cannot be answered from public reviews and forums; it needs primary research such as a short survey or interviews.

**Confidence: high** (287 items, 7 sources). **Caveat.** Absence from public posts does not mean people do not remember these things, only that they do not write them down.

<!-- insights:end -->

## Read this first: what this evidence can and cannot support

- **Mentions, not prevalence.** The sample is public reviews and posts, which over-represent angry and technical users. Nothing here estimates how many people have a problem.
- **The sample leans on Google Photos.** 171 of the 287 failures (60%) are about Google Photos, 49 (17%) Apple Photos, 20 Amazon Photos, and a handful each for OneDrive, Ente, Immich and Samsung; 30 name no product. Findings about non-Google products rest on very few threads.
- **One thread can supply many items.** The 287 failures come from 229 distinct threads. Where it matters this report counts threads.
- **The classifications are model judgments, checked by a model.** The extractor agreed with my hand labels on the failure mode 75% of the time (100 items), on outcome 83% and on photo type 87%; the labels were made by Claude, not a human, and the last prompt was tuned against the same 100 labels, so these figures are optimistic. Cluster checks were also done by a single model rater.
- **Some sources are thin.** Play and App Store reviews are mostly praise or one-line complaints; YouTube supplied only 5 failures.
- **Access.** Reddit data was collected through a third-party scraping service in a way Reddit's rules do not permit, at small non-commercial scale; Google Photos Help Community threads were read by automated means that Google's general terms reportedly restrict. Both are disclosed here on purpose.

## How the evidence was produced

| Stage | Count |
|---|---|
| Raw items collected (7 sources) | 5,640 |
| Kept by a keyword filter and classified by an LLM | 1,951 |
| Classified as about finding photos | 740 |
| Extracted into structured records | 872 |
| **Real retrieval failures** (extraction says the person had trouble finding photos) | **287** |
| In a ranked problem cluster | 260 (91%) |

Failures by source: Google Photos Community 102, Reddit 65, Play 41, App Store 32, Hacker News 27, Stack Exchange 15, YouTube 5. Each post was reduced to a structured record (what was being looked for, what was remembered or forgotten, how the person searched, why it failed, outcome, severity) and every quote was checked to be word-for-word in the source post.

## 1. What kinds of old photos do users struggle to retrieve?

**Short answer: the data can barely say, and what it does show is about lost or wrong dates.** Of the 287 failures, 189 (66%) do not name a photo type and 269 (94%) do not state an age. Where a type is named: people or pets 53, screenshots 17, migrated libraries 12, early digital 8, received or forwarded 7, scanned prints 1. Among the 34 failures about old-type or age-stated photos, missing or wrong metadata is the largest identified cause (16 of 34, 47%), against 9% for all failures. (The photo-type labels are the least reliable field: only 15 of 22 known types matched on the check set, and one blurry-thumbnail complaint was tagged "early digital".)

What the old-photo cases look like:

- **Scans lose their dates.** "Even having scanned them in I've ended up with meta-data around the scan or import date, rather than actual data." — Hacker News, [link](https://news.ycombinator.com/item?id=46482782)
- **Migration flattens dates.** "If I use Google Takeout to download them and then import them, heaps of my photos lose their date taken, and just have their date set to the same day I uploaded them." — Reddit, [link](https://www.reddit.com/r/googlephotos/comments/1qpxbyu/the_wave_of_users_leaving_google_photos/o2ctjf5/)
- **A fix tool leaves a remainder.** "there are still nearly 3,000 photo which this programme can't locate the metadata (aka still remains in a wrong date format)." — YouTube, [link](https://www.youtube.com/watch?v=4LnnPMmXOjY&lc=UgxQrjIdeJoBmWCK9qF4AaABAg)
- **Old photos fall out of view.** "all my pre 2018 photos seem to have disappeared from the pictures section." — Google Community, [link](https://support.google.com/photos/thread/432725648)
- **Screenshots and non-camera images are hard to isolate.** "It is not as easy to filter and find photos that you haven’t taken with your iPhone." — App Store, [link](https://itunes.apple.com/au/review?id=1584215428&type=Purple%20Software)
- **Received photos vanish from where people expect.** "I'm looking for one specific photograph, a jpg taken on my iPhone, which I know was sent to my partner over Messages, towards the end of 2019." — Stack Exchange, [link](https://apple.stackexchange.com/questions/411055/where-does-mac-messages-store-older-attachments)

## 2. What do people remember about a photo, and what have they forgotten?

**Remembered.** Across the 287 failures the extractor found 85 remembered-cue mentions (and one forgotten cue): appearance 31, where 16, when 12, who 10, text in the photo 7, event 3, source 3, purpose 3. Read closely, many of the 31 "appearance" cues are example search words ("dog", "cat", "car"), not a memory of one specific photo, and several come from hypothetical Hacker News comments. The real ones look like this:

- **When, loosely:** "a few photos of my kids from a couple of years ago." — Reddit, [link](https://www.reddit.com/r/googlephotos/comments/1gs76kk/cant_find_the_pictures_that_were_in_a/) · "trying to find photos taken in 2012" — Google Community, [link](https://support.google.com/photos/thread/465289959) · "towards the end of 2019." — Stack Exchange, [link](https://apple.stackexchange.com/questions/411055/where-does-mac-messages-store-older-attachments)
- **Where:** "Typing "museum" suggests the many museums I've toured, but when I submit the keyword only one single painting I took a photo of shows up, none of the others." — Google Community, [link](https://support.google.com/photos/thread/455977807)
- **Who:** "In my use case, I'd like to search for my child and have it bring up pictures from both mine and my partner's photos." — Reddit, [link](https://www.reddit.com/r/immich/comments/1wco77z/release_v320_share_recognises_people/p9d01qb/)
- **What it looked like:** "Today, I'm searching for a photo of a bee on a vibrant blue flower." — Google Community, [link](https://support.google.com/photos/thread/437393828)
- **Words in the image or a label the person added:** "I labeled it "cricut" but for the past year when I search "cricut" it says no photos found." — Google Community, [link](https://support.google.com/photos/thread/443469614)

**Forgotten.** The extractor marked three cues as forgotten, all about *when*, all from Hacker News. Reading them:

- **Real and clear:** "I can't always remember when we went somewhere, but pretty often someone will ask about a photo from a trip to X place, and then location search finds it easily." — [link](https://news.ycombinator.com/item?id=46482782). This person remembers *where* and has forgotten *when*.
- **Indirect:** "rather than me having to remember what year it happened and scroll through photos until I find it." — [link](https://news.ycombinator.com/item?id=45928548). Describes the burden of recalling a year, in praise of AI search.
- **Not a real case:** "Which Christmas, hell I don't know" — [link](https://news.ycombinator.com/item?id=45681213). This is one of two hypothetical example queries in a comment about AI search.

So the evidence for "people remember what and where but forget when" is **one clear statement**. That is a lead, not a finding. Nobody in the corpus says what they have forgotten about *who*, *event* or *appearance*, and the corpus has no forgotten cues at all from reviews, forums or Reddit. People describe a symptom ("search doesn't work"), rarely the memory behind it.

## 3. How do people search when their memory is incomplete?

**Mostly the posts do not say.** How the person searched is stated in only 70 of 287 failures; 217 are "not stated". Where stated: descriptive keyword 38, time anchor (a year or month) 12, broad-then-browse 7, wording that does not match the system's labels 6, guessing a category 3, a natural-language question 1. 34 posts quote a query the person typed.

- **Descriptive keywords that fail:** "Even using a simple keyword like "dog" should pull up the multitude of photos I've taken of my dog, but it doesn't." — Google Community, [link](https://support.google.com/photos/thread/455977807)
- **Browse when search fails:** "How can I easily and quickly find all the poodles within that album and not have to page down over and over thru 500 pictures and check each one for the poodles?" — Reddit, [link](https://www.reddit.com/r/googlephotos/comments/1vcu3cs/finding_specific_photo_in_a_large_album/p2kn53g/)
- **Manual scrolling as the fallback:** "manually scroll back months or years and glance at every photo to find what I’m looking for." — Google Community, [link](https://support.google.com/photos/thread/439649217)
- **Guess a category, then use text search:** "My awful workaround was photos of all my membership barcodes labeled with a sharpie so that I can search "Gym" or "Library" or whatever to pull them up from OCR indexing." — Hacker News, [link](https://news.ycombinator.com/item?id=48021904)
- **Search by a word inside the photo:** "I SEARCHED ' A71' IN THE SEARCH AND DOESN'T SHOW RECENT PHOTOS HAS THIS TEXT IN IT." — Google Community, [link](https://support.google.com/photos/thread/444986278)

**Workarounds are rare.** Only 21 of 287 failures (7%) mention one, and they are mostly manual: scrolling, clearing the cache, exporting and re-importing, switching apps, or turning Gemini off. A few posts do report something that worked (turning Gemini off, waiting a day, a server-side fix), but 11 of the 287 failures end with the photo found, and none reports a lasting fix for the underlying problem.

## 4. Which problems matter most, and how do they compare?

Nine clusters were ranked. The score is a weighted sum of frequency (distinct threads, 35%), spread across sources (15%), severity (20%), "underserved" (share not found times share with no workaround, 20%) and recency (10%). The weights are a judgment, not a measurement. Cluster 8 leads under the default, equal and frequency-only weightings and is second when only severity and underserved count; clusters 5, 14 and 3 fill the next places. **The top is stable; the middle order is not.**

| Rank | Cluster | Items | Threads | Sources | Not found | Workaround | Last 6 months |
|---|---|---|---|---|---|---|---|
| 1 | Search returns nothing, wrong or irrelevant results | 59 | 53 | 6 | 73% | 14% | 61% |
| 2 | Update removed or rearranged browsing features (borderline check) | 39 | 32 | 7 | 49% | 8% | 51% |
| 3 | General difficulty locating media | 14 | 14 | 3 | 86% | 0% | 79% |
| 4 | Finding and ordering photos by metadata | 25 | 24 | 7 | 56% | 8% | 44% |
| 5 | Broken search and error messages | 27 | 23 | 6 | 48% | 0% | 81% |
| 6 | People and face recognition, grouping and naming problems | 40 | 29 | 4 | 30% | 10% | 95% |
| 7 | Missing old photos and screenshots | 20 | 17 | 3 | 70% | 0% | 100% |
| 8 | Broken keyword and image search | 13 | 12 | 4 | 46% | 0% | 62% |
| 9 | AI (Gemini) search replaced or worsened classic search | 23 | 15 | 4 | 35% | 9% | 87% |

Two more clusters (27 items) were too mixed to rank. The full definitions, quotes and cue tables for every cluster are in `eval/results/clusters.md`, and the Explorer app shows them interactively.

**1. Search returns nothing, wrong or irrelevant results.** The largest and most consistent cluster, seen in every source but YouTube.
- "if I search in Google photos I can find anything eg searched for Nokia phone but in Apple photos can’t find anything." — App Store, [link](https://itunes.apple.com/au/review?id=1584215428&type=Purple%20Software)
- "After uploading all my images and videos over 3 days, the Google photos search by faces doesnt work either." — Google Community, [link](https://support.google.com/photos/thread/430853685)
- "wrote beard etc. it found photos of my cats instead of me with beard journey." — Reddit, [link](https://www.reddit.com/r/iphone/comments/1h4g34s/the_search_function_is_photos_is_utterly_useless/m1ngnk0/)

**2. Updates that remove or rearrange ways of browsing.** Complaints that a redesign took away month grouping, date labels, zoom levels, albums or places. This cluster only barely passed the quality check (7 of 10 fresh items fit; two were off-topic), so treat its rank with caution.
- "You removed the grouping by month. Hard to find picture nows." — App Store, [link](https://itunes.apple.com/ca/review?id=962194608&type=Purple%20Software)
- "When viewing an individual photo from years ago, if I click off that photo then rather than retaining that time view the app goes automatically racing forward in time to resume today's date view!" — Play, [link](https://play.google.com/store/apps/details?id=com.amazon.clouddrive.photos&reviewId=4ebe787f-657f-4ce3-ace9-d451dc4e18a9)
- "Additional my mail search and photo search broke with Apple Intelligence/iOS18 integration." — Hacker News, [link](https://news.ycombinator.com/item?id=44965337)

**3. General difficulty locating media.** Short store reviews with the highest not-found rate (86%) and no workarounds. They are too vague to diagnose, which is itself a finding: people cannot say why they cannot find things.
- "it takes me almost 5 minutes to find the picture I really want" — App Store, [link](https://itunes.apple.com/au/review?id=1584215428&type=Purple%20Software)
- "I can't find some of my pictures and videos" — Google Community, [link](https://support.google.com/photos/thread/468696040)
- "cant find photo in some folder" — Play, [link](https://play.google.com/store/apps/details?id=io.ente.photos&reviewId=28c72136-6fdf-4791-92a3-a165dbfc477c)

**4. Finding and ordering photos by metadata.** The cluster closest to the old-photo question, spread across 7 sources.
- "expect about 1% of your pictures to end up with a wrong date (the date of the takeout request) and no other metadata." — App Store, [link](https://itunes.apple.com/us/review?id=1542026904&type=Purple%20Software)
- "The dates shown on the app are not always correct, for example dated Jan 23rd will be found in Feb 3rd?" — Play, [link](https://play.google.com/store/apps/details?id=app.alextran.immich&reviewId=63629071-bb5d-439a-805f-1f21c94120ee)

**How the problems differ.**
- **By source.** Google Community supplies most face, people and "old photos missing" items; store reviews supply the vague locating complaints and many of the update complaints; Reddit, Stack Exchange and YouTube supply most migration and metadata cases. Reddit appears in 8 of the 9 ranked clusters.
- **By product.** Google Photos dominates every cluster (171 of 287 failures). Apple Photos (49) shows up mostly in the update-rearrangement cluster (14) and the search-returns-nothing cluster (9). Amazon Photos and the self-hosted apps appear only in a few reviews each.
- **By recency.** Face and people problems (95% of items from the last six months), missing old photos (100%) and AI search (87%) are the most recent; metadata problems (44%) are the least recent.
- **By severity.** Almost everything is "inconvenience" (253 of 287 failures); time loss is 26, emotional loss 2, data loss 0. Data loss and emotional loss appear a little more among the items set aside as not search problems (15 of 585), but they are rare there too.

## 5. Hypotheses tested

The seven hypotheses were written down in `docs/context.md` before the analysis.

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| 1 | Old-photo retrieval failures come mostly from missing or wrong metadata, not bad search | Tentatively supported | 16 of 34 old-type or age-stated failures are metadata, against 9% overall; small and partly circular |
| 2 | People remember who and event better than when and where | Not supported | Remembered: where 16, when 12, who 10, event 3; counts tiny, no forgotten who or event cues |
| 3 | Screenshots and functional images are a distinct retrieval problem | Inconclusive | 17 items; same not-found rate as all failures (53%); few purpose cues |
| 4 | Post-LLM complaints are about loss of control more than accuracy | Not supported | 4 of 23 in the cluster (7 of 37 across all AI mentions) ask for the old search or a switch; 10 of 23 describe worse or wrong results |
| 5 | Migration is a disproportionate source of unrecoverable failures | Inconclusive | Migrated photos are 4% of failures; 67% not found (8 of 12) against 53% overall; "unrecoverable" cannot be judged from posts |
| 6 | Reddit workarounds reveal needs that store reviews only hint at | Not supported | Workaround rate: Reddit 8%, App Store 6%, Google Community 7%; Hacker News 15% on 27 items |
| 7 | Many "retrieval" complaints are really account, sync or deletion problems | Strongly supported | 585 of 872 extracted items (67%) and 455 of the 740 the classifier called retrieval (61%) were not a failure to find photos |

## 6. Opportunity areas, with how strong the evidence is

These are areas to look at, not solutions. Strength reflects how many threads and sources support the area, not how big the market is.

| Area | Strength | Why |
|---|---|---|
| **Search that finds nothing or the wrong thing, with no way forward** | Strong | Largest cluster, 6 sources, 73% not found, 14% workaround at best; most complaints are about accuracy, not control |
| **Dates and places lost in scanning and migration** | Moderate | 7 sources, mixed fixes exist (third-party tools) and still leave a remainder; old-photo evidence is thin |
| **Updates that take away ways of browsing** | Moderate, cautioned | 32 threads, 7 sources, but the cluster only barely passed its quality check |
| **People and face features that silently stop working** | Moderate | 29 threads, 95% recent, but a lower not-found rate (30%): people lose a feature more than a photo |
| **Vague "can't find my photos" with no stated cause** | Moderate, diagnostic | Highest not-found rate, nobody says why: a gap in how well the product explains itself |
| **Telling recovery, backup and account problems apart from search** | Strong | Two thirds of "can't find" complaints were something else; these users need routing, not better search |

## 7. What we still do not know, and what to do next

- **What people remember and forget about a photo they cannot find.** Public reviews and forums do not contain it. The engine's schema (remembered and forgotten cues by type) is ready for data that does: a short survey or a handful of interviews asking people to describe a photo they failed to find, what they remembered, and what they tried.
- **Anything about old photos as such.** Only 6% of failures give an age. Sources aimed at old and scanned photos (genealogy and digitizing communities) were only lightly tried and mostly reached through Reddit.
- **Non-Google products.** Findings about Apple Photos, Amazon Photos and the self-hosted apps come from a few dozen threads at best.
- **Whether any of this is common.** Counts are mentions in a sample. A survey, or the products' own search-failure data, is needed for prevalence.
- **Better checks.** The gold sets were labeled by a model. A human review of the borderline items would firm up the accuracy figures.

## Appendix: method, quality and files

**Pipeline.** Collect (Google Play, App Store, YouTube, Reddit via Apify, Google Photos Community, Stack Exchange, Hacker News) → keyword filter → LLM relevance classification (Gemini `flash-lite`; recall 96%, precision 72% on 300 labeled items, optimistic because the prompt was tuned on them) → structured extraction with a quote validator (Gemini `flash-lite`, prompt v4) → grouping by failure mode and meaning-based clustering (local MiniLM embeddings, Ward linkage) → LLM naming → human-style check (8 of 10 items must fit).

**Quality measures.** Extraction vs hand labels (100 items, model-labeled): failure mode 75%, outcome 83%, photo type 87%; run-to-run stability 89% to 96%; "is a retrieval failure" precision 75%, recall 73%. Validator: every stored quote is verbatim; 6 of about 880 items never validated. Spot-audit of 50 random extractions by the model: about 94% right on failure mode, 90% on outcome. Cluster check: 8 of 9 ranked clusters pass; cluster 5 is 7 of 10.

**Cost.** Zero. Everything ran on free tiers (Gemini, YouTube, Stack Exchange, Hacker News APIs, and about $0.80 of Apify's free monthly credit).

**Where things are.** `data/engine.db` holds all data (authors stored only as salted hashes, never names). `eval/` holds labels, results and the cluster audit. `eval/results/clusters.md` is the full cluster write-up. `app/explorer.py` is the Explorer. `docs/` holds the problem statement, context, retrieval plan, architecture and implementation plan.

**Reproduce.** From the project root: `PYTHONPATH=src python -m engine.cli report`, `cluster-report`, and `PYTHONPATH=src streamlit run app/explorer.py`.
