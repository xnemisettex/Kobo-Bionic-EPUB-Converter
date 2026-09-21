#!/usr/bin/env python3
"""Batch Kobo Bionic converter based on the successful Riyria test."""
import html
import argparse
import shutil
import traceback
import math
import os
import posixpath
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import etree

DEFAULT_SOURCE_FOLDER = None
MIN_FREE_BYTES = 1024 ** 3
BOLD_PERCENT = 40

# Lexical scanner: retain the exact original bytes of all markup and attributes.
TAG = re.compile(r'<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<!DOCTYPE[^\[>]*(?:\[.*?\])?\s*>|<![^>]*>|<(?:[^>"\']|"[^"]*"|\'[^\']*\')*>', re.S | re.I)
TAG_NAME = re.compile(r'<\s*(/?)\s*([A-Za-z_][\w:.-]*)')
WORD = re.compile(r'[^\W_]+(?:[\'\u2019][^\W_]+)*', re.UNICODE)
ENTITY = re.compile(r'&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);')
SKIP = {'head', 'script', 'style', 'svg', 'math', 'code', 'pre', 'textarea', 'a', 'b', 'strong', 'ruby', 'rt', 'rp', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}


def bionic_text(raw):
    # Entity references remain spelled exactly as in the source.
    chars, originals, last = [], [], 0
    for match in ENTITY.finditer(raw):
        segment = raw[last:match.start()]
        chars.extend(segment)
        originals.extend(segment)
        entity = match.group()
        decoded = html.unescape(entity)
        chars.append(decoded if len(decoded) == 1 else '\0')
        originals.append(entity)
        last = match.end()
    chars.extend(raw[last:])
    originals.extend(raw[last:])
    plain = ''.join(chars)
    output, cursor, count = [], 0, 0
    for match in WORD.finditer(plain):
        start, end = match.span()
        output.append(''.join(originals[cursor:start]))
        word = match.group()
        if len(word) > 1 and any(ch.isalpha() for ch in word):
            n = min(len(word), max(1, math.ceil(len(word) * BOLD_PERCENT / 100)))
            if n > 1 and word[n - 1] in "'\u2019":
                n -= 1
            output.append('<b>' + ''.join(originals[start:start+n]) + '</b>' + ''.join(originals[start+n:end]))
            count += 1
        else:
            output.append(''.join(originals[start:end]))
        cursor = end
    output.append(''.join(originals[cursor:]))
    return ''.join(output), count


def transform_markup(source):
    output, cursor, stack, count = [], 0, [], 0
    for match in TAG.finditer(source):
        segment = source[cursor:match.start()]
        if segment:
            if 'body' in stack and not any(name in SKIP for name in stack):
                segment, added = bionic_text(segment)
                count += added
            output.append(segment)
        tag = match.group()
        output.append(tag)
        tag_match = TAG_NAME.match(tag)
        if tag_match and not tag.startswith(('<!--', '<!', '<?')):
            closing, name = tag_match.groups()
            name = name.rsplit(':', 1)[-1].lower()
            if closing:
                if not stack or stack[-1] != name:
                    raise ValueError(f'Unexpected closing tag: {tag[:100]}')
                stack.pop()
            elif not tag.rstrip().endswith('/>'):
                stack.append(name)
        cursor = match.end()
    output.append(source[cursor:])
    if stack:
        raise ValueError('Unclosed markup elements: ' + ', '.join(stack[-5:]))
    return ''.join(output), count


def xml_root(data):
    return etree.fromstring(data, parser=etree.XMLParser(resolve_entities=False, no_network=True, recover=False))


def structural_signature(data):
    root = xml_root(data)
    result = []
    def visit(element):
        if not isinstance(element.tag, str):
            result.append(('comment-or-PI', etree.tostring(element)))
            return
        name = etree.QName(element).localname
        if name == 'b' and not element.attrib:
            # Only new <b> tags should be present; the source is checked separately.
            for child in element:
                visit(child)
            return
        result.append((element.tag, tuple(sorted(element.attrib.items()))))
        for child in element:
            visit(child)
    visit(root)
    links = [(x.get('href'), x.get('id'), ''.join(x.itertext())) for x in root.iter() if isinstance(x.tag, str) and etree.QName(x).localname == 'a']
    return result, ''.join(root.itertext()), links


def verify_chapter(before, after):
    original_root = xml_root(before)
    changed_root = xml_root(after)
    # Recreate the expected transformation from the untouched original. Comparing
    # the complete bytes keeps pre-existing <b> tags, attributes, links and markup
    # intact; stripping every <b> tag incorrectly rejected many valid books.
    expected, _ = transform_markup(before.decode('utf-8-sig'))
    if after != expected.encode('utf-8'):
        raise ValueError('Converted chapter differs from the expected text-only transformation')
    if ''.join(original_root.itertext()) != ''.join(changed_root.itertext()):
        raise ValueError('Visible chapter text changed')
    def links(root):
        return [(x.get('href'), x.get('id'), ''.join(x.itertext())) for x in root.iter() if isinstance(x.tag, str) and etree.QName(x).localname == 'a']
    if links(original_root) != links(changed_root):
        raise ValueError('Hyperlinks changed')


