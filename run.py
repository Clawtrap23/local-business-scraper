#!/usr/bin/env python3
import sys

from src.business_scraper import main as osm_main
from src.google_maps_scraper import main as google_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "google":
        sys.argv.pop(1)
        raise SystemExit(google_main())
    raise SystemExit(osm_main())
