import csv
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Product


HEADER_RE = re.compile(r"^(?P<name>.+?)\s*\[(?P<code>\d+)\]\s*$")


def norm_name(s: str) -> str:
    """
    Normalise names for matching:
    - lowercase
    - remove apostrophes/punctuation
    - collapse whitespace
    """
    s = (s or "").strip().lower()
    s = s.replace("’", "'")
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def similarity(a: str, b: str) -> float:
    """
    0..1 similarity using stdlib difflib.
    """
    return SequenceMatcher(None, a, b).ratio()


@dataclass
class LoreEntry:
    name: str
    code: str
    description: str


def parse_lore_txt(text: str) -> List[LoreEntry]:
    """
    Parse blocks of:
      Name [1234]
      description...

    Blocks separated by blank lines, but we also detect new headers.
    """
    lines = text.splitlines()
    entries: List[LoreEntry] = []

    current_name: Optional[str] = None
    current_code: Optional[str] = None
    buf: List[str] = []

    def flush():
        nonlocal current_name, current_code, buf
        if current_name and current_code:
            desc = "\n".join([ln.rstrip() for ln in buf]).strip()
            entries.append(LoreEntry(name=current_name.strip(), code=current_code.strip(), description=desc))
        current_name, current_code, buf = None, None, []

    for raw in lines:
        line = raw.rstrip()

        m = HEADER_RE.match(line.strip())
        if m:
            # new entry begins
            flush()
            current_name = m.group("name")
            current_code = m.group("code")
            continue

        # accumulate description lines (including blank lines; we’ll trim on flush)
        if current_name:
            buf.append(line)

    flush()
    return entries


class Command(BaseCommand):
    help = "Import lore from data/lore.txt and attach to products by fuzzy matching on Product.name."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="data/lore.txt",
            help="Path to lore text file (default: data/lore.txt).",
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=0.87,
            help="Similarity threshold 0..1 (default: 0.87). Increase to be stricter.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write to DB; just print summary and write report.",
        )
        parser.add_argument(
            "--report",
            default="reports/lore_match_report.csv",
            help="CSV report output path (default: reports/lore_match_report.csv).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of lore entries processed (testing).",
        )

    def handle(self, *args, **opts):
        path = Path(opts["path"])
        threshold = float(opts["threshold"])
        dry_run = bool(opts["dry_run"])
        report_path = Path(opts["report"])
        limit = int(opts["limit"])

        if not path.exists():
            raise CommandError(f"Lore file not found: {path}")

        text = path.read_text(encoding="utf-8")
        entries = parse_lore_txt(text)
        if not entries:
            raise CommandError("No lore entries parsed. Check file format.")

        if limit:
            entries = entries[:limit]

        products = list(Product.objects.all())
        if not products:
            raise CommandError("No products found in DB. Build your catalogue first.")

        # Precompute normalised product names
        prod_norm = [(p, norm_name(p.name)) for p in products]

        updated = 0
        unmatched = 0
        low_confidence = 0

        report_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []

        updated_product_ids = set()

        def best_match(entry_name: str) -> Tuple[Optional[Product], float]:
            target = norm_name(entry_name)
            best_p = None
            best_s = 0.0
            for p, pn in prod_norm:
                s = similarity(target, pn)
                if s > best_s:
                    best_s = s
                    best_p = p
            return best_p, best_s

        # Write changes in one transaction if not dry-run
        ctx = transaction.atomic() if not dry_run else nullcontext()

        with ctx:
            for e in entries:
                p, score = best_match(e.name)

                # Hard floor: refuse to match completely unrelated entries
                # Hard floor: completely unrelated → UNMATCHED
                if score < 0.75:
                    unmatched += 1
                    rows.append([e.code, e.name, "", "", f"{score:.3f}", "UNMATCHED"])
                    continue

                if not p:
                    unmatched += 1
                    rows.append([e.code, e.name, "", "", f"{score:.3f}", "UNMATCHED"])
                    continue

                # Below confidence threshold → LOW_CONFIDENCE
                if score < threshold:
                    low_confidence += 1
                    rows.append([e.code, e.name, p.sku, p.name, f"{score:.3f}", "LOW_CONFIDENCE"])
                    continue

                # 🔒 Prevent overwriting the same product multiple times
                if p.id in updated_product_ids:
                    rows.append([e.code, e.name, p.sku, p.name, f"{score:.3f}", "DUPLICATE_SKIPPED"])
                    continue

                # Prepare descriptions
                short = e.description.split("\n", 1)[0].strip()
                if len(short) > 200:
                    short = short[:197] + "..."

                # Update product
                if not dry_run:
                    p.short_description = short
                    p.description = e.description.strip()
                    p.save(update_fields=["short_description", "description"])

                updated_product_ids.add(p.id)
                updated += 1
                rows.append([e.code, e.name, p.sku, p.name, f"{score:.3f}", "UPDATED"])


        # Write report CSV
        with report_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["lore_code", "lore_name", "matched_sku", "matched_product_name", "score", "action"])
            w.writerows(rows)

        self.stdout.write(self.style.SUCCESS("Lore import complete."))
        self.stdout.write(f"Entries processed: {len(entries)}")
        self.stdout.write(f"UPDATED: {updated}")
        self.stdout.write(f"LOW_CONFIDENCE (<{threshold}): {low_confidence}")
        self.stdout.write(f"UNMATCHED: {unmatched}")
        self.stdout.write(f"Report written: {report_path}")


# Python 3.13 doesn't include contextlib.nullcontext? It does, but keep safe:
try:
    from contextlib import nullcontext  # type: ignore
except ImportError:  # pragma: no cover
    class nullcontext:  # minimal fallback
        def __enter__(self): return None
        def __exit__(self, *exc): return False
