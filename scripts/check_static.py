"""Validate relative links, fragments, image metadata and CSS assets without dependencies."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids, self.urls, self.images, self.h1 = [], [], [], 0
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        self.h1 += tag == 'h1'
        if tag == 'img':
            self.images.append(attrs)
        self.urls.extend(attrs[key] for key in ('href', 'src') if attrs.get(key))
        if attrs.get('srcset'):
            self.urls.extend(part.strip().split()[0] for part in attrs['srcset'].split(','))

pages = {path: Page(path.read_text()) for path in ROOT.glob('*.html')}
errors, references = [], 0
for path, page in pages.items():
    if len(page.ids) != len(set(page.ids)):
        errors.append(f'{path.name}: duplicate IDs')
    if page.h1 != 1:
        errors.append(f'{path.name}: expected one H1, got {page.h1}')
    for image in page.images:
        if 'alt' not in image:
            errors.append(f'{path.name}: missing alt on {image.get("src")}')
    for value in page.urls:
        url = urlsplit(value)
        if url.scheme or url.netloc:
            continue
        references += 1
        target = (path.parent / unquote(url.path)).resolve() if url.path else path
        if not target.exists():
            errors.append(f'{path.name}: missing file {value}')
        elif url.fragment and target.suffix == '.html':
            target_page = pages.get(target)
            if target_page is None:
                target_page = Page(target.read_text())
            if unquote(url.fragment) not in target_page.ids:
                errors.append(f'{path.name}: missing anchor {value}')
for path in (ROOT / 'assets/css').glob('*.css'):
    for value in re.findall(r'url\([\"\']?([^\)\"\']+)', path.read_text()):
        if not urlsplit(value).scheme and not (path.parent / value).exists():
            errors.append(f'{path.name}: missing CSS asset {value}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'PASS: {len(pages)} HTML pages; {references} relative references; image alt and CSS assets.')
