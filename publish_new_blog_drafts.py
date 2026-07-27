#!/usr/bin/env python3

r"""Create blog drafts in Firestore for newer LinkedIn posts.

The script scans local `.txt` files named `YYYYMMDD-title.txt`, compares their
date prefix against the newest published blog post in Firestore, and creates a
draft for each newer local post.

Authentication uses a Firebase service account JSON file. You can pass it via
`--credentials` or the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.

Examples:
  python publish_new_blog_drafts.py --credentials C:\path\service-account.json --dry-run
  python publish_new_blog_drafts.py --credentials C:\path\service-account.json
  python publish_new_blog_drafts.py --cutoff-date 2026-05-27 --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = DEFAULT_SOURCE_DIR / ".env"
DEFAULT_PROJECT_ID = "angelo-falci"
DEFAULT_TAGS = ("post linkedin",)
FILE_PATTERN = re.compile(r"^(\d{8})-(.+)\.txt$")


@dataclass(frozen=True)
class LocalPost:
    filename: str
    file_path: Path
    title: str
    slug: str
    content: str
    excerpt: str
    display_date: datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create Firestore draft blog posts for local LinkedIn files newer "
            "than the newest published post."
        )
    )
    parser.add_argument(
        "--source-dir",
        default=os.environ.get("LINKEDIN_SOURCE_DIR", str(DEFAULT_SOURCE_DIR)),
        help="Directory containing LinkedIn .txt posts. Defaults to the script directory.",
    )
    parser.add_argument(
        "--credentials",
        help=(
            "Path to the Firebase service account JSON file. If omitted, the "
            "GOOGLE_APPLICATION_CREDENTIALS environment variable is used."
        ),
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("BLOG_FIRESTORE_PROJECT_ID", DEFAULT_PROJECT_ID),
        help="Firebase project id. Defaults to angelo-falci.",
    )
    parser.add_argument(
        "--collection",
        default=os.environ.get("BLOG_FIRESTORE_COLLECTION", "posts"),
        help="Firestore collection containing blog posts. Defaults to posts.",
    )
    parser.add_argument(
        "--locale",
        default=os.environ.get("BLOG_POST_LOCALE", "it"),
        help="Post locale to query and create. Defaults to it.",
    )
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help="Tag to add to created drafts. Repeat the flag to add multiple tags.",
    )
    parser.add_argument(
        "--cutoff-date",
        default=os.environ.get("BLOG_CUTOFF_DATE"),
        help=(
            "Override the newest published date lookup. Accepted formats: "
            "YYYY-MM-DD or YYYYMMDD. Useful for dry runs without Firebase access."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview eligible posts without creating Firestore drafts.",
    )
    return parser.parse_args()


def generate_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9\s-]", "", ascii_only)
    collapsed_spaces = re.sub(r"\s+", "-", cleaned)
    collapsed_hyphens = re.sub(r"-+", "-", collapsed_spaces)
    return collapsed_hyphens.strip("-")


def title_from_segment(segment: str) -> str:
    title = segment.replace("-", " ").strip()
    if not title:
        return ""
    return title[:1].upper() + title[1:]


def excerpt_from_content(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped if len(stripped) <= 200 else stripped[:197] + "..."
    return ""


def parse_prefix_to_datetime(prefix: str) -> datetime:
    if not re.fullmatch(r"\d{8}", prefix):
        raise ValueError(f"Invalid date prefix: {prefix}")
    parsed = datetime.strptime(prefix, "%Y%m%d")
    return parsed.replace(tzinfo=timezone.utc)


def parse_user_date(value: str) -> date:
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def load_env_file(env_path: Path) -> None:
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key:
            continue

        if value and key in {"GOOGLE_APPLICATION_CREDENTIALS", "LINKEDIN_SOURCE_DIR"}:
            candidate = Path(value)
            if not candidate.is_absolute():
                value = str((env_path.parent / candidate).resolve())

        os.environ.setdefault(key, value)


def resolve_tags(cli_tags: Sequence[str] | None) -> tuple[str, ...]:
    if cli_tags:
        return tuple(dict.fromkeys(tag.strip() for tag in cli_tags if tag.strip()))

    env_tags = os.environ.get("BLOG_POST_TAGS", "")
    if env_tags.strip():
        return tuple(dict.fromkeys(tag.strip() for tag in env_tags.split(",") if tag.strip()))

    return DEFAULT_TAGS


def collect_local_posts(source_dir: Path) -> tuple[list[LocalPost], list[str]]:
    posts: list[LocalPost] = []
    invalid_files: list[str] = []

    for entry in sorted(source_dir.iterdir(), key=lambda item: item.name):
        if not entry.is_file():
            continue
        match = FILE_PATTERN.match(entry.name)
        if not match:
            continue

        date_prefix, title_segment = match.groups()
        try:
            display_date = parse_prefix_to_datetime(date_prefix)
        except ValueError:
            invalid_files.append(entry.name)
            continue

        content = entry.read_text(encoding="utf-8").strip()
        posts.append(
            LocalPost(
                filename=entry.name,
                file_path=entry,
                title=title_from_segment(title_segment),
                slug=f"linkedin-{date_prefix}-{generate_slug(title_segment)}",
                content=content,
                excerpt=excerpt_from_content(content),
                display_date=display_date,
            )
        )

    return posts, invalid_files


def resolve_credentials_path(explicit_path: str | None) -> Path | None:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return None


def init_firestore(credentials_path: Path, project_id: str):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        from google.cloud.firestore_v1.base_query import FieldFilter
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'firebase-admin'. Install it with: pip install firebase-admin"
        ) from exc

    if not credentials_path.exists():
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    app = None
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(
            credentials.Certificate(str(credentials_path)),
            {"projectId": project_id},
        )

    return firestore.client(app=app), firestore, FieldFilter


def apply_equals_filter(query, field_filter_cls, field_name: str, value: str):
    return query.where(filter=field_filter_cls(field_name, "==", value))


def coerce_firestore_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if hasattr(value, "to_datetime"):
        return value.to_datetime().date()

    if isinstance(value, (int, float)):
        timestamp = float(value)
        if abs(timestamp) > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()

    if isinstance(value, str):
        raw = value.strip()
        for parser in (date.fromisoformat, lambda item: datetime.fromisoformat(item.replace("Z", "+00:00")).date()):
            try:
                return parser(raw)
            except ValueError:
                continue

    raise RuntimeError(
        f"Unexpected displayDate type returned by Firestore: {type(value).__name__}"
    )


def get_latest_published_date(db, firestore_module, field_filter_cls, collection_name: str, locale: str) -> date | None:
    query = apply_equals_filter(db.collection(collection_name), field_filter_cls, "status", "published")
    query = apply_equals_filter(query, field_filter_cls, "locale", locale)
    query = query.order_by("displayDate", direction=firestore_module.Query.DESCENDING).limit(1)
    docs = list(query.stream())
    if not docs:
        return None

    data = docs[0].to_dict() or {}
    display_date = data.get("displayDate")
    if display_date is None:
        return None

    return coerce_firestore_date(display_date)


def slug_exists(db, field_filter_cls, collection_name: str, slug: str) -> bool:
    query = apply_equals_filter(db.collection(collection_name), field_filter_cls, "slug", slug).limit(1)
    docs = list(query.stream())
    return bool(docs)


def create_draft(db, firestore_module, collection_name: str, post: LocalPost, locale: str, tags: Sequence[str]) -> None:
    db.collection(collection_name).add(
        {
            "title": post.title,
            "slug": post.slug,
            "content": post.content,
            "excerpt": post.excerpt,
            "coverImage": "",
            "tags": list(tags),
            "status": "draft",
            "locale": locale,
            "displayDate": post.display_date,
            "publishedAt": None,
            "createdAt": firestore_module.SERVER_TIMESTAMP,
            "updatedAt": firestore_module.SERVER_TIMESTAMP,
        }
    )


def format_post_line(post: LocalPost) -> str:
    return f"{post.filename} -> {post.slug} ({post.display_date.date().isoformat()})"


def filter_newer_posts(posts: Iterable[LocalPost], cutoff: date | None) -> tuple[list[LocalPost], list[LocalPost]]:
    newer: list[LocalPost] = []
    older_or_equal: list[LocalPost] = []
    for post in posts:
        if cutoff is None or post.display_date.date() > cutoff:
            newer.append(post)
        else:
            older_or_equal.append(post)
    return newer, older_or_equal


def main() -> int:
    load_env_file(DEFAULT_ENV_FILE)
    args = parse_args()
    source_dir = Path(args.source_dir).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Source directory not found: {source_dir}", file=sys.stderr)
        return 1

    posts, invalid_files = collect_local_posts(source_dir)
    if not posts and not invalid_files:
        print("No LinkedIn post files found.")
        return 0

    firestore_db = None
    firestore_module = None
    field_filter_cls = None
    cutoff_date: date | None

    if args.cutoff_date:
        cutoff_date = parse_user_date(args.cutoff_date)
    else:
        credentials_path = resolve_credentials_path(args.credentials)
        if credentials_path is None:
            print(
                "Credentials required unless --cutoff-date is provided. Use --credentials or set GOOGLE_APPLICATION_CREDENTIALS.",
                file=sys.stderr,
            )
            return 1
        firestore_db, firestore_module, field_filter_cls = init_firestore(credentials_path, args.project_id)
        cutoff_date = get_latest_published_date(
            firestore_db,
            firestore_module,
            field_filter_cls,
            args.collection,
            args.locale,
        )

    candidates, skipped_by_cutoff = filter_newer_posts(posts, cutoff_date)
    tags = resolve_tags(args.tags)

    print(f"Source directory: {source_dir}")
    print(f"Parsed posts: {len(posts)}")
    if invalid_files:
        print(f"Skipped invalid date files: {len(invalid_files)}")
        for name in invalid_files:
            print(f"  INVALID {name}")

    if cutoff_date is None:
        print("Latest published post: none found")
    else:
        print(f"Latest published post date: {cutoff_date.isoformat()}")
    print(f"Eligible newer posts: {len(candidates)}")
    print(f"Skipped by cutoff: {len(skipped_by_cutoff)}")

    if args.dry_run:
        print("\nDRY RUN: no Firestore writes will be performed.")
        for post in candidates:
            print(f"  WOULD CREATE {format_post_line(post)}")
        return 0

    if firestore_db is None or firestore_module is None or field_filter_cls is None:
        credentials_path = resolve_credentials_path(args.credentials)
        if credentials_path is None:
            print("Credentials are required for Firestore writes.", file=sys.stderr)
            return 1
        firestore_db, firestore_module, field_filter_cls = init_firestore(credentials_path, args.project_id)

    created = 0
    duplicate_count = 0
    error_count = 0

    for post in candidates:
        try:
            if slug_exists(firestore_db, field_filter_cls, args.collection, post.slug):
                print(f"  SKIP DUPLICATE {format_post_line(post)}")
                duplicate_count += 1
                continue

            create_draft(
                firestore_db,
                firestore_module,
                args.collection,
                post,
                args.locale,
                tags,
            )
            print(f"  CREATED {format_post_line(post)}")
            created += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR {post.filename}: {exc}", file=sys.stderr)
            error_count += 1

    print("\nDone.")
    print(f"Created: {created}")
    print(f"Duplicates skipped: {duplicate_count}")
    print(f"Cutoff skipped: {len(skipped_by_cutoff)}")
    print(f"Invalid skipped: {len(invalid_files)}")
    print(f"Errors: {error_count}")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())