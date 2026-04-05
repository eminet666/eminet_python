"""
pdf_to_epub.py — Convertit un fichier PDF en EPUB

Dépendances :
    pip install pdfplumber ebooklib

Usage :
    python pdf_to_epub.py input.pdf              # génère input.epub
    python pdf_to_epub.py input.pdf -o livre.epub
    python pdf_to_epub.py input.pdf --title "Mon Titre" --author "Auteur"
"""

import argparse
import html
import re
import uuid
from pathlib import Path

import pdfplumber
from ebooklib import epub


# ──────────────────────────────────────────────
# 1. Nettoyage du texte extrait
# ──────────────────────────────────────────────

# Caractères interdits en XML 1.0 (hors \t \n \r)
_INVALID_XML_CHARS = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff\ufffe\uffff]"
)

def sanitize(text: str) -> str:
    """Supprime les caractères invalides en XML et normalise."""
    text = _INVALID_XML_CHARS.sub("", text)
    text = text.replace("\x0c", "\n")   # form-feed → saut de ligne
    return text


# ──────────────────────────────────────────────
# 2. Extraction du texte PDF
# ──────────────────────────────────────────────

def extract_pages(pdf_path: str) -> tuple[list[str], dict]:
    """Retourne (pages, metadata)."""
    pages = []
    metadata = {"title": "", "author": ""}

    with pdfplumber.open(pdf_path) as pdf:
        meta = pdf.metadata or {}
        metadata["title"] = sanitize(meta.get("Title") or "")
        metadata["author"] = sanitize(meta.get("Author") or "")

        for page in pdf.pages:
            raw = page.extract_text() or ""
            pages.append(sanitize(raw))

    return pages, metadata


# ──────────────────────────────────────────────
# 3. Conversion texte → XHTML (bytes)
# ──────────────────────────────────────────────

def text_to_xhtml(text: str, page_num: int) -> bytes:
    """
    Convertit le texte brut d'une page en XHTML valide encodé en UTF-8.
    On retourne des bytes : ebooklib/lxml les parse sans ambiguïté d'encodage.
    """
    lines = text.splitlines() if text else []
    html_parts = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        escaped = html.escape(line, quote=False)
        if len(line) < 80 and line.isupper():
            html_parts.append(f"    <h2>{escaped}</h2>")
        else:
            html_parts.append(f"    <p>{escaped}</p>")

    if not html_parts:
        html_parts = [f"    <p><em>Page {page_num} — contenu non extractible.</em></p>"]

    body_content = "\n".join(html_parts)

    xhtml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"\n'
        '  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="fr">\n'
        '<head>\n'
        '  <meta http-equiv="Content-Type"'
        ' content="application/xhtml+xml; charset=utf-8"/>\n'
        f'  <title>Page {page_num}</title>\n'
        '</head>\n'
        '<body>\n'
        f'  <h1>Page {page_num}</h1>\n'
        f'{body_content}\n'
        '</body>\n'
        '</html>\n'
    )
    return xhtml.encode("utf-8")


# ──────────────────────────────────────────────
# 4. Création du fichier EPUB
# ──────────────────────────────────────────────

CSS = b"""
body  { font-family: Georgia, serif; line-height: 1.7; margin: 1em 2em; }
h1    { font-size: 1.1em; color: #555; border-bottom: 1px solid #ccc;
        padding-bottom: 0.3em; margin-bottom: 0.8em; }
h2    { font-size: 1.05em; font-weight: bold; margin-top: 1.2em; }
p     { margin: 0.4em 0; text-align: justify; }
"""


def build_epub(
    pages: list[str],
    output_path: str,
    title: str = "Document",
    author: str = "Inconnu",
) -> None:
    """Construit et sauvegarde le fichier EPUB."""
    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language("fr")
    book.add_author(author)

    css_item = epub.EpubItem(
        uid="style",
        file_name="style.css",
        media_type="text/css",
        content=CSS,
    )
    book.add_item(css_item)

    chapters: list[epub.EpubHtml] = []
    toc: list[epub.Link] = []

    for i, page_text in enumerate(pages, start=1):
        ch = epub.EpubHtml(
            title=f"Page {i}",
            file_name=f"page_{i:04d}.xhtml",
            lang="fr",
        )
        ch.content = text_to_xhtml(page_text, i)   # bytes
        ch.add_item(css_item)
        book.add_item(ch)
        chapters.append(ch)
        toc.append(epub.Link(f"page_{i:04d}.xhtml", f"Page {i}", f"page{i}"))

    book.toc = toc
    book.spine = ["nav"] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(output_path, book)


# ──────────────────────────────────────────────
# 5. Point d'entrée
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Convertit un PDF en EPUB.")
    parser.add_argument("input", help="Fichier PDF source")
    parser.add_argument("-o", "--output",
                        help="Fichier EPUB de sortie (défaut : même nom que l'entrée)")
    parser.add_argument("--title",  help="Titre  (écrase les métadonnées du PDF)")
    parser.add_argument("--author", help="Auteur (écrase les métadonnées du PDF)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌  Fichier introuvable : {input_path}")
        raise SystemExit(1)

    output_path = args.output or input_path.with_suffix(".epub")

    print(f"📖  Lecture de : {input_path}")
    pages, meta = extract_pages(str(input_path))
    print(f"    {len(pages)} page(s) détectée(s)")

    title  = args.title  or meta["title"]  or input_path.stem
    author = args.author or meta["author"] or "Inconnu"
    print(f"    Titre  : {title}")
    print(f"    Auteur : {author}")

    print(f"✍️   Génération de : {output_path}")
    build_epub(pages, str(output_path), title=title, author=author)

    print(f"✅  EPUB créé avec succès : {output_path}")


if __name__ == "__main__":
    main()
