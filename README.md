# local-business-scraper

A layered local-business and tradies lead-generation pipeline built around Google Maps discovery, website enrichment, and sales-oriented scoring.

This project is designed to help answer questions like:
- Which tradies operate around Brisbane CBD and nearby suburbs?
- Which of them have no website, a weak website, or a modern website?
- Which businesses are the best targets for a website offer?
- Which businesses may already have a decent site, but still be good CRM/process leads?
- Which businesses have usable contact details and social presence for outreach?

---

# 1. What this project does overall

At a high level, the pipeline works in layers:

1. **Discovery layer**
   - Find businesses using Google Maps searches.

2. **Geographic expansion layer**
   - Search suburb by suburb, not just one broad city query.

3. **Deduplication layer**
   - Merge repeated businesses found through multiple searches.

4. **Website audit layer**
   - Decide whether the business has no website, a weak/basic website, or a more modern one.

5. **Lead scoring layer**
   - Score how commercially interesting the business looks for a website/CRM offer.

6. **Website enrichment layer**
   - Visit the website, crawl important internal pages, and extract contact/social signals.

7. **Social relevance layer**
   - Estimate whether extracted social links are actually relevant to the business.

The project is therefore not just a scraper. It is becoming a **lead qualification pipeline**.

---

# 2. Important status of the project

## Main pipeline: Google Maps based
This is the **current recommended pipeline** and the one you should focus on.

Why:
- much better for tradies and service businesses than the old OSM approach
- more commercially useful business discovery
- better contact detail availability
- much better fit for website + CRM targeting

## Legacy pipeline: OpenStreetMap / Overpass
The old OSM-based pipeline is still in the repo, but it is now **legacy / mostly obsolete** for the intended use case.

It is weaker because:
- it often misses websites that actually exist
- tradie coverage is poorer
- it is better for generic POI collection than for lead generation

Use it only if you specifically want the old map-tag-based approach.

---

# 3. How the pipeline works, layer by layer

## Layer 1. Google Maps discovery

### Goal
Find real businesses by searching Google Maps the way a customer would.

### How it works
The project opens Google Maps in headless Chromium, runs searches such as:
- `plumbers in Brisbane CBD`
- `locksmiths in Spring Hill Brisbane`
- `solar panel installers in South Brisbane Brisbane`

It collects listing links, opens the listings one by one, and extracts:
- business name
- category
- address
- website
- phone
- rating
- reviews count when possible
- hours when possible
- Google Maps URL

### Main file
- `src/google_maps_scraper.py`

### Why this layer exists
This is the best current discovery source in the project for tradies and small service businesses.

---

## Layer 2. Geographic expansion through suburb lists

### Goal
Avoid relying on one overly broad query like `Brisbane`, which tends to favor bigger or more prominent businesses.

### How it works
Instead of only searching one central area, the pipeline reads a suburb list from:
- `config/brisbane-cbd-nearby-suburbs.txt`

Then it combines each suburb with each tradie keyword from:
- `config/tradie-keywords.txt`

Example combinations:
- `plumbers in Brisbane City Brisbane`
- `plumbers in Spring Hill Brisbane`
- `locksmiths in South Brisbane Brisbane`
- etc.

### Why this layer exists
This improves coverage of smaller local businesses and reduces the chance that Google only returns large, obvious players.

---

## Layer 3. Deduplication

### Goal
Remove the same business showing up multiple times across suburb and keyword searches.

### How it works
The pipeline compares businesses using combinations of:
- name
- phone
- website
- address
- category

If the same business appears multiple times, it is merged into one row in the final output.

### Main file
- `src/tradie_pipeline.py`

### Why this layer exists
Without deduplication, suburb-by-suburb searching would create a messy, repetitive spreadsheet.

---

## Layer 4. Website audit

### Goal
Decide whether the business has:
- no website
- a website that is unreachable/weak
- a basic website
- a more modern website

### How it works
For businesses with a website, the project checks signals like:
- whether the website loads
- whether it uses HTTPS
- whether there is a contact form
- whether there is quote/booking intent
- whether there is a recent year signal on the site

### Output fields
Examples:
- `website_status`
- `website_quality`
- `website_quality_score`
- `website_notes`
- `has_contact_form`
- `has_quote_intent`
- `has_recent_year_signal`

### Main file
- `src/lead_scoring.py`

### Why this layer exists
A business with no website or a weak/basic site is often a strong website-sales target.

---

## Layer 5. Lead scoring

