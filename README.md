# local-business-scraper

A Google Maps based local business and tradies scraping pipeline for Brisbane-style suburb-by-suburb lead collection.

## What this project is for

This project is designed to collect business information for:
- plumbers
- locksmiths
- carpenters
- roofers
- solar installers
- waterproofing businesses
- electricians
- smart home installers
- security installers
- and other local service businesses / tradies

The main use case is:
- pick a target area such as **Brisbane CBD**
- search nearby suburbs one by one
- run multiple tradie/business queries
- collect business listings from **Google Maps**
- remove duplicates
- export the final result to **CSV** and **Excel**

## Important status

### Main pipeline: Google Maps
This is the **current recommended pipeline**.

Use this for real work.

### Old pipeline: OpenStreetMap / Overpass
This is still present in the repo, but it is now **legacy / mostly obsolete for the intended use case**.

Why it is no longer the preferred option:
- weaker coverage for tradies and service businesses
- misses many websites and real businesses
- better for generic map POIs than for lead generation

You can still run it, but for tradies and small-business prospecting, use the **Google Maps pipeline** instead.

## Project structure

### Main files

- `run.py`
  - main entry point
  - lets you run the project in different modes

- `src/google_maps_scraper.py`
  - single-query Google Maps scraper
  - useful for tests and one-off searches like:
    - `plumbers in Brisbane CBD`

- `src/tradie_pipeline.py`
  - the main multi-suburb pipeline
  - reads a suburb list and a keyword list
  - runs many Google Maps searches
  - deduplicates results
  - exports final spreadsheet files

- `src/business_scraper.py`
  - old OpenStreetMap-based pipeline
  - kept for reference / fallback
  - no longer the preferred workflow

### Config files

- `config/brisbane-cbd-nearby-suburbs.txt`
  - editable list of suburbs to search
  - one suburb per line
  - this is where you change the target suburb coverage in future

- `config/tradie-keywords.txt`
  - editable list of tradie / service keywords
  - one keyword per line
  - this is where you add or remove categories

### Output files

Generated files are written to `output/`, for example:
- `google-maps-results.csv`
- `google-maps-results.xlsx`
- `tradies-brisbane-cbd-nearby-suburbs.csv`
- `tradies-brisbane-cbd-nearby-suburbs.xlsx`

## Setup

This project is intended to run in the dedicated Conda environment created on this machine.

### Conda environment

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
```

If the environment does not exist yet, create/update it from:

```bash
conda env create -f environment.yml
```

or, if it already exists:

```bash
conda env update -f environment.yml --prune
```

### Install Playwright browser runtime

Run this once:

```bash
/home/profile1/miniconda3/envs/local-business-scraper/bin/python -m playwright install chromium
```

## How to run

## 1. Recommended: multi-suburb tradies pipeline

This is the main production-style workflow.

It:
- reads the suburb list from `config/brisbane-cbd-nearby-suburbs.txt`
- reads tradie keywords from `config/tradie-keywords.txt`
- runs all keyword × suburb searches in Google Maps
- merges the results
- removes duplicates
- writes CSV and Excel output

Run:

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py tradies --total-per-query 8
```

### What `--total-per-query` means
It is the maximum number of Google Maps listings to collect for each search.

For example, with:
- 30 suburbs
- 20 keywords
- `--total-per-query 8`

The pipeline may attempt up to:
- 30 × 20 × 8 listing slots

In practice, deduplication will reduce the final output.

## 2. Single Google Maps query mode

Use this when you want to test one search manually.

Example:

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py google "plumbers in Brisbane CBD" --total 12
```

This writes:
- `output/google-maps-results.csv`
- `output/google-maps-results.xlsx`

## 3. Legacy OSM mode

This mode is still available, but it is no longer the recommended path.

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py "Brisbane CBD" --radius-km 2
```

Use it only if you specifically want the old OpenStreetMap-based approach.

## Editable files you will likely change

### Suburb list
Edit:

```text
config/brisbane-cbd-nearby-suburbs.txt
```

One suburb per line.

Current included suburbs:
- Brisbane City
- Spring Hill
- Petrie Terrace
- Fortitude Valley
- New Farm
- Teneriffe
- Newstead
- Kangaroo Point
- South Brisbane
- West End
- Highgate Hill
- Milton
- Paddington
- Red Hill
- Herston
- Bowen Hills
- Woolloongabba
- East Brisbane
- Auchenflower
- Toowong
- Norman Park
- Bulimba
- Hawthorne
- Balmoral
- Ashgrove
- Kelvin Grove
- St Lucia
- Dutton Park
- Annerley
- Greenslopes

