#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inkrementelle Übersetzung von Obersorbisch nach Deutsch.

Ursprüngliche Zeilengrenzen werden im Originalpuffer gespeichert.
Sie unterstützen sowohl die Erkennung stabiler deutscher Sätze als
auch die Auswahl der Kürzungsposition im obersorbischen Original.
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
MIN_STABLE_LENGTH = 20

MIN_MATCH_RATIO = 0.40
MIN_MATCH_WORDS = 4

REQUEST_DELAY = 0.0
STEPS = False

WORD_COUNT_FUZZY_MATCH = 10

# Eine ursprüngliche Zeilengrenze darf bevorzugt werden, wenn
# ihre Ähnlichkeit höchstens so weit unter dem besten Treffer liegt.
BOUNDARY_SCORE_TOLERANCE = 0.08


# ------------------------------------------------------------
# Übersetzungsdienst
# ------------------------------------------------------------

def translate_text(text, source_lang, target_lang, url=TRANSLATION_URL):
    """Sendet Text an den Übersetzungsdienst."""
    if not text.strip():
        return ""

    text = text.rstrip()

    # Falls gewünscht, hier einen Punkt ergänzen:
    if not re.search(r'[.!?…]["\'»”)\]]*$', text):
        text += "."

    payload = {
        "text": text,
        "source_language": source_lang,
        "target_language": target_lang,
    }

    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    response.raise_for_status()

    return response.json().get("translation", text)


# ------------------------------------------------------------
# Allgemeine Hilfsfunktionen
# ------------------------------------------------------------

def common_prefix(strings):
    """Ermittelt den längsten gemeinsamen Zeichenanfang."""
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


def has_sentence_ending(text):
    """Prüft, ob Text mit einem Satzzeichen endet."""
    return bool(re.search(r'[.!?…]["\'»”)\]]*$', text.rstrip()))


def sentence_prefixes(text):
    """Liefert vollständige Satzpräfixe aus einem Text."""
    prefixes = []
    pattern = re.compile(r'[.!?…]["\'»”)\]]*(?=\s|$)')

    for match in pattern.finditer(text):
        candidate = text[:match.end()].strip()
        if candidate:
            prefixes.append(candidate)

    return prefixes


# ------------------------------------------------------------
# Stabilitätserkennung
# ------------------------------------------------------------

def find_stable_prefix(translations, line_boundary_history=None):
    """
    Erkennt einen stabilen deutschen Anfang.

    Zuerst wird der gemeinsame Präfix der letzten Übersetzungen
    betrachtet. Vollständige Sätze werden bevorzugt.

    Zusätzlich werden Übersetzungen betrachtet, die beim Erreichen
    einer ursprünglichen HSB-Zeilengrenze entstanden sind. Ein dort
    erkannter Satz wird nur verwendet, wenn er in allen aktuellen
    Übersetzungen unverändert am Anfang vorkommt.
    """
    if len(translations) < STABILITY_WINDOW:
        return ""

    recent = translations[-STABILITY_WINDOW:]
    prefix = common_prefix(recent)

    if len(prefix.strip()) >= MIN_STABLE_LENGTH:
        # Vollständigen Satz im gemeinsamen Präfix bevorzugen.
        candidates = sentence_prefixes(prefix)
        if candidates:
            return candidates[-1]

    # Zeilenrand-basierter Rückfall:
    # Ein früherer Übersetzungssnapshot an einer HSB-Zeilengrenze
    # kann einen vollständigen Satz enthalten, der in den neueren
    # Übersetzungen weiterhin unverändert am Anfang steht.
    if line_boundary_history:
        recent_texts = translations[-STABILITY_WINDOW:]

        for item in reversed(line_boundary_history):
            snapshot = item["translation"]

            for candidate in reversed(sentence_prefixes(snapshot)):
                if len(candidate) < MIN_STABLE_LENGTH:
                    continue

                if all(text.startswith(candidate) for text in recent_texts):
                    return candidate

    # Falls kein vollständiger Satz erkennbar ist, auf eine
    # vollständige Wortgrenze des gemeinsamen Präfixes zurückfallen.
    if len(prefix.strip()) >= MIN_STABLE_LENGTH:
        last_space = prefix.rfind(" ")
        if last_space >= MIN_STABLE_LENGTH:
            return prefix[:last_space].strip()

    return ""