### Goal
Turn raw scraped data into sales-priority signals.

### How it works
The project scores businesses higher when they are:
- strong tradie/service categories
- missing a website
- have a weak or unreachable site
- have a listed phone number
- show signs of being an active business
- have weak quote/contact funnel signals

### Output fields
Examples:
- `lead_score`
- `lead_priority`
- `target_reason`
- `website_lead_score`
- `website_lead_priority`
- `website_lead_reason`
- `crm_lead_score`
- `crm_lead_priority`
- `crm_lead_reason`
- `crm_maturity_score`
- `crm_maturity_level`
- `crm_detected_tools`
- `crm_detected_forms`
- `crm_detected_booking_signals`
- `crm_detected_chat_widgets`
- `crm_detected_portal_signals`
- `crm_operational_complexity`
- `best_offer_type`
- `outreach_angle`

### Interpretation
- `website_lead_*` fields tell you how strong the business is as a website/redesign lead
- `crm_lead_*` fields tell you how strong the business is as a CRM/process/lead-handling lead
- `crm_maturity_*` fields estimate how developed their current workflow stack already is
- `crm_detected_*` fields show what the scanner found on the website
- `best_offer_type` suggests whether you should lead with:
  - `website`
  - `crm`
  - `website_and_crm`

### Why this layer exists
This turns the sheet from raw data into a more commercially useful prospecting list.

---

## Layer 6. Website enrichment

### Goal
Go beyond the Google Maps listing and collect deeper signals directly from the business website.

### How it works
The enrichment script:
1. visits the homepage
2. extracts emails, phones, socials, and contact hints
3. follows deeper internal pages like:
   - contact
   - about
   - quote
   - booking
   - services
4. extracts more contact/social signals from those deeper pages

### Main file
- `src/enrich_data.py`

### Why this layer exists
The Google Maps listing is useful, but the website contains much richer commercial signals.

---

## Layer 7. Better contact enrichment

### Goal
Make contact details cleaner and more usable for outreach.

### How it works
The enrichment layer now gives priority to:
- explicit `mailto:` links for email
- explicit `tel:` links for phone
- internal contact/quote pages for better contact-page discovery

It also tries to:
- normalize multiple phone-number variants
- choose a single best phone number
- store the best contact page URL

### Output fields
Examples:
- `enriched_emails_found`
- `enriched_phones_found`
- `enriched_best_phone`
- `enriched_contact_page_urls`
- `enriched_contact_page_best_url`

### Why this layer exists
Raw website scraping can be noisy. This layer is meant to make the data more usable for actual outreach.

---

## Layer 8. Social extraction

### Goal
Capture the business’s social presence from the website.

### How it works
The enrichment layer scans the site and deeper pages for links to:
- Facebook
- Instagram
- LinkedIn
- YouTube
- TikTok

It stores both:
- high-level presence signals
- exact extracted URLs

### Output fields
Examples:
- `enriched_social_links`
- `enriched_facebook_url`
- `enriched_instagram_url`
- `enriched_linkedin_url`
- `enriched_youtube_url`
- `enriched_tiktok_url`

### Why this layer exists
Some businesses may have weak websites but strong social presence, which is commercially relevant.

---

## Layer 9. Social relevance scoring

### Goal
Estimate whether an extracted social link is actually relevant to the business.

### How it works
This layer compares:
- business name
- social URL slug / handle / path

Examples:
- a handle like `mitchellplumbinggas` is a strong match for `Mitchell Plumbing & Gas`
- an unrelated page like `MPAQAwards` is a weak match for `The Brisbane Plumbers`

### Output fields
Examples:
- `enriched_facebook_relevance_score`
- `enriched_facebook_relevance_confidence`
- `enriched_facebook_relevance_reason`
- `enriched_social_relevance_best_score`
- `enriched_social_relevance_best_confidence`
- `enriched_social_relevance_best_reason`

### Why this layer exists
Not every extracted social link is actually the business’s official profile.

---

# 4. Main files and what each one does

## Root / entry point
- `run.py`
  - main command entry point
  - routes to different modes:
    - legacy OSM mode
    - single-query Google mode
    - suburb-based tradies pipeline
    - enrichment mode

## Discovery / scraping
- `src/google_maps_scraper.py`
  - Google Maps listing discovery and extraction

- `src/business_scraper.py`
  - old OpenStreetMap pipeline, legacy

## Pipeline orchestration
- `src/tradie_pipeline.py`
  - combines suburb list + tradie keywords
  - runs searches
  - deduplicates results
  - writes tradies output files

