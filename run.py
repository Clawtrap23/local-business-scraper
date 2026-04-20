#!/usr/bin/env python3
import sys

from src.business_scraper import main as osm_main
from src.google_maps_scraper import main as google_main
from src.tradie_pipeline import main as tradie_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "google":
        sys.argv.pop(1)
        raise SystemExit(google_main())
    if len(sys.argv) > 1 and sys.argv[1] == "tradies":
        sys.argv.pop(1)
        raise SystemExit(tradie_main())
    raise SystemExit(osm_main())