def force_stable_prefix(translations, line_boundary_history=None):
    """
    Erzwingt ein deutsches Segment, wenn keine reguläre Stabilität
    erkannt wurde. Satzgrenzen aus früheren Übersetzungen werden
    bevorzugt, sofern sie noch am Anfang der aktuellen Übersetzung
    stehen.
    """
    if not translations:
        return ""

    recent = translations[-STABILITY_WINDOW:]
    prefix = common_prefix(recent)

    candidates = sentence_prefixes(prefix)
    if candidates:
        return candidates[-1]

    # Zeilengrenzen-Historie nutzen, sofern ein Satz aus einem
    # früheren Snapshot noch am Anfang der aktuellen Texte steht.
    if line_boundary_history:
        for item in reversed(line_boundary_history):
            snapshot = item["translation"]

            for candidate in reversed(sentence_prefixes(snapshot)):
                if all(text.startswith(candidate) for text in recent):
                    return candidate

    if prefix.strip():
        last_space = prefix.rfind(" ")
        if last_space > 0:
            return prefix[:last_space].strip()

    latest = translations[-1].strip()
    if not latest:
        return ""

    latest_sentences = sentence_prefixes(latest)
    if latest_sentences:
        return latest_sentences[0]

    # Den erzwungenen Fallback anhand einer Wortanzahl statt einer
    # Zeichenlänge begrenzen.
    latest_tokens = tokenize_with_positions(latest)
    if len(latest_tokens) > WORD_COUNT_FUZZY_MATCH:
        cut_position = latest_tokens[WORD_COUNT_FUZZY_MATCH - 1][2]
        candidate = latest[:cut_position]
    else:
        candidate = latest

    return candidate.strip() or latest


# ------------------------------------------------------------
# Unscharfe Suche im Originalpuffer
# ------------------------------------------------------------

def tokenize_with_positions(text):
    """Zerlegt Text in Wörter und speichert Zeichenpositionen."""
    return [
        (match.group(), match.start(), match.end())
        for match in re.finditer(r"\w+", text, flags=re.UNICODE)
    ]


def normalize_word(word):
    """Normalisiert ein Wort für den Vergleich."""
    return word.casefold()


def score_prefix(translated_words, original_words):
    """Vergleicht Rückübersetzung mit einem Originalwortpräfix."""
    return difflib.SequenceMatcher(
        None,
        translated_words,
        original_words,
        autojunk=False,
    ).ratio()