## Website audit and scoring
- `src/lead_scoring.py`
  - website classification
  - lead scoring

## Deep enrichment
- `src/enrich_data.py`
  - website enrichment
  - deeper internal-page crawling
  - contact/social extraction
  - social URL extraction
  - contact-page discovery

- `src/social_relevance.py`
  - scores whether social URLs look relevant to the business

- `src/phone_utils.py`
  - phone normalization
  - best phone selection

## Config files
- `config/brisbane-cbd-nearby-suburbs.txt`
  - editable suburb list

- `config/tradie-keywords.txt`
  - editable tradie category list

---

# 5. What the config files do

## `config/brisbane-cbd-nearby-suburbs.txt`
One suburb per line.

Used to control where the suburb-by-suburb pipeline searches.

Change this file when you want to:
- expand to more suburbs
- narrow to tighter local areas
- use another city pattern later

## `config/tradie-keywords.txt`
One tradie/business keyword per line.

Examples:
- plumbers
- locksmiths
- carpenters
- electricians
- roofers
- waterproofing services

Change this file when you want to:
- add new categories
- remove categories
- focus on a specific niche

---

# 6. Outputs and what they mean

Outputs are written into `output/`.

Examples:
- `google-maps-results.csv`
- `google-maps-results.xlsx`
- `tradies-brisbane-cbd-nearby-suburbs.csv`
- `tradies-brisbane-cbd-nearby-suburbs.xlsx`
- `enriched-results.csv`
- `enriched-results.xlsx`
- small test outputs used during development

## Typical row content after scraping + scoring + enrichment
A row can now include:
- search query
- business name
- category
- address
- website
- phone
- rating
- maps URL
- website status / quality
- lead score / priority
- target reason
- found emails
- normalized phones
- best phone
- contact page URLs
- best contact page URL
- social URLs
- social relevance scores
- deep pages crawled

## Full field reference

Below is what each output field means.

### Discovery fields

#### `query`
The exact Google Maps search query used to find the business.
Example: `plumbers in Brisbane City Brisbane`

#### `name`
The business name extracted from Google Maps.

#### `category`
The business category shown in Google Maps.
Examples: `Plumber`, `Locksmith`, `Electrician`

#### `address`
The street address or location text extracted from Google Maps.

#### `website`
The website URL shown in Google Maps.
This is the starting website URL before deeper enrichment.

#### `phone`
The phone number shown in Google Maps.
This is separate from enriched website-extracted phones.

#### `rating`
The Google Maps rating text.
Usually something like `4.8`.

#### `reviews_count`
The reviews count text from Google Maps.
May be blank if extraction failed or Google did not show it clearly.

#### `services`
Extra services-related text extracted from the listing when available.
This can help show breadth of offering.

#### `hours`
Business hours text extracted from Google Maps when available.

#### `maps_url`
The direct Google Maps place URL for that business listing.
Useful for manual review.

### Website audit fields

#### `website_status`
The high-level website status.
Typical values:
- `no_website`
- `website_unreachable`
- `has_website`

#### `website_quality`
A simple website quality classification.
Typical values:
- `none`
- `weak`
- `basic`
- `modern`

#### `website_quality_score`
Numeric score behind the website quality classification.
Higher usually means a stronger/more complete website presence.

#### `website_notes`
Short explanation of what the audit found.
Examples:
- uses HTTPS
- has contact form
- has quote intent
- recent year signal found

#### `has_contact_form`
Whether the website appears to have a visible contact form.
Typical values:
- `yes`
- `no`
- `unknown`

#### `has_quote_intent`
Whether the website shows visible quote/booking intent.
Typical values:
- `yes`
- `no`
- `unknown`

This is based on phrases like:
- request a quote
- get a quote
- book now
- free quote

#### `has_recent_year_signal`
Whether the website appears to contain a recent year signal.
This is used as a rough proxy that the site may be more recently maintained.

### Combined lead scoring fields

#### `lead_score`
The overall combined commercial score.
Currently this is driven by the stronger of the website or CRM opportunity score.

#### `lead_priority`
Priority bucket for the overall combined lead.
Typical values:
- `high`
- `medium`
- `low`

#### `target_reason`
Combined human-readable reason explaining why the row looks commercially interesting.

### Website lead fields

#### `website_lead_score`
Numeric score for website/redesign opportunity.
Higher means the business looks more like a website sales target.

