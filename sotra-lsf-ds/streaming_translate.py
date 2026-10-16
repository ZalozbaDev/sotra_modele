#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inkrementelle Übersetzung von Obersorbisch nach Deutsch.

Ablauf:
1. Textsegmente aus einer Datei zeilenweise einlesen.
2. Segmente im obersorbischen Eingabepuffer akkumulieren.
3. Den gesamten Puffer nach Deutsch übersetzen.
4. Die Übersetzungen der letzten Durchläufe vergleichen.
5. Einen stabilen Anfang der deutschen Übersetzung erkennen.
6. Den stabilen Anfang zur Kontrolle nach Obersorbisch zurückübersetzen.
7. Den verbleibenden deutschen Text nach Obersorbisch übersetzen.
8. Den zurückübersetzten Rest als neuen Eingabepuffer verwenden.

Sprachcodes:
    Obersorbisch: hsb
    Deutsch:      de
"""

import argparse
import difflib
import sys
import time
from pathlib import Path

import requests


# ------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------

SOURCE_LANG = "hsb"
TARGET_LANG = "de"

TRANSLATION_URL = "http://localhost:3000/translate"

# Anzahl aufeinanderfolgender Übersetzungen, die verglichen werden.
STABILITY_WINDOW = 3

# Mindestlänge eines stabilen Textanfangs.
MIN_STABLE_LENGTH = 40

# Kurze Wartezeit zwischen den Anfragen (Sekunden).
# Bei Bedarf auf 0 setzen.
REQUEST_DELAY = 0.0


# ------------------------------------------------------------
# Übersetzungsdienst
# ------------------------------------------------------------

def translate_text(
    text,
    source_lang,
    target_lang,
    url=TRANSLATION_URL
):
    """
    Sendet Text an den Übersetzungsdienst und gibt die
    Übersetzung zurück.
    """

    payload = {
        "text": text,
        "source_language": source_lang,
        "target_language": target_lang
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=120
    )

    response.raise_for_status()

    return response.json().get("translation", text)


# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------

def common_prefix(strings):
    """
    Ermittelt den längsten gemeinsamen Zeichenanfang
    einer Liste von Strings.
    """

    if not strings:
        return ""

    prefix = strings[0]

    for text in strings[1:]:
        limit = min(len(prefix), len(text))
        index = 0

        while index < limit and prefix[index] == text[index]:
            index += 1

        prefix = prefix[:index]

        if not prefix:
            break

    return prefix


def find_stable_prefix(translations):
    """
    Sucht einen stabilen Anfang in den letzten Übersetzungen.

    Ein stabiler Anfang ist ein Textpräfix, das in allen
    Übersetzungen des Stabilitätsfensters identisch ist.

    Bevorzugt wird eine vollständige Satzgrenze.
    Falls keine Satzgrenze existiert, wird ersatzweise
    eine Wortgrenze verwendet.

    Rückgabe:
        stabiler Text oder leerer String
    """

    if len(translations) < STABILITY_WINDOW:
        return ""

    recent = translations[-STABILITY_WINDOW:]

    prefix = common_prefix(recent)

    if len(prefix) < MIN_STABLE_LENGTH:
        return ""

    # Bevorzugt an einer vollständigen Satzgrenze abschneiden.
    sentence_endings = [
        prefix.rfind("."),
        prefix.rfind("!"),
        prefix.rfind("?")
    ]

    last_sentence_end = max(sentence_endings)

    if last_sentence_end >= MIN_STABLE_LENGTH - 1:
        return prefix[:last_sentence_end + 1].strip()

    # Wenn noch kein vollständiger Satz vorliegt:
    # ersatzweise an einer Wortgrenze abschneiden.
    last_space = prefix.rfind(" ")

    if last_space >= MIN_STABLE_LENGTH:
        return prefix[:last_space].strip()

    return ""


def remove_prefix(text, prefix):
    """
    Entfernt ein bekanntes Präfix aus einem String.

    Diese Funktion wird nur auf die deutsche Übersetzung
    angewendet, nicht auf den ursprünglichen sorbischen Text.
    """

    if not prefix:
        return text

    if text.startswith(prefix):
        return text[len(prefix):].lstrip()

    # Normalerweise sollte das Präfix exakt übereinstimmen.
    # Falls nicht, wird nichts entfernt.
    print(
        "WARNUNG: Der stabile Text ist kein exakter Anfang "
        "der aktuellen Übersetzung."
    )

    return text


def print_section(title, text):
    """
    Gibt einen Verarbeitungsschritt übersichtlich aus.
    """

    print()
    print("=" * 72)
    print(title)
    print("-" * 72)
    print(text if text else "[leer]")
    print("=" * 72)


# ------------------------------------------------------------
# Hauptverarbeitung
# ------------------------------------------------------------

def process_file(input_file, output_file):
    """
    Verarbeitet eine Textdatei zeilenweise.

    Jede nichtleere Eingabezeile wird an den aktuellen
    obersorbischen Eingabepuffer angehängt.

    Sobald ein stabiler deutscher Textanfang erkannt wird,
    wird der verbleibende deutsche Text zurückübersetzt
    und als neuer obersorbischer Eingabepuffer verwendet.
    """

    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Eingabedatei nicht gefunden: {input_path}"
        )

    # Aktueller, noch nicht abgeschlossener Eingabepuffer.
    buffer_hsb = ""

    # Übersetzungen seit dem letzten Commit.
    translation_history = []

    # Letzte gespeicherte deutsche Übersetzung.
    stored_translation_de = ""

    # Protokoll für die Ausgabedatei.
    output_lines = []

    # Statistiken.
    segment_count = 0
    commit_count = 0

    lines = input_path.read_text(
        encoding="utf-8"
    ).splitlines()

    print_section(
        "START",
        f"Eingabedatei: {input_path}\n"
        f"Ausgabedatei: {output_path}\n"
        f"Anzahl Zeilen: {len(lines)}\n"
        f"Sprachen: {SOURCE_LANG} -> {TARGET_LANG}\n"
        f"Stabilitätsfenster: {STABILITY_WINDOW}\n"
        f"Mindestlänge: {MIN_STABLE_LENGTH}"
    )

    for line_number, line in enumerate(lines, start=1):

        # Leere Zeilen überspringen.
        if not line.strip():
            print(
                f"\nZeile {line_number}: leer, wird übersprungen."
            )
            continue

        segment_count += 1

        print()
        print("#" * 72)
        print(
            f"SEGMENT {segment_count} "
            f"(Dateizeile {line_number})"
        )
        print("#" * 72)

        # ----------------------------------------------------
        # Schritt 1: Eingabesegment akkumulieren
        # ----------------------------------------------------

        if buffer_hsb:
            buffer_hsb = buffer_hsb.rstrip() + " " + line.strip()
        else:
            buffer_hsb = line.strip()

        print_section(
            "1. Akkumulierter String Sprache A (hsb)",
            buffer_hsb
        )

        # ----------------------------------------------------
        # Schritt 2: Gesamten Eingabepuffer übersetzen
        # ----------------------------------------------------

        try:
            translation_de = translate_text(
                buffer_hsb,
                SOURCE_LANG,
                TARGET_LANG
            )

        except requests.RequestException as exc:
            print(f"Übersetzungsfehler: {exc}")
            print("Verarbeitung wird abgebrochen.")
            raise

        print_section(
            "2. Übersetzter String Sprache B (de)",
            translation_de
        )

        # ----------------------------------------------------
        # Schritt 3: Übersetzung speichern
        # ----------------------------------------------------

        stored_translation_de = translation_de

        translation_history.append(translation_de)

        print_section(
            "3. Gespeicherter String Sprache B (de)",
            stored_translation_de
        )

        print(
            f"Anzahl gespeicherter Vergleichsübersetzungen: "
            f"{len(translation_history)}"
        )

        # ----------------------------------------------------
        # Schritt 4: Stabilen Anfang suchen
        # ----------------------------------------------------

        stable_prefix_de = find_stable_prefix(
            translation_history
        )

        if not stable_prefix_de:

            print_section(
                "4. Stabiler Teil",
                "Noch kein ausreichend stabiler Textanfang "
                "erkannt. Es wird weiter akkumuliert."
            )

            output_lines.append(
                f"[Segment {segment_count}]\n"
                f"Eingabe hsb: {buffer_hsb}\n"
                f"Übersetzung de: {translation_de}\n"
                f"Status: Noch kein stabiler Textanfang\n"
            )

            if REQUEST_DELAY:
                time.sleep(REQUEST_DELAY)

            continue

        print_section(
            "4. Stabiler Teil Sprache B (de)",
            stable_prefix_de
        )

        # ----------------------------------------------------
        # Schritt 5: Stabilen Teil zurückübersetzen
        # ----------------------------------------------------

        try:
            stable_prefix_hsb = translate_text(
                stable_prefix_de,
                TARGET_LANG,
                SOURCE_LANG
            )

        except requests.RequestException as exc:
            print(f"Rückübersetzungsfehler: {exc}")
            print("Verarbeitung wird abgebrochen.")
            raise

        print_section(
            "5. Rückübersetzung des stabilen Teils "
            "(de -> hsb)",
            stable_prefix_hsb
        )

        # ----------------------------------------------------
        # Schritt 6: Stabilen deutschen Teil entfernen
        # ----------------------------------------------------

        remaining_de = remove_prefix(
            translation_de,
            stable_prefix_de
        )

        print_section(
            "6. Verbleibender String Sprache B (de)",
            remaining_de
        )

        # ----------------------------------------------------
        # Schritt 7: Verbleibenden Text zurückübersetzen
        #
        # WICHTIG:
        # Wir entfernen NICHT einfach Zeichen oder Wörter
        # aus buffer_hsb. Die deutsche Übersetzung und der
        # ursprüngliche sorbische Text können strukturell
        # unterschiedlich sein.
        #
        # Stattdessen erzeugen wir einen neuen Eingabepuffer
        # aus dem verbleibenden deutschen Text.
        # ----------------------------------------------------

        if remaining_de:

            try:
                new_buffer_hsb = translate_text(
                    remaining_de,
                    TARGET_LANG,
                    SOURCE_LANG
                )

            except requests.RequestException as exc:
                print(f"Übersetzungsfehler: {exc}")
                print("Verarbeitung wird abgebrochen.")
                raise

        else:
            new_buffer_hsb = ""

        print_section(
            "7. Rückübersetzung des verbleibenden Textes "
            "(de -> hsb)",
            new_buffer_hsb
        )

        # ----------------------------------------------------
        # Schritt 8: Eingabepuffer reduzieren
        # ----------------------------------------------------

        old_buffer_hsb = buffer_hsb

        buffer_hsb = new_buffer_hsb

        print_section(
            "8. Reduzierung des Eingangsstrings Sprache A",
            f"Vorher:\n{old_buffer_hsb}\n\n"
            f"Nachher:\n{buffer_hsb}"
        )

        print(
            "\nHinweis: Der neue Eingabepuffer ist eine "
            "Rückübersetzung des verbleibenden deutschen "
            "Textes und nicht notwendigerweise eine "
            "wortgetreue Restmenge des Originals."
        )

        # ----------------------------------------------------
        # Schritt 9: Verarbeitung protokollieren
        # ----------------------------------------------------

        commit_count += 1

        output_lines.append(
            f"[Commit {commit_count}]\n"
            f"Stabiler Teil de: {stable_prefix_de}\n"
            f"Rückübersetzung hsb: {stable_prefix_hsb}\n"
            f"Verbleibender Text de: {remaining_de}\n"
            f"Neuer Eingabepuffer hsb: {buffer_hsb}\n"
        )

        # Nach einem Commit beginnt die Stabilitätserkennung
        # für den neuen Eingabepuffer von vorn.
        translation_history.clear()

        print_section(
            "9. Status nach dem Commit",
            f"Commit-Nummer: {commit_count}\n"
            f"Neuer Eingabepuffer: {buffer_hsb}\n"
            f"Vergleichshistorie zurückgesetzt."
        )

        if REQUEST_DELAY:
            time.sleep(REQUEST_DELAY)

    # --------------------------------------------------------
    # Abschluss
    # --------------------------------------------------------

    print_section(
        "ABSCHLUSS: Verbleibender Eingabepuffer",
        buffer_hsb
    )

    # Den verbleibenden Text nach Möglichkeit noch einmal
    # übersetzen, damit auch der letzte Rest ausgegeben wird.
    if buffer_hsb.strip():

        try:
            final_translation_de = translate_text(
                buffer_hsb,
                SOURCE_LANG,
                TARGET_LANG
            )

            print_section(
                "ABSCHLUSS: Letzte Übersetzung nach Deutsch",
                final_translation_de
            )

            output_lines.append(
                "[Abschluss]\n"
                f"Verbleibender Text hsb: {buffer_hsb}\n"
                f"Letzte Übersetzung de: {final_translation_de}\n"
            )

        except requests.RequestException as exc:
            print(
                "WARNUNG: Der verbleibende Text konnte "
                f"nicht abschließend übersetzt werden: {exc}"
            )

            output_lines.append(
                "[Abschluss: Übersetzungsfehler]\n"
                f"Verbleibender Text hsb: {buffer_hsb}\n"
            )

    else:
        output_lines.append(
            "[Abschluss]\n"
            "Kein verbleibender Eingabetext.\n"
        )

    # Ergebnisprotokoll schreiben.
    output_path.write_text(
        "\n".join(output_lines),
        encoding="utf-8"
    )

    print_section(
        "FERTIG",
        f"Verarbeitete Segmente: {segment_count}\n"
        f"Erkannte stabile Abschnitte: {commit_count}\n"
        f"Ergebnisdatei: {output_path}"
    )


# ------------------------------------------------------------
# Kommandozeilenprogramm
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Inkrementelle Übersetzung von Obersorbisch "
            "nach Deutsch mit Stabilitätserkennung."
        )
    )

    parser.add_argument(
        "input",
        help="Eingabedatei mit einem Segment pro Zeile"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="uebersetzungsprotokoll.txt",
        help=(
            "Ausgabedatei für das Protokoll "
            "(Standard: uebersetzungsprotokoll.txt)"
        )
    )

    args = parser.parse_args()

    try:
        process_file(
            args.input,
            args.output
        )

    except (OSError, requests.RequestException) as exc:
        print(
            f"\nFEHLER: {exc}",
            file=sys.stderr
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
    