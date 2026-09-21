
# Kobo Bionic EPUB Converter

Create Bionic Reading editions of EPUB books **directly on your Kobo after transferring them with Calibre**.

Kobo Bionic EPUB Converter is a Python utility that scans a connected Kobo, finds EPUB files in their existing folders, and creates separate copies with the beginning of each word bolded. It offers three formatting strengths: **Light, Medium and Strong**.

The original books remain in place. Converted editions are saved alongside them, with a strength label added to the filename and embedded book title so they can be distinguished in the Kobo library.

> **Recommended workflow:** Transfer and organise your books with Calibre first, then run this converter against the files already on your Kobo. This utility does not replace Calibre.

## Features

- **Three Bionic Reading strengths:** Light (25%), Medium (40%) and Strong (60%).
- **Automatic Kobo detection:** Looks for a connected Kobo rather than requiring a fixed Windows drive letter.
- **Built-in library scanner:** Recursively discovers EPUB files and uses their actual filenames and folder paths.
- **Read-only preview:** Inspect discovered books and planned output paths before converting anything.
- **Non-destructive conversion:** Creates a separate edition without overwriting the original EPUB.
- **Existing-copy detection:** Skips a book when the selected strength’s output file already exists.
- **EPUB structure checks:** Checks converted chapters and package information to detect unexpected changes.
- **Single-book and bulk modes:** Test one book before converting the rest of your library.

The converter is designed to retain the source book’s chapter order, table of contents, internal hyperlinks, footnotes, images, stylesheets and other non-text resources. It changes the embedded title to identify the new edition; other metadata is intended to remain unchanged.

EPUB formatting varies between publishers and conversion tools. A successful conversion check is not a guarantee that every book will display identically in every reading application.

## Choose a formatting strength

| Script | Word prefix bolded | Output label |
|---|---:|---|
| `kobo_bionic_light.py` | 25% | `(Bionic Light)` |
| `kobo_bionic_medium.py` | 40% | `(Bionic Medium)` |
| `kobo_bionic_strong.py` | 60% | `(Bionic Strong)` |

For example, converting a book with the Medium script produces:

```text
Books/
└── Ana & Din Mysteries/
    ├── The Tainted Cup.kepub.epub
    └── The Tainted Cup (Bionic Medium).kepub.epub
```

The converted file stays in the **same folder** as its source. The original remains available, and the converted edition has its own embedded title.

Each strength is a separate edition. Running a different strength can therefore create another copy of the same book. Be mindful of available storage space before converting an entire library at multiple strengths.

## Requirements

- A computer running Python 3.
- A Kobo eReader connected by USB and available as a drive.
- EPUB books already transferred to the Kobo, preferably using Calibre.
- The Python dependency listed in `requirements.txt`.

The scripts are designed for EPUB-based files, including `.epub` and `.kepub.epub` filenames.

**DRM-protected books are not supported.** This project does not remove or bypass DRM.

## Installation

1. Download or clone this repository.
2. Extract it to a folder on your computer.
3. Open PowerShell or a terminal in that folder.
4. Install the required dependency:

   ```powershell
   py -m pip install -r requirements.txt
   ```

On systems where `py` is unavailable, use your installed Python command, such as `python3`, instead.

## Using the converter

### 1. Transfer your books with Calibre

Use Calibre to transfer your books to the Kobo and organise them as you normally would. **Finish the transfer before running the converter.**

Keep the Kobo connected to your computer and ensure its storage is accessible as a drive.

### 2. Scan your Kobo

Start with a read-only scan. For example, to inspect the library using the Light version:

```powershell
py kobo_bionic_light.py --scan
```

The scanner attempts to locate the connected Kobo and recursively discovers eligible EPUB files. It reports the actual source paths, the corresponding output paths and whether a matching converted copy already exists.

**Scanning does not modify any books.**

If automatic detection does not find your Kobo, specify its books folder explicitly:

```powershell
py kobo_bionic_light.py --books "E:\Books" --scan
```

Replace `E:\Books` with the correct path for your device. The drive letter may change each time you reconnect it.

### 3. Preview the pending conversions

To see which books would receive a Medium edition without creating any files:

```powershell
py kobo_bionic_medium.py --dry-run --all
```

