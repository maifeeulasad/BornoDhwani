"""
Bengali Grapheme-to-Phoneme (G2P) Converter
============================================
Converts Bengali Unicode text to IPA phonetic transcription.

Phonology reference: https://en.wikipedia.org/wiki/Bengali_phonology

Key design decisions:
  • NFC normalisation applied on entry (ো = single codepoint, etc.)
  • Nukta (়) peek-ahead: ড+় → /ɽ/, ঢ+় → /ɽʱ/, য+় → /j/
  • Inherent vowel /ɔ/ suppressed:
      – after a virama (conjunct member)
      – on word-final consonant (no following Bengali character)
  • ই/ঈ/ি/ী → /i/; উ/ঊ/ু/ূ → /u/ (no vowel-length distinction)
  • ড/ঢ → /ɽ//ɽʱ/ in non-initial positions
  • য in virama conjunct position → /j/; word-initial/post-consonant → /dʒ/
  • ণ → /n/; ঞ → /n/; শ/ষ → /ʃ/; স → /s/ (configurable)
  • ং assimilates to following consonant's place
  • ঁ (chandrabindu) nasalises the preceding or following vowel
  • হ → [h] word-initial, [ɦ] medial
"""

from __future__ import annotations
import re
import unicodedata
from typing import Optional


# ────────────────────────────────────────────────────────────────────────────
# Unicode constants
# ────────────────────────────────────────────────────────────────────────────
VIRAMA       = '\u09CD'  # ্
ANUSVARA     = '\u0982'  # ং
VISARGA      = '\u0983'  # ঃ
CHANDRABINDU = '\u0981'  # ঁ
NUKTA        = '\u09BC'  # ়


# ────────────────────────────────────────────────────────────────────────────
# Phoneme tables
# ────────────────────────────────────────────────────────────────────────────

INDEPENDENT_VOWELS: dict[str, str] = {
    'অ': 'ɔ', 'আ': 'a',  'ই': 'i',  'ঈ': 'i',
    'উ': 'u', 'ঊ': 'u',  'ঋ': 'ri', 'ৠ': 'rri',
    'ঌ': 'li','ৡ': 'lli','এ': 'e',  'ঐ': 'oi̯',
    'ও': 'o', 'ঔ': 'ou̯',
}

DEPENDENT_VOWELS: dict[str, str] = {
    '\u09BE': 'a',   # া
    '\u09BF': 'i',   # ি
    '\u09C0': 'i',   # ী
    '\u09C1': 'u',   # ু
    '\u09C2': 'u',   # ূ
    '\u09C3': 'ri',  # ৃ
    '\u09C4': 'rri', # ৄ
    '\u09C7': 'e',   # ে
    '\u09C8': 'oi̯',  # ৈ
    '\u09CB': 'o',   # ো
    '\u09CC': 'ou̯',  # ৌ
}

# Base consonants → IPA  (nukta-modified forms handled via peek-ahead)
CONSONANTS: dict[str, str] = {
    # Velars
    'ক': 'k',   'খ': 'kʰ',  'গ': 'ɡ',   'ঘ': 'ɡʱ',  'ঙ': 'ŋ',
    # Palato-alveolars
    'চ': 'tʃ',  'ছ': 'tʃʰ', 'জ': 'dʒ',  'ঝ': 'dʒʱ', 'ঞ': 'n',
    # Retroflexes
    'ট': 'ʈ',   'ঠ': 'ʈʰ',  'ড': 'ɖ',   'ঢ': 'ɖʱ',  'ণ': 'n',
    # Dentals
    'ত': 't',   'থ': 'tʰ',  'দ': 'd',   'ধ': 'dʱ',  'ন': 'n',
    # Labials
    'প': 'p',   'ফ': 'f',   'ব': 'b',   'ভ': 'bʱ',  'ম': 'm',
    # Sonorants / approximants
    'য': 'dʒ',  # /j/ in conjuncts or word-finally via nukta form
    'র': 'r',
    'ল': 'l',
    'শ': 'ʃ',
    'ষ': 'ʃ',
    'স': 's',
    'হ': 'ɦ',  # medial default; initial → 'h' via allophony
    # Nukta forms (ড+় ঢ+় য+় stored as 2-codepoint keys after NFC)
    'ড' + NUKTA: 'ɽ',
    'ঢ' + NUKTA: 'ɽʱ',
    'য' + NUKTA: 'j',
    # Khanda ta
    'ৎ': 't',
    # Avagraha
    'ঽ': 'ɔ',
}

