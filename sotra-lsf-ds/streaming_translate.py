#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inkrementelle Übersetzung von Obersorbisch nach Deutsch.

Ablauf:
1. Segmente aus einer Textdatei zeilenweise einlesen.
2. Im Originalpuffer (hsb) akkumulieren.
3. Gesamten Puffer nach Deutsch übersetzen.
4. Stabilen Anfang der deutschen Übersetzung erkennen.
5. Stabilen deutschen Teil nach Obersorbisch zurückübersetzen.
6. Rückübersetzung unscharf mit dem Originalpuffer vergleichen.
7. Den passenden Anfang aus dem Originalpuffer entfernen.
8. Mit dem verbleibenden Originalpuffer fortfahren.

Wichtig:
Der Originalpuffer wird NICHT durch eine Rückübersetzung
des verbleibenden deutschen Textes ersetzt.
"""

import argparse
import difflib
import re
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

STABILITY_WINDOW = 3
MIN_STABLE_LENGTH = 15

# Mindestähnlichkeit für die unscharfe Suche.
# Wertebereich: 0.0 bis 1.0
MIN_MATCH_RATIO = 0.40

# Mindestanzahl Wörter für einen zuverlässigen Vergleich.
MIN_MATCH_WORDS = 4

REQUEST_DELAY = 0.0

STEPS=False

LINELEN_FUZZY_MATCH = 60

# ------------------------------------------------------------
# Übersetzungsdienst
# ------------------------------------------------------------

def translate_text(
    text,
    source_lang,
    target_lang,
    url=TRANSLATION_URL
):
    """Sendet Text an den Übersetzungsdienst.

    Wenn der Quelltext nicht mit einem Satzzeichen endet,
    wird vor der Übersetzung ein Punkt angehängt.
    """
    if not text.strip():
        return ""

    text = text.rstrip()

    # Punkt ergänzen, wenn kein Satzzeichen am Ende steht.
    #if not re.search(r'[.!?…]["\'»”)\]]*$', text):
    #    text += "."

    payload = {
        "text": text,
        "source_language": source_lang,
        "target_language": target_lang
    }

    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120
    )

    response.raise_for_status()

    return response.json().get("translation", text)


# ------------------------------------------------------------
# Stabilitätserkennung
# ------------------------------------------------------------

def common_prefix(strings):
    """Ermittelt den längsten gemeinsamen Zeichenanfang."""

    if not strings:
        return ""

    prefix = strings[0]

    for text in strings[1:]:
        limit = min(len(prefix), len(text))
        index = 0

        while (
            index < limit
            and prefix[index] == text[index]
        ):
            index += 1

        prefix = prefix[:index]

        if not prefix:
            break

    return prefix


def find_stable_prefix(translations):
    """
    Erkennt einen stabilen Anfang der deutschen Übersetzung.

    Es werden die letzten STABILITY_WINDOW Übersetzungen
    miteinander verglichen.
    """

    if len(translations) < STABILITY_WINDOW:
        return ""

    recent = translations[-STABILITY_WINDOW:]
    prefix = common_prefix(recent)

    if len(prefix) < MIN_STABLE_LENGTH:
        return ""

    # Bevorzugt vollständige Sätze.
    sentence_endings = [
        prefix.rfind("."),
        prefix.rfind("!"),
        prefix.rfind("?")
    ]

    last_sentence_end = max(sentence_endings)

    if last_sentence_end >= MIN_STABLE_LENGTH - 1:
        return prefix[:last_sentence_end + 1].strip()

    # Andernfalls an einer Wortgrenze abschneiden.
    last_space = prefix.rfind(" ")

    if last_space >= MIN_STABLE_LENGTH:
        return prefix[:last_space].strip()

    return ""

def force_stable_prefix(translations):
    """
    Erzwingt die Festlegung eines deutschen Textsegments,
    wenn die normale Stabilitätserkennung nicht erfolgreich ist.

    Strategie:
    1. Längsten gemeinsamen Präfix der Historie bestimmen.
    2. Wenn möglich, an einer Satzgrenze abschneiden.
    3. Andernfalls den Anfang der letzten Übersetzung
       bis zu einer Wortgrenze verwenden.

    Rückgabe:
        Ein nichtleerer deutscher Textanfang oder "".
    """

    if not translations:
        return ""

    # Zunächst den gemeinsamen Präfix der gesamten Historie
    # bestimmen. Das kann auch bei abweichenden Übersetzungen
    # einen brauchbaren gemeinsamen Anfang ergeben.
    prefix = common_prefix(translations)

    if prefix.strip():
        # Satzgrenze bevorzugen.
        sentence_endings = [
            prefix.rfind("."),
            prefix.rfind("!"),
            prefix.rfind("?")
        ]

        last_sentence_end = max(sentence_endings)

        if last_sentence_end >= 0:
            candidate = prefix[:last_sentence_end + 1].strip()

            if candidate:
                return candidate

        # Sonst an der letzten vollständigen Wortgrenze.
        last_space = prefix.rfind(" ")

        if last_space > 0:
            candidate = prefix[:last_space].strip()

            if candidate:
                return candidate

    # Kein brauchbarer gemeinsamer Präfix:
    # Anfang der aktuellsten Übersetzung verwenden.
    latest = translations[-1].strip()

    if not latest:
        return ""

    # Möglichst einen vollständigen Satz verwenden.
    sentence_match = re.search(r"^.*?[.!?](?:\s|$)", latest)

    if sentence_match:
        return sentence_match.group().strip()

    # Sonst den ersten Teil bis zur nächsten Wortgrenze.
    limit = min(LINELEN_FUZZY_MATCH, len(latest))

    if limit < len(latest):
        boundary = latest.rfind(" ", 0, limit)

        if boundary > 0:
            return latest[:boundary].strip()

    # Letzter Rückfall: gesamte bisherige Übersetzung.
    return latest

# ------------------------------------------------------------
# Unscharfe Suche im Originalpuffer
# ------------------------------------------------------------

def tokenize_with_positions(text):
    """
    Zerlegt Text in Wörter und speichert deren Zeichenpositionen.

    Die Positionen beziehen sich auf den Originaltext.
    Satzzeichen bleiben dadurch im Originalpuffer erhalten.
    """

    return [
        (match.group(), match.start(), match.end())
        for match in re.finditer(r"\w+", text, flags=re.UNICODE)
    ]


def normalize_word(word):
    """Normalisiert ein Wort für den Vergleich."""

    return word.casefold()


def find_fuzzy_prefix(original, backtranslated):
    """
    Sucht einen möglichst passenden Anfang im Originalpuffer.

    Verglichen wird die Rückübersetzung des stabilen deutschen
    Abschnitts mit verschiedenen Wortpräfixen des Originals.

    Rückgabe:
        (entfernter_text, resttext, ähnlichkeit)

    Wenn kein zuverlässiger Treffer gefunden wird:
        ("", original, bester_score)

    Es wird ausschließlich ein Präfix des Originalpuffers
    entfernt. Text aus der Mitte oder vom Ende wird niemals
    herausgeschnitten.
    """

    original_tokens = tokenize_with_positions(original)
    translated_tokens = tokenize_with_positions(backtranslated)

    original_words = [
        normalize_word(token[0])
        for token in original_tokens
    ]

    translated_words = [
        normalize_word(token[0])
        for token in translated_tokens
    ]

    #print_section(
    #    "Vergleich: Rückübersetzung (hsb)",
    #    backtranslated
    #)

    print("Wörter der Rückübersetzung:")
    print(translated_words)

    print("\nWörter im Originalpuffer:")
    print(original_words)

    # Ohne genügend Vergleichswörter ist eine zuverlässige
    # unscharfe Suche schwierig.
    if len(translated_words) < MIN_MATCH_WORDS:
        print(
            "\nZu wenige Wörter in der Rückübersetzung. "
            "Der Originalpuffer bleibt unverändert."
        )

        return "", original, 0.0

    if len(original_words) < MIN_MATCH_WORDS:
        print(
            "\nZu wenige Wörter im Originalpuffer. "
            "Der Originalpuffer bleibt unverändert."
        )

        return "", original, 0.0

    target_length = len(translated_words)

    # Die gesuchte Originalspanne kann kürzer oder länger
    # als die Rückübersetzung sein.
    min_length = max(
        MIN_MATCH_WORDS,
        int(target_length * 0.5)
    )

    max_length = min(
        len(original_words),
        int(target_length * 1.8) + 3
    )

    best_score = 0.0
    best_length = 0

    print("\nKandidaten für den Originalpräfix:")

    for candidate_length in range(
        min_length,
        max_length + 1
    ):

        candidate_words = original_words[:candidate_length]

        # Zeichenfolge auf Wortebene vergleichen.
        matcher = difflib.SequenceMatcher(
            None,
            translated_words,
            candidate_words,
            autojunk=False
        )

        similarity = matcher.ratio()

        print(
            f"  {candidate_length:3d} Wörter: "
            f"Ähnlichkeit = {similarity:.3f}"
        )

        if similarity > best_score:
            best_score = similarity
            best_length = candidate_length

    print(f"\nBeste Ähnlichkeit: {best_score:.3f} - {best_length} Wörter")
    # print(f"Erforderliche Ähnlichkeit: {MIN_MATCH_RATIO:.3f}")

    if (
        best_length == 0
        or best_score < MIN_MATCH_RATIO
    ):
        #print(
        #    "\nKein ausreichend zuverlässiger Treffer."
        #    "\nDas Abschneiden wird erzwungen."
        #)

        # Anzahl der Wörter aus der Rückübersetzung als
        # Schätzwert für die Länge des zu entfernenden
        # Originalpräfixes verwenden.
        #
        # Bei zu wenigen Wörtern trotzdem mindestens ein
        # Originalwort entfernen, sofern vorhanden.
        estimated_length = max(
            1,
            len(translated_words)
        )

        # Niemals mehr Wörter entfernen, als vorhanden sind.
        best_length = min(
            estimated_length,
            len(original_tokens)
        )

        if best_length == 0:
            return "", original, best_score

        # Zeichenposition des letzten zu entfernenden Wortes.
        cut_position = original_tokens[best_length - 1][2]

        removed_text = original[:cut_position]
        remaining_text = original[cut_position:].lstrip()

        print_section(
            "ERZWUNGENES Abschneiden: ",
            f"{removed_text} | {remaining_text} - " 
            f"{best_score:.3f} < {MIN_MATCH_RATIO:.3f}."
        )

        #print_section(
        #    "ERZWUNGENES Abschneiden: Verbleibender Text",
        #    remaining_text
        #)

        #print(
        #    f"Warnung: Unscharfe Übereinstimmung "
        #    f"{best_score:.3f} liegt unter dem Grenzwert "
        #    f"{MIN_MATCH_RATIO:.3f}."
        #)

        return removed_text, remaining_text, best_score
    
    # Ende des letzten erkannten Wortes im Originaltext.
    cut_position = original_tokens[best_length - 1][2]

    removed_text = original[:cut_position]
    remaining_text = original[cut_position:].lstrip()

    print_section(
        "Gefundener Originalpräfix",
        f"{removed_text} | {remaining_text}" 
    )

    return removed_text, remaining_text, best_score


# ------------------------------------------------------------
# Ausgabe
# ------------------------------------------------------------

def print_section(title, text):
    print(title)
    print(text if text else "[leer]")
    print("-" * 3)


# ------------------------------------------------------------
# Hauptverarbeitung
# ------------------------------------------------------------

def process_file(input_file, output_file):

    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Eingabedatei nicht gefunden: {input_path}"
        )

    lines = input_path.read_text(
        encoding="utf-8"
    ).splitlines()

    # Originalpuffer in Obersorbisch.
    buffer_hsb = ""

    # Übersetzungen seit dem letzten erfolgreichen Commit.
    translation_history = []

    # Protokoll.
    output_lines = []

    segment_count = 0
    commit_count = 0

    print_section(
        "START",
        f"Eingabe: {input_path}\n"
        f"Ausgabe: {output_path}\n"
        f"Segmente: {len(lines)}\n"
        f"Sprachen: {SOURCE_LANG} -> {TARGET_LANG}\n"
        f"Stabilitätsfenster: {STABILITY_WINDOW}\n"
        f"Mindestlänge stabiler Text: {MIN_STABLE_LENGTH}\n"
        f"Mindestähnlichkeit: {MIN_MATCH_RATIO}"
    )

    for line_number, line in enumerate(lines, start=1):

        if STEPS:
            input("Enter drücken für die nächste Zeile ...")

        if not line.strip():
            print(
                f"\nZeile {line_number}: leer, übersprungen."
            )
            continue

        segment_count += 1

        print()
        print("#" * 72)
        print(f"SEGMENT {segment_count}")
        print("#" * 72)

        # ----------------------------------------------------
        # 1. Originaltext akkumulieren
        # ----------------------------------------------------

        if buffer_hsb:
            buffer_hsb = (
                buffer_hsb.rstrip()
                + " "
                + line.strip()
            )
        else:
            buffer_hsb = line.strip()

        print_section(
            "HSB:",
            buffer_hsb
        )

        # ----------------------------------------------------
        # 2. Gesamten Originalpuffer übersetzen
        # ----------------------------------------------------

        translation_de = translate_text(
            buffer_hsb,
            SOURCE_LANG,
            TARGET_LANG
        )

        print_section(
            "HSB2DE:",
            translation_de
        )

        # ----------------------------------------------------
        # 3. Übersetzung speichern
        # ----------------------------------------------------

        translation_history.append(translation_de)

        # stored_translation_de = translation_de

        #print_section(
        #    "3. Gespeicherter String (de)",
        #    stored_translation_de
        #)

        # ----------------------------------------------------
        # 4. Stabilen deutschen Textanfang suchen
        # ----------------------------------------------------

        stable_prefix_de = find_stable_prefix(
            translation_history
        )

        # Prüfen, ob die normale Stabilitätserkennung gescheitert ist
        # und der Originalpuffer die konfigurierte Schwelle erreicht hat.
        forced_stability = False

        if (
            not stable_prefix_de
            and len(buffer_hsb) >= LINELEN_FUZZY_MATCH
        ):
            stable_prefix_de = force_stable_prefix(
                translation_history
            )

            if stable_prefix_de:
                forced_stability = True

                #print_section(
                #    "DE-forced-stable:",
                #    stable_prefix_de
                #)

        if not stable_prefix_de:

            print_section(
                "DE-NO STABLE PREFIX:",
                "NONE"
            )

            if REQUEST_DELAY:
                time.sleep(REQUEST_DELAY)

            continue

        #if forced_stability:
        #    print(
        #        "WARNUNG: Das deutsche Segment wurde "
        #        "mangels ausreichender Stabilität erzwungen."
        #    )

        print_section(
            "DE-final:",
            f"{stable_prefix_de} - forced={forced_stability}"
        )

        # ----------------------------------------------------
        # 5. Stabilen deutschen Teil rückübersetzen
        # ----------------------------------------------------

        stable_prefix_hsb = translate_text(
            stable_prefix_de,
            TARGET_LANG,
            SOURCE_LANG
        )

        print_section(
            "DE-final2HSB:",
            stable_prefix_hsb
        )

        # ----------------------------------------------------
        # 6. Rückübersetzung unscharf im Original suchen
        # ----------------------------------------------------

        removed_text, remaining_text, similarity = (
            find_fuzzy_prefix(
                buffer_hsb,
                stable_prefix_hsb
            )
        )

        # ----------------------------------------------------
        # 7. Originalpuffer reduzieren
        # ----------------------------------------------------

        print_section(
            "HSB-reduce",
            f"({removed_text or '[nichts entfernt]'}) | {remaining_text}"
        )

        # Ohne erfolgreichen Treffer bleibt der Puffer
        # erhalten und es wird kein Commit ausgeführt.
        if not removed_text:

            #print(
            #    "\nKein Commit: Der Originalpuffer wurde "
            #    "nicht verändert. Die Suche wird bei "
            #    "späteren Segmenten erneut versucht."
            #)

            #output_lines.append(
            #    f"[Segment {segment_count}]\n"
            #    f"Original hsb: {buffer_hsb}\n"
            #    f"Übersetzung de: {translation_de}\n"
            #    f"Stabiler Teil de: {stable_prefix_de}\n"
            #    f"Rückübersetzung hsb: {stable_prefix_hsb}\n"
            #    f"Ähnlichkeit: {similarity:.3f}\n"
            #    f"Status: Kein zuverlässiger Treffer\n"
            #)

            if REQUEST_DELAY:
                time.sleep(REQUEST_DELAY)

            continue

        # Erst bei erfolgreicher Zuordnung wird der Puffer
        # tatsächlich gekürzt.
        old_buffer_hsb = buffer_hsb
        buffer_hsb = remaining_text

        commit_count += 1

        print_section(
            "HSB-new:",
            buffer_hsb
        )

        # Stabilen deutschen Abschnitt dauerhaft protokollieren.
        #output_lines.append(
        #    f"[Commit {commit_count}]\n"
        #    f"Stabiler Text de: {stable_prefix_de}\n"
        #    f"Rückübersetzung hsb: {stable_prefix_hsb}\n"
        #    f"Entfernter Originaltext hsb: {removed_text}\n"
        #    f"Ähnlichkeit: {similarity:.3f}\n"
        #    f"Originalpuffer vorher: {old_buffer_hsb}\n"
        #    f"Originalpuffer nachher: {buffer_hsb}\n"
        #)
        output_lines.append(f"{stable_prefix_de}")

        # Die Historie wird nach erfolgreicher Kürzung
        # zurückgesetzt, da nun ein neuer Textanfang vorliegt.
        translation_history.clear()

        #print_section(
        #    "9. Status nach erfolgreichem Commit",
        #    f"Commit: {commit_count}\n"
        #    f"Verbleibender Originalpuffer: {buffer_hsb}\n"
        #    f"Übersetzungshistorie zurückgesetzt."
        #)

        if REQUEST_DELAY:
            time.sleep(REQUEST_DELAY)

    # --------------------------------------------------------
    # Abschluss
    # --------------------------------------------------------

    print_section(
        "ABSCHLUSS: Verbleibender Originalpuffer (hsb)",
        buffer_hsb
    )

    if buffer_hsb.strip():

        final_translation_de = translate_text(
            buffer_hsb,
            SOURCE_LANG,
            TARGET_LANG
        )

        print_section(
            "ABSCHLUSS: Übersetzung des verbleibenden Textes",
            final_translation_de
        )

        #output_lines.append(
        #    "[Abschluss]\n"
        #    f"Verbleibender Originaltext hsb: {buffer_hsb}\n"
        #    f"Übersetzung de: {final_translation_de}\n"
        #)
        output_lines.append(f"{final_translation_de}")


    #else:
        #output_lines.append(
        #    "[Abschluss]\n"
        #    "Kein verbleibender Originaltext.\n"
        #)

    output_path.write_text(
        "\n".join(output_lines),
        encoding="utf-8"
    )

    print_section(
        "FERTIG",
        f"Verarbeitete Segmente: {segment_count}\n"
        f"Erfolgreiche Commits: {commit_count}\n"
        f"Ergebnisdatei: {output_path}"
    )


# ------------------------------------------------------------
# Kommandozeilenprogramm
# ------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Inkrementelle Übersetzung von Obersorbisch "
            "nach Deutsch mit unscharfer Entfernung "
            "stabiler Textanfänge."
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
        help="Ausgabedatei für das Protokoll"
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
    