#### `website_lead_priority`
Priority bucket for website opportunity.
Typical values:
- `high`
- `medium`
- `low`

#### `website_lead_reason`
Human-readable explanation for the website score.
Examples:
- no website
- weak website
- no contact form
- no quote funnel

### CRM lead fields

#### `crm_lead_score`
Numeric score for CRM / lead-handling / process opportunity.
Higher means the business looks like a stronger CRM/process target.

#### `crm_lead_priority`
Priority bucket for CRM opportunity.
Typical values:
- `high`
- `medium`
- `low`

#### `crm_lead_reason`
Human-readable explanation for the CRM opportunity score.

#### `crm_maturity_score`
Estimated score for how mature the current visible CRM/workflow stack appears to be.
Higher means more visible tooling or workflow structure is present.

#### `crm_maturity_level`
Bucketed maturity estimate.
Typical values:
- `low`
- `medium`
- `high`

#### `crm_detected_tools`
Comma-separated list of CRM, marketing, form, booking, or chat tools detected on the site.
Examples:
- `salesforce`
- `servicem8`
- `hubspot`
- `intercom`

#### `crm_detected_forms`
Comma-separated list of form/workflow types detected.
Examples:
- `contact_form`
- `quote_form`
- `booking_form`
- `callback_request`

#### `crm_detected_booking_signals`
Booking-related wording or signals found on the website.
Examples:
- `book now`
- `online booking`
- `appointment`

#### `crm_detected_chat_widgets`
Chat-related tools or chat signals found on the site.
Examples:
- `intercom`
- `tawk.to`
- `live chat`

#### `crm_detected_portal_signals`
Portal/login-related signals found on the site.
Examples:
- `client portal`
- `customer portal`
- `account login`

#### `crm_operational_complexity`
Rough estimate of business complexity based on website clues.
Typical values:
- `low`
- `medium`
- `high`

This uses clues like:
- emergency service messaging
- many services
- service-area wording
- team/staff wording

### Offer recommendation fields

#### `best_offer_type`
Suggested first commercial angle.
Typical values:
- `website`
- `crm`
- `website_and_crm`

#### `outreach_angle`
A plain-English suggestion for how to pitch the business first.

### Enrichment fields
These fields are added when you run `enrich` mode on an existing CSV.

#### `enriched_final_url`
The final website URL after redirects when enrichment visits the site.

#### `enriched_page_title`
The homepage title detected during enrichment.

#### `enriched_emails_found`
Emails extracted from the homepage and key internal pages.
Usually includes cleaned `mailto:` results when found.

#### `enriched_phones_found`
Phone numbers extracted from the website and normalized into cleaner formats.
This is website-derived data, not the raw Google Maps phone field.

#### `enriched_best_phone`
The single best phone number chosen from the enriched website phone set.
Useful for outreach targeting.

#### `enriched_contact_hints`
Whether the site appears to contain contact-related wording.
Typical values:
- `yes`
- `no`
- `unknown`

#### `enriched_contact_page_urls`
List of likely contact/quote/booking page URLs found on the website.

#### `enriched_contact_page_best_url`
The single best contact-style page URL chosen from the discovered contact pages.

#### `enriched_social_links`
High-level social presence summary based on detected domains.
Examples may include:
- `facebook.com`
- `instagram.com`
- `linkedin.com`

#### `enriched_facebook_url`
The exact Facebook URL extracted from the site, if found.

#### `enriched_instagram_url`
The exact Instagram URL extracted from the site, if found.

#### `enriched_linkedin_url`
The exact LinkedIn URL extracted from the site, if found.

#### `enriched_youtube_url`
The exact YouTube URL extracted from the site, if found.

#### `enriched_tiktok_url`
The exact TikTok URL extracted from the site, if found.

#### `enriched_facebook_relevance_score`
Numeric estimate of how relevant the detected Facebook URL looks to the business name.

#### `enriched_facebook_relevance_confidence`
Confidence label for the Facebook relevance estimate.

#### `enriched_facebook_relevance_reason`
Short explanation for the Facebook relevance estimate.

#### `enriched_instagram_relevance_score`
Numeric estimate of how relevant the detected Instagram URL looks to the business name.

#### `enriched_instagram_relevance_confidence`
Confidence label for the Instagram relevance estimate.

#### `enriched_instagram_relevance_reason`
Short explanation for the Instagram relevance estimate.

#### `enriched_linkedin_relevance_score`
Numeric estimate of how relevant the detected LinkedIn URL looks to the business name.