def package_info(z):
    container = xml_root(z.read('META-INF/container.xml'))
    rootfiles = container.xpath('//*[local-name()="rootfile"]')
    if not rootfiles:
        raise ValueError('Missing EPUB package reference')
    opf_path = rootfiles[0].get('full-path')
    opf = xml_root(z.read(opf_path))
    base = posixpath.dirname(opf_path)
    manifest = {}
    for item in opf.xpath('//*[local-name()="manifest"]/*[local-name()="item"]'):
        href = item.get('href')
        if href:
            path = posixpath.normpath(posixpath.join(base, unquote(urlsplit(href).path)))
            manifest[item.get('id')] = (path, item.get('media-type'), set(item.get('properties', '').split()))
    spine = [x.get('idref') for x in opf.xpath('//*[local-name()="spine"]/*[local-name()="itemref"]')]
    if not spine or any(item not in manifest for item in spine):
        raise ValueError('Invalid or empty chapter spine')
    chapters = []
    for item_id in spine:
        path, media_type, properties = manifest[item_id]
        if media_type in ('application/xhtml+xml', 'text/html') and 'nav' not in properties:
            if path not in z.namelist():
                raise ValueError('Missing chapter: ' + path)
            chapters.append(path)
    if not chapters:
        raise ValueError('No chapters identified from spine')
    return opf_path, opf, manifest, spine, list(dict.fromkeys(chapters))


def convert(source, destination):
    if destination.exists():
        raise FileExistsError('Existing Bionic copy: ' + str(destination))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='kobo_bionic_', suffix='.epub', delete=False) as f:
            temporary = Path(f.name)
        with zipfile.ZipFile(source) as zin:
            if zin.testzip() is not None:
                raise ValueError('Original EPUB ZIP is corrupt')
            original_names = zin.namelist()
            if original_names[0] != 'mimetype' or zin.getinfo('mimetype').compress_type != zipfile.ZIP_STORED:
                raise ValueError('Original EPUB mimetype layout is nonstandard')
            opf_path, opf, manifest, spine, chapters = package_info(zin)
            title_nodes = opf.xpath('//*[local-name()="metadata"]/*[local-name()="title"]')
            if not title_nodes:
                raise ValueError('Missing internal title')
            original_opf = zin.read(opf_path)
            # Preserve all original OPF markup except the exact title text.
            opf_text = original_opf.decode('utf-8-sig')
            title_pattern = re.compile(r'(<(?:[\w.-]+:)?title\b[^>]*>)([^<]*)(</(?:[\w.-]+:)?title>)', re.I)
            title_match = title_pattern.search(opf_text)
            if not title_match or title_match.group(2) != title_nodes[0].text:
                raise ValueError('Cannot safely update internal title without changing OPF structure')
            new_opf_text = opf_text[:title_match.start(2)] + title_match.group(2) + ' (Bionic Medium)' + opf_text[title_match.end(2):]
            new_opf = new_opf_text.encode('utf-8')
            if package_title_structure(opf) != package_title_structure(xml_root(new_opf)):
                raise ValueError('OPF structure changed unexpectedly')
            replacements = {opf_path: new_opf}
            total = 0
            for name in chapters:
                raw = zin.read(name)
                # UTF-8 is required for this particular test book. Fail closed on other encodings.
                chapter = raw.decode('utf-8-sig')
                updated, count = transform_markup(chapter)
                if count:
                    changed = updated.encode('utf-8')
                    verify_chapter(raw, changed)
                    replacements[name] = changed
                    total += count
            if not total:
                raise ValueError('No words were bolded')
            with zipfile.ZipFile(temporary, 'w', allowZip64=True) as zout:
                zout.comment = zin.comment
                for member in zin.infolist():
                    zout.writestr(member, replacements.get(member.filename, zin.read(member)))
        with zipfile.ZipFile(source) as zin, zipfile.ZipFile(temporary) as zout:
            if zout.testzip() is not None or zin.namelist() != zout.namelist():
                raise ValueError('Output ZIP or file order changed')
            _, _, orig_manifest, orig_spine, orig_chapters = package_info(zin)
            _, _, new_manifest, new_spine, new_chapters = package_info(zout)
            if (orig_manifest, orig_spine, orig_chapters) != (new_manifest, new_spine, new_chapters):
                raise ValueError('Chapter navigation or manifest changed')
            for name in zin.namelist():
                before, after = zin.read(name), zout.read(name)
                if name in orig_chapters:
                    verify_chapter(before, after)
                elif name != opf_path and before != after:
                    raise ValueError('Non-chapter resource changed: ' + name)
        # Copy only after verification; never overwrite a book.
        if shutil.disk_usage(destination.parent).free - temporary.stat().st_size < MIN_FREE_BYTES:
            raise OSError('Not enough free space on Kobo to keep 1 GB in reserve')
        try:
            with open(destination, 'xb') as target, open(temporary, 'rb') as finished:
                shutil.copyfileobj(finished, target)
        except Exception:
            if destination.exists():
                destination.unlink()
            raise
        print(f'SUCCESS: {destination}')
        print(f'Chapters retained: {len(chapters)}; words bolded: {total:,}')
        print('Original book, navigation files and hyperlink markup preserved.')
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def package_title_structure(root):
    return [(el.tag, tuple(sorted(el.attrib.items()))) for el in root.iter() if isinstance(el.tag, str)]


