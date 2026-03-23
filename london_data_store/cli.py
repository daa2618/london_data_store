"""Command-line interface for the London Data Store client."""

import argparse
import json
import sys

from .api import LondonDataStore


def _format_table(rows: list[list[str]], headers: list[str]) -> str:
    """Format rows as an aligned text table."""
    all_rows = [headers, *rows]
    widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]
    lines = []
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True))
    lines.append(header_line)
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(str(col).ljust(w) for col, w in zip(row, widths, strict=True)))
    return "\n".join(lines)


def _output(data, args, *, default_format="plain"):
    """Output data in the requested format."""
    fmt = getattr(args, "output_format", None) or default_format

    if getattr(args, "json_output", False):
        print(json.dumps(data, indent=2, default=str))
    elif fmt == "plain":
        if isinstance(data, list):
            limit = getattr(args, "limit", None)
            items = data[:limit] if limit else data
            for item in items:
                if isinstance(item, dict):
                    for k, v in item.items():
                        print(f"{k}: {v}")
                    print()
                else:
                    print(item)
        elif isinstance(data, dict):
            for k, v in data.items():
                print(f"{k}: {v}")
    elif fmt == "table" and isinstance(data, list) and data and isinstance(data[0], dict):
        limit = getattr(args, "limit", None)
        items = data[:limit] if limit else data
        headers = list(items[0].keys())
        rows = [[str(item.get(h, "")) for h in headers] for item in items]
        print(_format_table(rows, headers))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="london-data-store",
        description="Query the London Data Store catalogue",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    parser.add_argument(
        "--format", choices=["table", "plain"], default="plain", dest="output_format", help="Output format"
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of results")
    parser.add_argument("--no-cache", action="store_true", help="Disable disk cache")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # slugs
    subparsers.add_parser("slugs", help="List all dataset slugs")

    # titles
    subparsers.add_parser("titles", help="List all dataset titles")

    # search
    search_parser = subparsers.add_parser("search", help="Fuzzy-search dataset slugs")
    search_parser.add_argument("term", help="Search term")
    search_parser.add_argument("--scored", action="store_true", help="Show similarity scores")

    # formats
    subparsers.add_parser("formats", help="List all available data formats")

    # urls
    urls_parser = subparsers.add_parser("urls", help="Get download URLs for a slug")
    urls_parser.add_argument("slug", help="Dataset slug")

    # keywords
    kw_parser = subparsers.add_parser("keywords", help="Search datasets by keyword/tag")
    kw_parser.add_argument("keyword", help="Keyword to search tags")

    # info (v2)
    info_parser = subparsers.add_parser("info", help="Show full metadata for a dataset")
    info_parser.add_argument("slug", help="Dataset slug")

    # topics (v2)
    topics_parser = subparsers.add_parser("topics", help="List all topic categories")
    topics_parser.add_argument("--filter", dest="topic_filter", help="Filter datasets by topic")

    # download (v2)
    dl_parser = subparsers.add_parser("download", help="Download a dataset file")
    dl_parser.add_argument("slug", help="Dataset slug")
    dl_parser.add_argument("--format", dest="dl_format", help="File format (e.g., csv, geojson)")
    dl_parser.add_argument("--dest", default=".", help="Destination directory or file path")
    dl_parser.add_argument("--progress", action="store_true", help="Show download progress")

    args = parser.parse_args(argv)

    try:
        with LondonDataStore(cache=not args.no_cache) as lds:
            if args.command == "slugs":
                slugs = lds.get_all_slugs()
                limit = args.limit
                if limit:
                    slugs = slugs[:limit]
                if args.json_output:
                    _output(slugs, args)
                else:
                    for slug in slugs:
                        print(slug)
            
            elif args.command == "titles":
                titles = lds.get_all_titles()
                limit = args.limit
                if limit:
                    titles = titles[:limit]
                
                if args.json_output:
                    _output(titles, args)
                else:
                    for title in titles:
                        print(titles)

            elif args.command == "search":
                if args.scored:
                    results = lds.search(args.term, limit=args.limit or 20)
                    if args.json_output:
                        _output([{"title": s, "score": round(sc, 4)} for s, sc in results], args)
                    else:
                        for title, score in results:
                            print(f"{score:.4f}  {title}")
                else:
                    scored = lds.search(args.term, limit=args.limit or 20)
                    results = [s for s, _ in scored]
                    if results:
                        if args.json_output:
                            _output(results, args)
                        else:
                            for slug in results:
                                print(slug)
                    else:
                        print(f"No slugs matching '{args.term}'")
                        return 1

            elif args.command == "formats":
                formats = sorted(lds.get_all_d_types())
                if args.json_output:
                    _output(formats, args)
                else:
                    for fmt in formats:
                        print(fmt)

            elif args.command == "urls":
                urls = lds.get_download_url_for_slug(args.slug)
                if urls:
                    if args.json_output:
                        _output(urls, args)
                    else:
                        for url in urls:
                            print(url)
                else:
                    print(f"No URLs found for slug '{args.slug}'")
                    return 1

            elif args.command == "keywords":
                results = lds.filter_titles_for_keyword(args.keyword)
                if results:
                    if args.json_output:
                        _output(results, args)
                    else:
                        for title in results:
                            print(title)
                else:
                    print(f"No datasets matching keyword '{args.keyword}'")
                    return 1

            elif args.command == "info":
                ds = lds.get_dataset(args.slug)
                info = ds.to_dict()
                if args.json_output:
                    _output(info, args)
                else:
                    for key, value in info.items():
                        if key == "resources":
                            print(f"\n{key}:")
                            for res in value:
                                rk = res.get("key", "unknown")
                                rf = res.get("format", "")
                                ru = res.get("url", "")
                                print(f"  - {rk}: {rf} ({ru})")
                        elif value is not None and value != [] and value != "":
                            print(f"{key}: {value}")

            elif args.command == "topics":
                if args.topic_filter:
                    slugs = lds.filter_by_topic(args.topic_filter)
                    if args.json_output:
                        _output(slugs, args)
                    else:
                        for slug in slugs:
                            print(slug)
                else:
                    topics = lds.get_all_topics()
                    if args.json_output:
                        _output(topics, args)
                    else:
                        for topic in topics:
                            print(topic)

            elif args.command == "download":

                def _progress(downloaded, total):
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  {downloaded}/{total} bytes ({pct:.1f}%)", end="", flush=True)
                    else:
                        print(f"\r  {downloaded} bytes", end="", flush=True)

                callback = _progress if args.progress else None
                path = lds.download_file(
                    args.slug,
                    format=args.dl_format,
                    destination=args.dest,
                    progress_callback=callback,
                )
                if args.progress:
                    print()  # newline after progress
                print(f"Downloaded: {path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
