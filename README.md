# Kobo Bionic EPUB Converter

A Python utility for creating Bionic Reading editions of books already exported to a Kobo eReader using Calibre.

The converter is designed to run **directly against the book files on a connected Kobo**, after Calibre has completed its export. It creates a separate, Bionic-formatted copy of each selected book while leaving the original file in place.

## Overview

Bionic Reading applies bold formatting to the beginning of words to create visual reading cues. Kobo Bionic EPUB Converter applies this formatting to the text of existing EPUB books without intentionally altering their content or structure.

The tool is designed to preserve the elements that make an EPUB function as a book, including:

* Book metadata, such as title, author and other embedded publication information
* Chapter structure and reading order
* Table of contents and chapter navigation
* Internal hyperlinks, footnotes and other existing links
* Existing images, stylesheets and non-text resources
* The original EPUB file

Each converted book is saved alongside its source file with **`(Bionic)` added to the filename**.

For example:

```text
The Tainted Cup.kepub.epub
The Tainted Cup (Bionic).kepub.epub
```

The result is two separate files: the original book and its Bionic-formatted counterpart. The original is not overwritten.

**Note:** The `(Bionic)` suffix identifies the converted *filename*. Whether that suffix also appears in the book title displayed by the Kobo depends on the EPUB’s embedded title metadata and how the reader indexes the file. The converter’s intended behaviour is to preserve the original embedded metadata.

## Intended workflow

This utility is designed to fit into an existing Calibre-to-Kobo workflow:

1. Organise and prepare your books in Calibre.
2. Export or transfer the books to your Kobo.
3. Connect the Kobo to your computer and allow it to appear as a removable drive.
4. Run Kobo Bionic EPUB Converter against the books already on the device.
5. Safely eject the Kobo and allow the reader to process the new files.

**Run the converter after the Calibre export is complete.** It is not intended to replace Calibre’s library management, metadata editing or book-transfer functions.

## Library scanning and file discovery

Kobo libraries do not all use the same drive letter or folder structure. The converter is being designed to scan a user-selected directory recursively rather than rely on hard-coded book titles or paths.

The scan will identify eligible EPUB files, recognise existing `(Bionic)` copies and show which books are awaiting conversion. It will also provide a read-only way to inspect the discovered file structure before any changes are made.

This approach is intended to support libraries organised into series folders, author folders, genre folders or combinations of these.

## Conversion and file safety

The converter is intended to:

* Create a new file rather than modify the source EPUB.
* Retain the source book’s relative location within the existing folder structure.
* Skip books that already have a completed Bionic copy.
* Preserve EPUB navigation, links, metadata and resources.
* Validate the converted book before reporting a successful conversion.
* Report conversion failures without treating them as successful results.

**Back up your books before running a bulk conversion.** EPUB files can contain different markup and formatting conventions, and some books may require additional handling. A successful file conversion should also be checked in your preferred reading application before processing an entire library.

## Supported files

The converter is intended for EPUB-based books transferred to a Kobo, including files using the `.epub` and `.kepub.epub` filename extensions.

A `.kepub.epub` filename does not, by itself, guarantee compatibility with every Kobo-specific feature. Compatibility will depend on the source file and the conversion method used.

DRM-protected books are not supported. This project does not remove or bypass digital rights management.

## Installation and usage

Installation instructions, dependencies and the final command-line options will be documented when the revised converter and its library scanner have been tested.

The planned interface will support a read-only library scan, a single-book test conversion and a confirmed bulk conversion of remaining books.

## Project status

**In development.** The converter is being revised to handle a wider range of EPUB markup while maintaining checks that protect the original book structure. The scanning workflow and public command-line interface are also being prepared for release.

Until that work is complete, this repository should not be considered a stable bulk-conversion tool.

## Licence

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Disclaimer

This is an independent, community-developed utility and is not affiliated with or endorsed by Kobo, Rakuten Kobo or Calibre.

Users are responsible for ensuring they have the right to modify and create personal copies of the books they process, subject to applicable law and the terms governing those books.