def is_bionic(path):
    name = path.name.casefold()
    return any(name.endswith(f' (bionic{suffix}){ext}') for suffix in ('', ' light', ' medium', ' strong') for ext in ('.kepub.epub', '.epub'))


def output_path(source):
    name = source.name
    if name.casefold().endswith('.kepub.epub'):
        return source.with_name(name[:-len('.kepub.epub')] + ' (Bionic Medium).kepub.epub')
    return source.with_name(name[:-len('.epub')] + ' (Bionic Medium).epub')


def find_books_folder(explicit=None):
    """Resolve an explicit path or discover a connected Kobo on Windows."""
    if explicit is not None:
        folder = explicit.expanduser().resolve()
        if (folder / 'Books').is_dir() and (folder / '.kobo').is_dir():
            folder = folder / 'Books'
        if not folder.is_dir():
            raise FileNotFoundError(f'Books folder not found: {folder}')
        return folder
    candidates = []
    for letter in 'DEFGHIJKLMNOPQRSTUVWXYZ':
        drive = Path(f'{letter}:\\')
        if (drive / '.kobo').is_dir():
            books = drive / 'Books'
            candidates.append(books if books.is_dir() else drive)
    if not candidates:
        raise FileNotFoundError('No connected Kobo found. Connect it via USB, or pass --books "E:\\Books".')
    if len(candidates) > 1:
        raise RuntimeError('Multiple Kobo devices found. Specify --books: ' + ', '.join(map(str, candidates)))
    return candidates[0]


def main():
    ap = argparse.ArgumentParser(description='Convert Kobo books with medium (40%) Bionic formatting.')
    ap.add_argument('--all', action='store_true', help='Convert every eligible original in the selected folder')
    ap.add_argument('--limit', type=int, default=1, help='Number of books to convert without --all (default: 1)')
    ap.add_argument('--books', type=Path, default=None, help='Kobo Books directory or device root (auto-detected if omitted)')
    ap.add_argument('--scan', action='store_true', help='Read-only inventory of all discovered EPUBs and existing Bionic copies')
    ap.add_argument('--dry-run', action='store_true', help='Show pending books without writing anything')
    args = ap.parse_args()
    source_folder = find_books_folder(args.books)
    print('Scanning:', source_folder)
    sources = sorted((p for p in source_folder.rglob('*') if p.is_file() and p.name.casefold().endswith('.epub') and not is_bionic(p)), key=lambda p: str(p).casefold())
    pending = [(p, output_path(p)) for p in sources if not output_path(p).exists()]
    print(f'Found {len(sources)} original EPUBs; {len(pending)} without a Bionic copy.')
    if args.scan:
        for source in sources:
            print(('EXISTS: ' if output_path(source).exists() else 'PENDING: ') + str(source) + ' -> ' + str(output_path(source)))
        return
    if not args.all:
        pending = pending[:max(0, args.limit)]
        print('LIMITED MODE:', len(pending), 'book(s). Use --all for all remaining books.')
    if args.dry_run:
        for source, destination in pending:
            print('WOULD CONVERT:', source, '->', destination.name)
        return
    if args.all:
        answer = input('Convert ALL remaining books? Type CONVERT ALL: ').strip()
        if answer != 'CONVERT ALL':
            print('Cancelled. No books converted.')
            return
    successes = failures = 0
    for number, (source, destination) in enumerate(pending, 1):
        print(f'\n[{number}/{len(pending)}] {source}')
        try:
            if shutil.disk_usage(source_folder).free - int(source.stat().st_size * 1.5) < MIN_FREE_BYTES:
                print('STOP: insufficient Kobo space (1 GB reserve).')
                break
            convert(source, destination)
            successes += 1
        except Exception as exc:
            failures += 1
            print('FAILED:', source.name, str(exc))
            traceback.print_exc()
    print(f'\nFinished: {successes} converted, {failures} failed. Originals untouched.')
    print('Safely eject Kobo and allow time for its library to import the new books.')


if __name__ == '__main__':
    main()
