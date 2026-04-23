#!/usr/bin/env python3
import sys

from src.business_scraper import main as osm_main
from src.enrich_data import main as enrich_main
from src.google_maps_scraper import main as google_main
from src.run_logging import RunLogger
from src.tradie_pipeline import main as tradie_main


def detect_mode(argv: list[str]) -> tuple[str, callable]:
    if len(argv) > 1 and argv[1] == "google":
        argv.pop(1)
        return "google", google_main
    if len(argv) > 1 and argv[1] == "tradies":
        argv.pop(1)
        return "tradies", tradie_main
    if len(argv) > 1 and argv[1] == "enrich":
        argv.pop(1)
        return "enrich", enrich_main
    return "osm", osm_main


if __name__ == "__main__":
    original_argv = sys.argv[:]
    mode, entrypoint = detect_mode(sys.argv)
    logger = RunLogger(mode=mode, argv=original_argv)
    raise SystemExit(logger.run(entrypoint))