# Characters we recognise as consonant *starters* (single codepoints)
_CONSONANT_STARTERS: set[str] = {
    'ক','খ','গ','ঘ','ঙ',
    'চ','ছ','জ','ঝ','ঞ',
    'ট','ঠ','ড','ঢ','ণ',
    'ত','থ','দ','ধ','ন',
    'প','ফ','ব','ভ','ম',
    'য','র','ল','শ','ষ','স','হ',
    'ৎ','ঽ',
}

BENGALI_DIGITS: dict[str, str] = {
    '০':'0','১':'1','২':'2','৩':'3','৪':'4',
    '৫':'5','৬':'6','৭':'7','৮':'8','৯':'9',
}

PAUSE_CHARS: set[str] = set('।॥,;:!?')

NASAL_VOWEL_MAP: dict[str, str] = {
    'a':'ã','i':'ĩ','u':'ũ','e':'ẽ','o':'õ','ɔ':'ɔ̃','æ':'æ̃','ɛ':'ɛ̃',
}


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def is_bengali(ch: str) -> bool:
    return 0x0980 <= ord(ch) <= 0x09FF


def _nasalise(ipa: str) -> str:
    """Nasalise the rightmost vowel character in an IPA string."""
    chars = list(ipa)
    for idx in range(len(chars) - 1, -1, -1):
        if chars[idx] in NASAL_VOWEL_MAP:
            chars[idx] = NASAL_VOWEL_MAP[chars[idx]]
            return ''.join(chars)
    return ipa


def _apply_nasal_to_tail(ipa: str) -> str:
    """Nasalise the last vowel in an already-emitted IPA fragment."""
    return _nasalise(ipa)


# ────────────────────────────────────────────────────────────────────────────
# Main G2P class
# ────────────────────────────────────────────────────────────────────────────