#### `enriched_linkedin_relevance_confidence`
Confidence label for the LinkedIn relevance estimate.

#### `enriched_linkedin_relevance_reason`
Short explanation for the LinkedIn relevance estimate.

#### `enriched_youtube_relevance_score`
Numeric estimate of how relevant the detected YouTube URL looks to the business name.

#### `enriched_youtube_relevance_confidence`
Confidence label for the YouTube relevance estimate.

#### `enriched_youtube_relevance_reason`
Short explanation for the YouTube relevance estimate.

#### `enriched_tiktok_relevance_score`
Numeric estimate of how relevant the detected TikTok URL looks to the business name.

#### `enriched_tiktok_relevance_confidence`
Confidence label for the TikTok relevance estimate.

#### `enriched_tiktok_relevance_reason`
Short explanation for the TikTok relevance estimate.

#### `enriched_social_relevance_best_score`
Best relevance score across all detected social platforms.

#### `enriched_social_relevance_best_confidence`
Confidence label for the best social relevance result found.

#### `enriched_social_relevance_best_reason`
Short explanation for the strongest social relevance result.

#### `enriched_directory_mentions`
Directory domains mentioned on the website when detected.
Examples:
- Yellow Pages
- Yelp-style references
- Oneflare
- hipages

#### `enriched_deep_pages_checked`
Number of internal pages checked during enrichment crawling.

#### `enriched_deep_page_urls`
List of internal pages visited during deep enrichment.

#### `enriched_notes`
Short summary note about the enrichment run.

---

# 7. Setup

## Conda environment

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
```

If needed:

```bash
conda env create -f environment.yml
```

or update:

```bash
conda env update -f environment.yml --prune
```

## Install Playwright browser runtime

Run once:

```bash
/home/profile1/miniconda3/envs/local-business-scraper/bin/python -m playwright install chromium
```

---

# 8. How to run each part

## A. Main suburb-based tradies pipeline

This is the main discovery workflow.

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py tradies --total-per-query 8
```

Note:
- Google Maps collection is now hard capped at **20 results per query** even if a higher number is requested.
- The tradies pipeline now saves a checkpoint CSV after each query.
- XLSX checkpoints are written less often and always written at the end.
- The pipeline now stores run state and an audit cache so interrupted jobs can resume more efficiently.

### How the tradies pipeline works now

The current `tradies` mode behaves like this:

1. Read all suburbs from `config/brisbane-cbd-nearby-suburbs.txt`.
2. Read all tradie categories from `config/tradie-keywords.txt`.
3. Build one Google Maps query per suburb/category combination.
4. Skip queries already marked completed in the saved run-state file.
5. Scrape up to 20 Google Maps results for the current query.
6. Add raw rows into the in-progress dataset.
7. Deduplicate businesses across all collected rows.
8. Audit only businesses that are not already present in the audit cache.
9. Reuse cached website/CRM audit results for previously seen businesses.
10. Write the current checkpoint CSV after each query.
11. Write the XLSX checkpoint every few queries and again at final completion.
12. Save run state and audit cache so the job can resume later if interrupted.

### Files the tradies pipeline now creates

Main outputs:
- `output/tradies-brisbane-cbd-nearby-suburbs.csv`
- `output/tradies-brisbane-cbd-nearby-suburbs.xlsx`

Resume and cache files:
- `output/tradies-brisbane-cbd-nearby-suburbs-state.json`
- `output/tradies-brisbane-cbd-nearby-suburbs-audit-cache.json`

Run logs:
- `output/logs/<mode>-<timestamp>.json`
- `output/logs/<mode>-<timestamp>.log`
- `output/logs/<mode>-<timestamp>.error.log`

Timing metrics:
- `output/tradies-brisbane-cbd-nearby-suburbs-metrics.json`

### Resume behavior

If a run is interrupted:
- completed queries are remembered in the state file
- raw collected rows are preserved in the state file
- website/CRM audits are preserved in the audit cache

So the next run can skip already-completed queries and avoid re-auditing the same businesses.

If you want to ignore saved state and start over from scratch, run the tradies pipeline with:

```bash
python run.py tradies --fresh
```

### Run logging behavior

Each `run.py` execution now creates persistent log files in `output/logs/`.

The logger stores:
- the exact launched command
- the mode used (`tradies`, `google`, `enrich`, or legacy `osm`)
- stdout progress messages
- stderr/error output
- final success or failure status
- total run duration
- start and finish timestamps

This makes it easier to review:
- what command was launched
- what happened during the run
- what error messages appeared if something failed

