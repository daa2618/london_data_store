"""Command-line interface for the London Data Store client."""

import argparse
import sys

from .api import LondonDataStore


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="london-data-store",
        description="Query the London Data Store catalogue",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # slugs
    subparsers.add_parser("slugs", help="List all dataset slugs")

    # search
    search_parser = subparsers.add_parser("search", help="Fuzzy-search dataset slugs")
    search_parser.add_argument("term", help="Search term")

    # formats
    subparsers.add_parser("formats", help="List all available data formats")

    # urls
    urls_parser = subparsers.add_parser("urls", help="Get download URLs for a slug")
    urls_parser.add_argument("slug", help="Dataset slug")

    # keywords
    kw_parser = subparsers.add_parser("keywords", help="Search datasets by keyword/tag")
    kw_parser.add_argument("keyword", help="Keyword to search tags")

    args = parser.parse_args(argv)

    try:
        with LondonDataStore() as lds:
            if args.command == "slugs":
                for slug in lds.get_all_slugs():
                    print(slug)

            elif args.command == "search":
                results = lds.filter_slugs_for_string(args.term)
                if results:
                    for slug in results:
                        print(slug)
                else:
                    print(f"No slugs matching '{args.term}'")
                    return 1

            elif args.command == "formats":
                for fmt in sorted(lds.get_all_d_types()):
                    print(fmt)

            elif args.command == "urls":
                urls = lds.get_download_url_for_slug(args.slug)
                if urls:
                    for url in urls:
                        print(url)
                else:
                    print(f"No URLs found for slug '{args.slug}'")
                    return 1

            elif args.command == "keywords":
                results = lds.filter_slugs_for_keyword(args.keyword)
                if results:
                    for slug in results:
                        print(slug)
                else:
                    print(f"No datasets matching keyword '{args.keyword}'")
                    return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