Review the paths and make sure the script has selected the correct library.

### 4. Convert one book as a test

Before converting your whole library, test the selected strength on one book:

```powershell
py kobo_bionic_medium.py --limit 1
```

The script selects an eligible book that does not already have a Medium edition. Open the resulting file in your preferred reading application and check its text, chapter navigation and links.

> **Comparing strengths:** The Light, Medium and Strong scripts each select the first book missing *their own* edition. If you want to compare all three strengths on the **same book**, put a copy of that book’s original EPUB in a separate test folder and run each script against that folder using `--books`.

### 5. Convert the remaining books

Once you are satisfied with the test, run the bulk conversion for your chosen strength:

```powershell
py kobo_bionic_medium.py --all
```

The script asks you to type `CONVERT ALL` before proceeding.

It skips books that already have the selected strength’s output file and reports successes and failures as it works. A failed book is not reported as a successful conversion.

**Do not disconnect the Kobo while conversion is running.** When it finishes, safely eject the device and allow the Kobo time to import the new editions into its library.

## Command reference

The following examples use the Medium script. Substitute `kobo_bionic_light.py` or `kobo_bionic_strong.py` to use another strength.

| Command | Purpose |
|---|---|
| `py kobo_bionic_medium.py --scan` | Discover books and show their source and output paths without writing files. |
| `py kobo_bionic_medium.py --dry-run --all` | Preview all pending conversions without writing files. |
| `py kobo_bionic_medium.py --limit 1` | Convert one eligible book as a test. |
| `py kobo_bionic_medium.py --limit 5` | Convert up to five eligible books. |
| `py kobo_bionic_medium.py --all` | Convert all books missing a Medium edition, after confirmation. |
| `py kobo_bionic_medium.py --books "E:\Books" --scan` | Scan a specific books folder instead of relying on automatic detection. |

Run a script with `--help` to see its available options:

```powershell
py kobo_bionic_medium.py --help
```

## File safety and preservation

The converter is designed to make **new files**, not edit source books in place.

During conversion, it checks the source EPUB, processes chapter text, and validates the resulting EPUB before saving the completed edition. Its checks are intended to catch unexpected changes to chapter markup, visible text, hyperlinks, reading order and package resources.

The original book is not overwritten. An existing converted file is also not overwritten.

**Make a backup before bulk conversion.** The converter operates on files stored on your Kobo, and a backup provides a recovery point if the device is disconnected, storage fails or a particular EPUB behaves unexpectedly.

### A note about metadata

The converter deliberately adds the selected Bionic strength to the **embedded book title**, as well as the output filename. This allows the converted edition to appear as a distinct book in the Kobo library.

It is designed to preserve other embedded metadata, including author information, while retaining the original EPUB’s chapter navigation and resources.

## Troubleshooting

**The Kobo is not detected**

Confirm that it is connected by USB, that you have selected the option to connect it to the computer on the Kobo itself, and that its storage appears in File Explorer. If necessary, pass the correct folder using `--books`.

**The scanner finds no books**

Check that you are scanning the folder containing your EPUB files. Your books may be stored somewhere other than a folder named `Books`.

**A book is skipped**

The selected strength’s output file may already exist. The converter does not overwrite an existing edition.

**A book fails verification**

EPUBs can contain complex or unusual markup. The converter stops rather than knowingly saving a file that fails its checks. Keep the original book and the error output so the issue can be investigated.

**The converted book does not appear on the Kobo**

Safely eject the device and allow it time to process newly added files. If it still does not appear, check that the converted file exists and can be opened in an EPUB reader.

## Project status

This is an independently developed utility. The converter has been used on a personal Kobo library, but EPUBs vary widely and compatibility with every book, Kobo firmware version and reading application has not been established.

If you encounter a reproducible problem, please open a GitHub issue with the script version, command used and error message. **Do not upload copyrighted books or personal library files to a public issue.**

## Licence

This project is released under the [MIT License](LICENSE).

## Disclaimer

Kobo Bionic EPUB Converter is an independent project and is not affiliated with or endorsed by Rakuten Kobo, Calibre or the owners of the Bionic Reading trademark.

Only convert books you are legally permitted to modify. Users are responsible for complying with applicable copyright law and the terms governing their books.