def find_fuzzy_prefix(original, backtranslated, line_boundaries=None):
    """
    Sucht den passenden Anfang des Originalpuffers.

    Zeilengrenzen werden als zusätzliche Kandidaten berücksichtigt.
    Wenn ein Zeilengrenzen-Kandidat nahezu so gut passt wie der beste
    Treffer, wird die Zeilengrenze bevorzugt. Bei geringer Ähnlichkeit
    wird weiterhin ein Abschneiden erzwungen; wenn möglich an einer
    gespeicherten Zeilengrenze.
    """
    if line_boundaries is None:
        line_boundaries = []

    original_tokens = tokenize_with_positions(original)
    translated_tokens = tokenize_with_positions(backtranslated)

    original_words = [normalize_word(token[0]) for token in original_tokens]
    translated_words = [normalize_word(token[0]) for token in translated_tokens]

    print("Wörter der Rückübersetzung:")
    print(translated_words)
    print("\nWörter im Originalpuffer:")
    print(original_words)

    if not original_tokens:
        return "", original, 0.0, None

    if not translated_words:
        # Ohne Rückübersetzungswörter kann kein sinnvoller Vergleich
        # stattfinden. Eine Zeilengrenze ist hier der sicherste
        # verfügbare Kandidat; sonst bleibt mindestens ein Wort.
        usable = [
            b for b in line_boundaries
            if 0 < b["position"] <= len(original)
        ]
        if usable:
            boundary = usable[0]
            cut_position = boundary["position"]
            removed = original[:cut_position]
            remaining = original[cut_position:].lstrip()
            return removed, remaining, 0.0, boundary

        cut_position = original_tokens[0][2]
        return original[:cut_position], original[cut_position:].lstrip(), 0.0, None

    target_length = len(translated_words)
    min_length = max(1, min(MIN_MATCH_WORDS, int(target_length * 0.5)))
    max_length = min(len(original_words), int(target_length * 1.8) + 3)

    # Kandidaten aus der normalen Wortpräfixsuche.
    candidate_lengths = set(range(min_length, max_length + 1))

    # Auch Zeilengrenzen als Kandidaten zulassen, selbst wenn deren
    # Wortanzahl außerhalb des üblichen Suchbereichs liegt.
    boundary_by_length = {}
    for boundary in line_boundaries:
        position = boundary["position"]
        if position <= 0 or position > len(original):
            continue

        word_count = sum(1 for token in original_tokens if token[2] <= position)
        if word_count > 0:
            candidate_lengths.add(word_count)
            boundary_by_length.setdefault(word_count, []).append(boundary)

    scores = {}
    print("\nKandidaten für den Originalpräfix:")

    for candidate_length in sorted(candidate_lengths):
        if candidate_length > len(original_words):
            continue

        score = score_prefix(
            translated_words,
            original_words[:candidate_length],
        )
        scores[candidate_length] = score

        suffix = " (Zeilengrenze)" if candidate_length in boundary_by_length else ""
        print(
            f"  {candidate_length:3d} Wörter: "
            f"Ähnlichkeit = {score:.3f}{suffix}"
        )

    if not scores:
        return "", original, 0.0, None

    best_length = max(scores, key=scores.get)
    best_score = scores[best_length]

    # Einen fast gleich guten Zeilengrenzen-Kandidaten bevorzugen.
    boundary_options = []
    for length, boundaries in boundary_by_length.items():
        if length not in scores:
            continue
        if scores[length] >= best_score - BOUNDARY_SCORE_TOLERANCE:
            for boundary in boundaries:
                boundary_options.append((scores[length], boundary, length))

    selected_boundary = None

    if boundary_options:
        # Zuerst nach Ähnlichkeit sortieren, dann vollständige
        # Satzzeichen am Zeilenende bevorzugen.
        boundary_options.sort(
            key=lambda item: (
                item[0],
                bool(item[1].get("ends_sentence", False)),
                item[1]["position"],
            ),
            reverse=True,
        )
        boundary_score, selected_boundary, boundary_length = boundary_options[0]
        best_length = boundary_length
        best_score = boundary_score

    print(
        f"\nAusgewählter Kandidat: {best_length} Wörter, "
        f"Ähnlichkeit = {best_score:.3f}"
    )

    if selected_boundary is not None:
        cut_position = selected_boundary["position"]
        print(
            "Kürzungsposition anhand ursprünglicher Zeilengrenze: "
            f"Zeile {selected_boundary['line_number']}"
        )
    else:
        # Wortende verwenden und unmittelbar folgende Satzzeichen
        # mitnehmen, damit z. B. ein Punkt nicht im Restpuffer bleibt.
        cut_position = original_tokens[best_length - 1][2]
        while cut_position < len(original) and not original[cut_position].isspace():
            cut_position += 1

    # Bei geringer Ähnlichkeit weiterhin das Abschneiden erzwingen.
    if best_score < MIN_MATCH_RATIO:
        print(
            "\nWARNUNG: Die Ähnlichkeit liegt unter dem Grenzwert. "
            "Das Abschneiden wird trotzdem erzwungen."
        )

        # Wenn kein brauchbarer Zeilengrenzen-Kandidat gewählt wurde,
        # nach Möglichkeit die Grenze suchen, die der geschätzten
        # Wortanzahl am nächsten liegt.
        if selected_boundary is None and boundary_by_length:
            estimated_length = min(
                max(1, len(translated_words)),
                len(original_tokens),
            )
            possible = []
            for length, boundaries in boundary_by_length.items():
                if length in scores:
                    for boundary in boundaries:
                        possible.append((
                            abs(length - estimated_length),
                            -scores[length],
                            not boundary.get("ends_sentence", False),
                            boundary["position"],
                            boundary,
                            scores[length],
                        ))

            if possible:
                possible.sort(key=lambda item: item[:4])
                _, _, _, _, selected_boundary, boundary_score = possible[0]
                cut_position = selected_boundary["position"]
                best_score = boundary_score
                print(
                    "Erzwungene Kürzung an gespeicherter Zeilengrenze: "
                    f"Zeile {selected_boundary['line_number']}"
                )
        elif selected_boundary is None:
            estimated_length = min(
                max(1, len(translated_words)),
                len(original_tokens),
            )
            cut_position = original_tokens[estimated_length - 1][2]
            while cut_position < len(original) and not original[cut_position].isspace():
                cut_position += 1

    removed_text = original[:cut_position].rstrip()
    remaining_text = original[cut_position:].lstrip()

    print_section(
        "Gewählter Originalpräfix / verbleibender Text",
        f"{removed_text} | {remaining_text}\nÄhnlichkeit: {best_score:.3f}",
    )

    return removed_text, remaining_text, best_score, selected_boundary


