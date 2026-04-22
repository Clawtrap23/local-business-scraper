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

### What it does
- reads suburb file
- reads tradie keyword file
- runs Google Maps queries
- deduplicates results
- applies website audit and lead scoring
- writes final CSV/XLSX

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
