# local-business-scraper

Collect local business data inside a radius around a location and export it to CSV and Excel.

## What it does

This first version uses:
- Nominatim for geocoding a place like `Brisbane CBD`
- OpenStreetMap Overpass for nearby business/place data

It exports one row per business with:
- business name
- category/type
- address/location
- phone number
- website URL
- email address
- business size (rough heuristic)
- whether a website exists
- rough website quality heuristic
- coordinates and distance from the search center

## Setup

Recommended:

```bash
python3 -m pip install --user -r requirements.txt
```

If your machine does not have `pip` yet:

```bash
sudo apt update
sudo apt install -y python3-pip
python3 -m pip install --user -r requirements.txt
```

## Usage

```bash
python src/business_scraper.py "Brisbane CBD" --radius-km 2
```

Outputs go to `output/`:
- `brisbane-cbd.csv`
- `brisbane-cbd.xlsx`

## Notes

- This does **not** scrape Google Maps.
- Coverage depends on OpenStreetMap data quality in the target area.
- Email addresses and business size are often missing in map data, so those fields are best-effort.
- Website quality is a simple heuristic for now:
  - no website => `No website listed`
  - `https` => `Likely modern`
  - otherwise => `Possibly older/basic`

## Next improvements

Good next steps if you want a stronger lead-gen dataset:
- crawl each website homepage/contact page to extract emails more reliably
- add business opening hours
- add more categories
- enrich with Google Places or another paid/local-business API if you want broader coverage
- improve website quality scoring with live page inspection