### Tradie keyword list
Edit:

```text
config/tradie-keywords.txt
```

One keyword per line.

Examples already included:
- plumbers
- locksmiths
- carpenters
- solar panel installers
- waterproofing services
- roofers
- electricians
- smart home installers
- security system installers
- stone masons
- asbestos removal
- elevator technicians

## What the output contains

Depending on the Google Maps listing, output rows may include:
- query used
- business name
- category
- address
- website
- phone number
- rating
- review count
- service notes
- opening hours
- Google Maps listing URL

The tradies pipeline now also adds a **website audit and lead scoring layer**:
- `website_status`
- `website_quality`
- `website_quality_score`
- `website_notes`
- `has_contact_form`
- `has_quote_intent`
- `has_recent_year_signal`
- `lead_score`
- `lead_priority`
- `target_reason`

## Lead scoring and website audit logic

The project now tries to classify each business into one of these website states:
- `no_website`
- `website_unreachable`
- `has_website`

Then it scores website quality with a simple practical heuristic:
- `none` = no website listed
- `weak` = website missing / unreachable / very weak signals
- `basic` = some modern signals but limited conversion features
- `modern` = stronger modern signals

### Signals checked

The current audit checks things like:
- does the business have a listed website
- can the website actually load
- does the website use HTTPS
- is there a visible contact form
- is there visible quote / booking intent
- is there a recent year signal in the site content

### Lead scoring logic

This score is intentionally simple and sales-oriented.

Businesses score higher when they are:
- high-value tradie categories
- missing a website
- have a weak/unreachable website
- have a phone number listed
- have signs of real business activity
- have no visible quote funnel or contact form

### Practical interpretation

- `high` priority:
  - strongest website / CRM opportunity
  - usually no website or weak website plus strong tradie fit

- `medium` priority:
  - may have a basic website but still a strong improvement opportunity

- `low` priority:
  - usually already has a more modern website or weaker commercial fit

This is not a perfect truth engine. It is a **sales targeting heuristic** to help sort the scraped list into more useful buckets.

## Known limitations

- Google Maps scraping is more useful than the old OSM pipeline, but it is also more brittle.
- Google can change page structure at any time.
- Some businesses may appear in multiple suburb/keyword searches, so deduplication is necessary.
- Review count extraction is still weaker than name/website/phone extraction.
- Email extraction is not yet part of the main pipeline.

## Recommended workflow

If you want the best current result:

1. edit suburb list if needed
2. edit tradie keyword list if needed
3. run:

```bash
python run.py tradies --total-per-query 8
```

4. inspect the final deduplicated CSV/XLSX in `output/`

## Enrichment layer

A separate enrichment script is now included.

Purpose:
- take an existing scraped CSV
- visit each listed website
- extract extra signals from the website itself

Run it like this:

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py enrich output/tradies-brisbane-cbd-nearby-suburbs.csv --output-csv output/enriched-results.csv --output-xlsx output/enriched-results.xlsx
```

Current enrichment fields include:
- `enriched_final_url`
- `enriched_page_title`
- `enriched_emails_found`
- `enriched_phones_found`
- `enriched_contact_hints`
- `enriched_social_links`
- `enriched_directory_mentions`
- `enriched_notes`

## Enrichment ideas from here

Your instinct is right. The best next enrichment layers are:

### 1. Visit each official website
This is the best first move.

Why:
- high confidence source
- can extract emails, forms, booking/quote intent, socials, and trust signals
- can judge whether the site looks weak or modern

### 2. For businesses with no website, search for external presence
For smaller businesses with no official site, useful fallback sources are:
- Google search results
- Instagram
- Facebook
- TripAdvisor
- Yelp
- Yellow Pages
- local trade directories like hipages / Oneflare

This can help identify businesses that:
- truly have no website
- only rely on social media
- have directory-only presence
- are still good targets for a website + CRM offer

### 3. Split the sales opportunity into two types
This is probably the smartest commercial framing:

- **Website lead**
  - no website
  - weak/outdated website

- **CRM lead**
  - website exists
  - but weak lead capture, no quote funnel, no automation, weak follow-up

That means some businesses with modern-ish websites could still be valuable CRM leads.

## Future improvements

Planned / useful next upgrades:
- improve enrichment for email discovery
- add deeper website crawling for contact/about pages
- search Google / social / directory presence for no-website businesses
- improve review count extraction
- stronger deduplication logic
- add confidence/source scoring
- optionally swap discovery over to Google Places API for more stability
