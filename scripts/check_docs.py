"""Check local link targets and Markdown headings in the maintained project guides."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GUIDES = [
    'README.md', 'website/README.md', 'docs/CODEBASE_REVIEW.md',
    'docs/topology.md', 'docs/addressing-table.md', 'docs/access-policy.md',
    'docs/centralized-services.md', 'docs/fault-tolerance.md',
]
LINK = re.compile(r'(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)')


def without_fences(text):
    return re.sub(r'^```[^\n]*\n.*?^```[^\n]*$', '', text, flags=re.M | re.S)


def anchors(path):
    text = without_fences(path.read_text(encoding='utf-8-sig'))
    result = set()
    counts = {}
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        count = counts.get(slug, 0)
        result.add(f'{slug}-{count}' if count else slug)
        counts[slug] = count + 1
    return result


def main():
    files = [ROOT / name for name in GUIDES] + sorted((ROOT / 'docs/versions').rglob('*.md'))
    errors = []
    checked = 0
    for source in files:
        text = without_fences(source.read_text(encoding='utf-8-sig'))
        for raw in LINK.findall(text):
            url = urlsplit(raw.strip('<>'))
            if url.scheme or url.netloc:
                continue
            target = (source.parent / unquote(url.path)).resolve() if url.path else source
            checked += 1
            if not target.exists():
                errors.append(f'{source.relative_to(ROOT)}: missing {raw}')
            elif url.fragment and target.suffix.lower() == '.md' and unquote(url.fragment) not in anchors(target):
                errors.append(f'{source.relative_to(ROOT)}: missing heading {raw}')
    for error in errors:
        print(error)
    print(f'Checked {checked} local links in {len(files)} guides; {len(errors)} errors.')
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