Typical files per run:
- metadata JSON with command, status, timestamps, and total duration
- main `.log` file with normal progress output
- `.error.log` file with stderr and traceback output

### Tradies timing metrics

The `tradies` pipeline now also writes a dedicated metrics file:

- `output/tradies-brisbane-cbd-nearby-suburbs-metrics.json`

This file includes:
- total run duration
- how many queries were processed
- how many queries were expected
- per-query duration
- per-query batch row count
- deduped row count after each query
- audited row count after each query
- whether that query wrote an XLSX checkpoint

Per-query timing is also echoed into the normal run log output.

### CRM scoring optimization behavior

CRM detection still checks the homepage first and can inspect a few relevant internal pages such as contact, quote, booking, about, or service pages.

However, it now tries to stop early when the homepage already shows strong workflow/tool signals. That reduces unnecessary extra page fetches during scoring.

### What it does
- reads suburb file
- reads tradie keyword file
- runs Google Maps queries
- deduplicates results
- audits only businesses that have not already been audited in the current run cache
- applies website and CRM scoring
- writes checkpoint CSV after each query so progress is not lost
- writes XLSX less frequently to reduce checkpoint overhead
- stores resume state so interrupted runs can continue without redoing finished queries

---

## B. Single Google Maps query

Use this for a quick targeted test.

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py google "plumbers in Brisbane CBD" --total 12
```

---

## C. Enrichment mode

Use this after you already have a CSV and want deeper website/contact/social data.

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py enrich output/tradies-brisbane-cbd-nearby-suburbs.csv --output-csv output/enriched-results.csv --output-xlsx output/enriched-results.xlsx
```

### What it does
- visits websites from the existing CSV
- crawls deeper internal pages
- extracts better contact info
- extracts social URLs
- scores social relevance

---

## D. Legacy OSM mode

Still available, but no longer recommended for the main business use case.

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py "Brisbane CBD" --radius-km 2
```

---

# 9. Recommended workflow

If you want the best current commercial workflow, do this:

1. edit suburb list if needed
2. edit tradie keyword list if needed
3. run the main tradies pipeline
4. inspect the scored output
5. run enrichment on that output
6. inspect the enriched file for:
   - best phone
   - emails
   - contact page
   - social URLs
   - social relevance

In practice:

```bash
python run.py tradies --total-per-query 8
python run.py enrich output/tradies-brisbane-cbd-nearby-suburbs.csv --output-csv output/enriched-results.csv --output-xlsx output/enriched-results.xlsx
```

---

# 10. What the project is trying to help sell

The business logic behind the pipeline is roughly:
- identify businesses that need a website
- identify businesses that have a weak/basic website
- identify businesses that may still need CRM/process improvement even if the site is okay

That means there are at least two commercial angles:

## Website lead
Best signs:
- no website
- unreachable website
- weak/basic website
- no quote/contact funnel

## CRM lead
Best signs:
- website exists
- but weak contact capture
- weak quote/booking flow
- weak follow-up / process clues

The project now scores both of those lead types separately.

On the CRM side, the system now also scans the website for:
- embedded CRM / marketing / booking tools
- visible forms and booking signals
- chat widgets and portal hints
- operational complexity clues like emergency-service language, service-area language, and team/service breadth

---

# 11. Current limitations

This is a real working system, but not perfect.

## Known limitations
- Google Maps scraping is inherently brittle because Google can change page structure.
- Phone extraction is much improved, but still not perfect in every edge case.
- Social extraction is useful, but some extracted social links may still be weakly relevant.
- Review-count extraction is still weaker than name/website/phone extraction.
- The social relevance layer is still an early heuristic.
- No-website fallback discovery (Google/Instagram/directories) is not fully built yet.

---

# 12. What the next logical steps are

The strongest next upgrades would be:

1. **No-website fallback discovery**
   - Google/social/directory discovery for businesses with no listed website

2. **Better CRM-side scoring**
   - separate website-redesign leads from CRM/process leads

3. **Confidence scoring per field**
   - how trustworthy each email, phone, social, and website signal is

4. **Outreach-ready fields**
   - best contact channel
   - likely offer angle
   - short commercial summary

---

# 13. Quick summary

If you only remember one thing:

- **Use `tradies` mode for discovery and lead scoring**
- **Use `enrich` mode for deeper contact + social + website data**
- **Treat OSM mode as legacy**

This project is now a multi-layer prospecting pipeline, not just a basic scraper.
