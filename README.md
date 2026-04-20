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

## Setup with Conda

Miniconda is installed at:

```bash
/home/profile1/miniconda3
```

Create or use the dedicated environment:

```bash
/home/profile1/miniconda3/bin/conda activate local-business-scraper
```

If `conda activate` is not initialized in your shell yet, use either:

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
```

or run the script directly with the env Python:

```bash
/home/profile1/miniconda3/envs/local-business-scraper/bin/python run.py "Brisbane CBD" --radius-km 2
```

## Usage

```bash
source /home/profile1/miniconda3/etc/profile.d/conda.sh
conda activate local-business-scraper
python run.py "Brisbane CBD" --radius-km 2
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

## Environment contents

The `local-business-scraper` conda environment includes:
- Python 3.11
- requests
- openpyxl

## Next improvements

Good next steps if you want a stronger lead-gen dataset:
- crawl each website homepage/contact page to extract emails more reliably
- add business opening hours
- add more categories
- enrich with Google Places or another paid/local-business API if you want broader coverage
- improve website quality scoring with live page inspection