class BengaliG2P:
    """
    Grapheme-to-Phoneme converter for Standard Bengali.

    Examples
    --------
    >>> g2p = BengaliG2P()
    >>> g2p.convert("বাংলাদেশ")
    'baŋladeʃ'
    >>> g2p.convert("আমি বাংলায় গান গাই")
    'ami baŋlai̯ ɡan ɡai̯'
    >>> g2p.convert("মৃত্যু")
    'mritju'
    """

    def __init__(self, dialect: str = 'standard'):
        """
        Parameters
        ----------
        dialect : 'standard' | 'eastern'
            'eastern'  – Merges স→ʃ; ড/ঢ always flap.
            'standard' – Kolkata / written standard (default).
        """
        self.dialect = dialect

    # ── Public API ──────────────────────────────────────────────────────────

    def convert(self, text: str) -> str:
        """Convert Bengali text to an IPA string."""
        text = unicodedata.normalize('NFC', text)
        tokens = re.split(r'(\s+)', text)
        out: list[str] = []
        for tok in tokens:
            if re.fullmatch(r'\s+', tok):
                out.append(' ')
            elif tok:
                ipa = self._convert_word(tok)
                if ipa:
                    out.append(ipa)
        return ''.join(out).strip()

    def convert_with_details(self, text: str) -> list[dict]:
        """Return per-token dicts with keys: grapheme, ipa, is_bengali."""
        text = unicodedata.normalize('NFC', text)
        tokens = re.split(r'(\s+)', text)
        results = []
        for tok in tokens:
            if not tok or re.fullmatch(r'\s+', tok):
                continue
            is_bn = any(is_bengali(ch) for ch in tok)
            ipa = self._convert_word(tok) if is_bn else tok
            results.append({'grapheme': tok, 'ipa': ipa, 'is_bengali': is_bn})
        return results

    # ── Word-level ───────────────────────────────────────────────────────────

    def _convert_word(self, word: str) -> str:
        chars = list(word)
        n = len(chars)
        out: list[str] = []
        i = 0
        # Track whether we've emitted any Bengali yet (for word-initial detection)
        seen_bengali = False

        while i < n:
            ch = chars[i]

            # Bengali digit
            if ch in BENGALI_DIGITS:
                out.append(BENGALI_DIGITS[ch])
                i += 1
                continue

            # Non-Bengali passthrough
            if not is_bengali(ch):
                out.append('|' if ch in PAUSE_CHARS else ch)
                i += 1
                continue

            # Chandrabindu: nasalise whatever vowel was last emitted
            if ch == CHANDRABINDU:
                if out:
                    out[-1] = _apply_nasal_to_tail(out[-1])
                i += 1
                continue

            # Anusvara ং (standalone, not after consonant — handled in cluster)
            if ch == ANUSVARA:
                next_ch = chars[i + 1] if i + 1 < n else ''
                out.append(self._anusvara_allophone(next_ch))
                i += 1
                continue

            # Visarga ঃ
            if ch == VISARGA:
                out.append('h')
                i += 1
                continue

            # Stray virama (shouldn't appear outside cluster, but guard)
            if ch == VIRAMA:
                i += 1
                continue

            # Independent vowel
            if ch in INDEPENDENT_VOWELS:
                out.append(INDEPENDENT_VOWELS[ch])
                seen_bengali = True
                i += 1
                continue

            # Stray dependent vowel sign (rare)
            if ch in DEPENDENT_VOWELS:
                out.append(DEPENDENT_VOWELS[ch])
                i += 1
                continue

            # Consonant (main path)
            if ch in _CONSONANT_STARTERS:
                word_initial = not seen_bengali
                ipa_chunk, consumed = self._process_consonant(
                    chars, i, word_initial=word_initial
                )
                out.append(ipa_chunk)
                seen_bengali = True
                i += consumed
                continue

            # Nukta by itself (shouldn't happen post-NFC, but guard)
            if ch == NUKTA:
                i += 1
                continue

            # Fallback
            out.append(ch)
            i += 1

        return ''.join(out)

    # ── Consonant cluster processor ─────────────────────────────────────────

    def _process_consonant(
        self, chars: list[str], start: int, word_initial: bool
    ) -> tuple[str, int]:
        """
        Consume a consonant cluster + its following vowel/modifiers.

        Returns (ipa_string, chars_consumed).

        Inherent vowel /ɔ/ is added after the cluster UNLESS:
          – the consonant was followed by virama (it's a conjunct member)
          – it's the last Bengali consonant in the word (word-final, no vowel follows)
        """
        n = len(chars)
        i = start
        cluster_ipa_parts: list[str] = []
        is_first_consonant = True

        # ── Collect cluster (C্C্C...) ──────────────────────────────────────
        while i < n and chars[i] in _CONSONANT_STARTERS:
            c = chars[i]

            # Peek for nukta modifier
            if i + 1 < n and chars[i + 1] == NUKTA:
                key = c + NUKTA
                if key in CONSONANTS:
                    c_ipa = CONSONANTS[key]
                    i += 2  # consume base + nukta
                else:
                    c_ipa = self._base_consonant_ipa(c, word_initial and is_first_consonant)
                    i += 1
            else:
                # য in a virama-conjunct position (not the first consonant of the cluster)?
                # If it's a non-initial cluster member, realise as /j/
                in_conjunct = not is_first_consonant
                c_ipa = self._base_consonant_ipa(
                    c,
                    initial=(word_initial and is_first_consonant),
                    in_conjunct=in_conjunct,
                )
                i += 1

            cluster_ipa_parts.append(c_ipa)
            is_first_consonant = False

            # Does a virama follow? → cluster continues, no inherent vowel on this C
            if i < n and chars[i] == VIRAMA:
                i += 1  # consume virama and loop
            else:
                break   # no virama → end of cluster

        # ── Look ahead for vowel sign / modifiers ──────────────────────────
        j = i
        vowel_ipa: str = ''
        nasal = False
        coda = ''

        if j < n:
            nc = chars[j]

            # Chandrabindu before matra
            if nc == CHANDRABINDU:
                nasal = True
                j += 1
                nc = chars[j] if j < n else ''

            if nc in DEPENDENT_VOWELS:
                vowel_ipa = DEPENDENT_VOWELS[nc]
                j += 1
                # Chandrabindu after matra
                if j < n and chars[j] == CHANDRABINDU:
                    nasal = True
                    j += 1
                # Anusvara after vowel
                if j < n and chars[j] == ANUSVARA:
                    coda = self._anusvara_allophone(chars[j + 1] if j + 1 < n else '')
                    j += 1
                # Visarga after vowel
                if j < n and chars[j] == VISARGA:
                    coda = 'h'
                    j += 1

            elif nc == ANUSVARA:
                vowel_ipa = 'ɔ'
                coda = self._anusvara_allophone(chars[j + 1] if j + 1 < n else '')
                j += 1

            elif nc == VISARGA:
                vowel_ipa = 'ɔ'
                coda = 'h'
                j += 1

            else:
                # No explicit vowel: add inherent /ɔ/ only if more Bengali follows
                remaining_bengali = any(
                    is_bengali(chars[k]) and chars[k] != VIRAMA
                    for k in range(j, n)
                )
                vowel_ipa = 'ɔ' if remaining_bengali else ''

        # j == n: word-final → no inherent vowel (already '')

        # ── Assemble ────────────────────────────────────────────────────────
        cluster_ipa = ''.join(cluster_ipa_parts)
        v = _nasalise(vowel_ipa) if (nasal and vowel_ipa) else vowel_ipa
        return cluster_ipa + v + coda, j - start

    # ── Per-consonant IPA with allophony ────────────────────────────────────

    def _base_consonant_ipa(
        self, ch: str, initial: bool = False, in_conjunct: bool = False
    ) -> str:
        """
        Return IPA for a single consonant codepoint, applying:
          - ড/ঢ → flap in non-initial position
          - হ  → [h] initial, [ɦ] medial
          - য  → [j] when inside a virama conjunct; [dʒ] elsewhere
          - স  → [ʃ] in eastern dialect
        """
        base = CONSONANTS.get(ch, ch)

        if ch == 'ড':
            return 'ɖ' if initial else 'ɽ'
        if ch == 'ঢ':
            return 'ɖʱ' if initial else 'ɽʱ'
        if ch == 'হ':
            return 'h' if initial else 'ɦ'
        if ch == 'য':
            # in conjunct (preceded by virama inside cluster) → semivowel /j/
            if in_conjunct:
                return 'j'
            return 'dʒ'
        if ch == 'স' and self.dialect == 'eastern':
            return 'ʃ'

        return base

    # ── Anusvara place assimilation ──────────────────────────────────────────

    def _anusvara_allophone(self, following: str) -> str:
        """Return assimilated nasal IPA for anusvara before `following` char."""
        velar   = set('কখগঘঙ')
        palatal = set('চছজঝঞ')
        retro   = {'ট','ঠ','ড','ঢ','ণ', 'ড'+NUKTA, 'ঢ'+NUKTA}
        dental  = set('তথদধন')
        labial  = set('পফবভম')

        if following in velar:   return 'ŋ'
        if following in palatal: return 'n'   # /ɲ/ not phonemic
        if following in retro:   return 'n'
        if following in dental:  return 'n'
        if following in labial:  return 'm'
        return 'ŋ'  # default (word-final or before vowel)