# ------------------------------------------------------------
# Ausgabe
# ------------------------------------------------------------

def print_section(title, text):
    print(title)
    print(text if text else "[leer]")
    print("-" * 3)


# ------------------------------------------------------------
# Zeilengrenzen verwalten
# ------------------------------------------------------------

def append_source_line(buffer_hsb, line, line_boundaries, line_number):
    """
    Fügt eine Eingabezeile an den Puffer an und speichert ihre
    ursprüngliche Endposition im zusammengefügten Puffer.
    """
    line = line.strip()
    if not line:
        return buffer_hsb

    if buffer_hsb:
        buffer_hsb = buffer_hsb.rstrip() + " " + line
    else:
        buffer_hsb = line

    line_boundaries.append({
        "position": len(buffer_hsb),
        "line_number": line_number,
        "ends_sentence": has_sentence_ending(line),
    })

    return buffer_hsb


def shift_line_boundaries(line_boundaries, cut_position):
    """
    Entfernt Zeilengrenzen aus dem bereits abgeschnittenen Bereich
    und verschiebt verbleibende Positionen relativ zum neuen Puffer.
    """
    shifted = []

    for boundary in line_boundaries:
        position = boundary["position"]

        # Die Grenze am Ende des entfernten Präfixes ist verbraucht.
        if position <= cut_position:
            continue

        shifted_boundary = dict(boundary)
        shifted_boundary["position"] = position - cut_position
        shifted.append(shifted_boundary)

    return shifted


# ------------------------------------------------------------
# Hauptverarbeitung
# ------------------------------------------------------------

def process_file(input_file, output_file):
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.is_file():
        raise FileNotFoundError(f"Eingabedatei nicht gefunden: {input_path}")

    # splitlines() erhält die einzelnen Zeilen als getrennte Segmente.
    lines = input_path.read_text(encoding="utf-8").splitlines()

    buffer_hsb = ""
    line_boundaries = []

    # Jede Übersetzung entspricht einem Stand des Puffers nach einer
    # Eingabezeile. Die zweite Historie hält die zugehörigen Snapshots
    # an den ursprünglichen Zeilengrenzen fest.
    translation_history = []
    line_boundary_history = []

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
        f"Mindestähnlichkeit: {MIN_MATCH_RATIO}",
    )

    for line_number, line in enumerate(lines, start=1):
        if STEPS:
            input("Enter drücken für die nächste Zeile ...")

        if not line.strip():
            print(f"\nZeile {line_number}: leer, übersprungen.")
            continue

        segment_count += 1

        print()
        print("#" * 72)
        print(f"SEGMENT {segment_count} (Quelldatei-Zeile {line_number})")
        print("#" * 72)

        # 1. Originalzeile anhängen und ihre Endposition speichern.
        buffer_hsb = append_source_line(
            buffer_hsb,
            line,
            line_boundaries,
            line_number,
        )

        print_section("HSB-Puffer:", buffer_hsb)
        print("Gespeicherte Zeilengrenzen:")
        print([
            {
                "position": item["position"],
                "line_number": item["line_number"],
                "ends_sentence": item["ends_sentence"],
            }
            for item in line_boundaries
        ])

        # 2. Gesamten Originalpuffer übersetzen.
        translation_de = translate_text(
            buffer_hsb,
            SOURCE_LANG,
            TARGET_LANG,
        )
        print_section("HSB2DE:", translation_de)

        # 3. Übersetzungshistorie speichern.
        translation_history.append(translation_de)
        line_boundary_history.append({
            "line_number": line_number,
            "source_boundary": len(buffer_hsb),
            "translation": translation_de,
        })

        # 4. Stabilen deutschen Textanfang suchen.
        stable_prefix_de = find_stable_prefix(
            translation_history,
            line_boundary_history,
        )

        forced_stability = False

        if (
            not stable_prefix_de
            and len(tokenize_with_positions(buffer_hsb)) >= WORD_COUNT_FUZZY_MATCH
        ):
            stable_prefix_de = force_stable_prefix(
                translation_history,
                line_boundary_history,
            )
            forced_stability = bool(stable_prefix_de)

        if not stable_prefix_de:
            print_section("DE-NO STABLE PREFIX:", "NONE")
            if REQUEST_DELAY:
                time.sleep(REQUEST_DELAY)
            continue

        print_section(
            "DE-final:",
            f"{stable_prefix_de} - forced={forced_stability}",
        )

        # 5. Den stabilen deutschen Teil zurückübersetzen.
        stable_prefix_hsb = translate_text(
            stable_prefix_de,
            TARGET_LANG,
            SOURCE_LANG,
        )
        print_section("DE-final2HSB:", stable_prefix_hsb)

        # 6. Rückübersetzung im Originalpuffer suchen; gespeicherte
        # Zeilengrenzen werden als zusätzliche Kandidaten verwendet.
        removed_text, remaining_text, similarity, selected_boundary = (
            find_fuzzy_prefix(
                buffer_hsb,
                stable_prefix_hsb,
                line_boundaries,
            )
        )

        print_section(
            "HSB-reduce",
            f"({removed_text or '[nichts entfernt]'}) | {remaining_text}",
        )

        # Ohne entfernten Text keinen Commit durchführen.
        if not removed_text:
            if REQUEST_DELAY:
                time.sleep(REQUEST_DELAY)
            continue

        # 7. Puffer und Zeilengrenzen gemeinsam aktualisieren.
        old_buffer_hsb = buffer_hsb
        cut_position = len(removed_text)
        buffer_hsb = remaining_text
        line_boundaries = shift_line_boundaries(
            line_boundaries,
            cut_position,
        )

        commit_count += 1

        print_section("HSB-new:", buffer_hsb)
        print("Verbleibende Zeilengrenzen:")
        print([
            {
                "position": item["position"],
                "line_number": item["line_number"],
                "ends_sentence": item["ends_sentence"],
            }
            for item in line_boundaries
        ])

        output_lines.append(stable_prefix_de.strip())

        # Nach dem Commit beziehen sich die Übersetzungen auf einen
        # neuen Pufferanfang; deshalb die Historien zurücksetzen.
        translation_history.clear()
        line_boundary_history.clear()

        if REQUEST_DELAY:
            time.sleep(REQUEST_DELAY)

    # Abschluss: verbleibenden Originalpuffer übersetzen.
    print_section("ABSCHLUSS: Verbleibender HSB-Puffer", buffer_hsb)

    if buffer_hsb.strip():
        final_translation_de = translate_text(
            buffer_hsb,
            SOURCE_LANG,
            TARGET_LANG,
        )
        print_section(
            "ABSCHLUSS: Übersetzung des verbleibenden Textes",
            final_translation_de,
        )
        if final_translation_de.strip():
            output_lines.append(final_translation_de.strip())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(output_lines) + ("\n" if output_lines else ""),
        encoding="utf-8",
    )

    print_section(
        "FERTIG",
        f"Verarbeitete Segmente: {segment_count}\n"
        f"Erfolgreiche Commits: {commit_count}\n"
        f"Ergebnisdatei: {output_path}",
    )


# ------------------------------------------------------------
# Kommandozeilenprogramm
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Inkrementelle Übersetzung von Obersorbisch nach Deutsch "
            "mit stabiler Segmentierung und gespeicherten Zeilengrenzen."
        )
    )

    parser.add_argument(
        "input",
        help="Eingabedatei mit einem Segment pro Zeile",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="uebersetzungsprotokoll.txt",
        help="Ausgabedatei für die deutsche Übersetzung",
    )
    parser.add_argument(
        "--steps",
        action="store_true",
        help="Vor jeder Eingabezeile auf Enter warten",
    )

    args = parser.parse_args()

    global STEPS
    STEPS = args.steps

    try:
        process_file(args.input, args.output)
    except (OSError, requests.RequestException) as exc:
        print(f"\nFEHLER: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