# ────────────────────────────────────────────────────────────────────────────
# Convenience wrapper
# ────────────────────────────────────────────────────────────────────────────

def bengali_to_ipa(text: str, dialect: str = 'standard') -> str:
    """One-liner helper."""
    return BengaliG2P(dialect=dialect).convert(text)


# ────────────────────────────────────────────────────────────────────────────
# Demo / CLI
# ────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    g2p = BengaliG2P(dialect='standard')

    demo: list[tuple[str, str]] = [
        # ── Basic vocabulary ──────────────────────────────────────────────
        ('বাংলা',           'bangla'),
        ('বাংলাদেশ',        'bangladesh'),
        ('আমি',             'ami'),
        ('তুমি',            'tumi'),
        ('আমরা',            'we (amɔra)'),
        ('সে',              'she/he'),
        ('বই',              'book'),
        ('মানুষ',           'human'),
        ('পানি',            'water'),
        ('আলো',             'light'),
        ('ঘর',              'house'),
        ('মা',              'mother'),
        ('বাবা',            'father'),
        # ── Aspirates ─────────────────────────────────────────────────────
        ('খাওয়া',          'eating'),
        ('ঘুম',             'sleep'),
        ('থাকা',            'to stay'),
        ('ধন',              'wealth'),
        # ── Retroflexes & flaps ───────────────────────────────────────────
        ('ঢাকা',            'Dhaka'),
        ('পড়া',            'reading (ɽ)'),
        ('বড়',             'big (ɽ)'),
        ('ঢেউ',             'wave'),
        # ── Consonant clusters ────────────────────────────────────────────
        ('গ্রাম',           'gram → village'),
        ('স্কুল',           'school'),
        ('প্রথম',           'first'),
        ('মৃত্যু',          'death (য→j in conjunct)'),
        ('স্পষ্ট',          'clear'),
        ('বিজ্ঞান',         'science'),
        # ── Nasalisation ──────────────────────────────────────────────────
        ('চাঁদ',            'moon (nasal)'),
        ('বাঁশ',            'bamboo (nasal)'),
        ('গাঁও',            'village (nasal)'),
        # ── Anusvara assimilation ─────────────────────────────────────────
        ('বাংলাদেশ',        'anusvara→ŋ before ল'),
        ('রংপুর',           'anusvara→m before প'),
        ('সংখ্যা',          'anusvara→ŋ before খ'),
        ('সন্তান',          'cluster ন্ত'),
        # ── য় /j/ ──────────────────────────────────────────────────────
        ('বাংলায়',          'in Bengali (য়→j)'),
        ('নয়',              'nine (য়→j)'),
        # ── Sentences ─────────────────────────────────────────────────────
        ('আমি বাংলায় গান গাই', 'I sing in Bengali'),
        ('তোমার নাম কী?',       'What is your name?'),
        ('আমার নাম রাহেলা।',    'My name is Rahela.'),
        ('সে ভালো আছে।',        'She/He is well.'),
    ]

    w = 28
    print('Bengali G2P Converter — IPA Output (Standard dialect)')
    print('=' * 72)
    print(f'{"Bengali":<{w}} {"Gloss":<26} {"IPA"}')
    print('-' * 72)
    for bn, gloss in demo:
        ipa = g2p.convert(bn)
        print(f'{bn:<{w}} {gloss:<26} /{ipa}/')

    # Eastern dialect comparison
    print()
    print('Eastern dialect (স→ʃ, ড always ɽ):')
    g2p_east = BengaliG2P(dialect='eastern')
    for bn in ['বাংলাদেশ', 'সে', 'স্কুল', 'ড়াক']:
        print(f'  {bn:<20} /{g2p_east.convert(bn)}/')

    # Detailed breakdown
    print()
    print('Detailed token breakdown: "আমি বাংলায় গান গাই"')
    for tok in g2p.convert_with_details('আমি বাংলায় গান গাই'):
        print(f'  {tok["grapheme"]!r:<16}  →  /{tok["ipa"]}/')

    if len(sys.argv) > 1:
        raw = ' '.join(sys.argv[1:])
        print(f'\nCustom: {raw}')
        print(f'IPA   : /{g2p.convert(raw)}/')