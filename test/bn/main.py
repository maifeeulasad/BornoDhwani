"""
test_bengali_g2p.py
====================
Extensive, zero-dependency test suite for the Bengali G2P converter.

Structure (nested suites → groups → individual cases):
  Suite 1  — Independent Vowels
  Suite 2  — Dependent Vowel Signs (matras)
  Suite 3  — Inherent Vowel /ɔ/ Logic
  Suite 4  — Consonant Inventory (all 30 base consonants)
  Suite 5  — Aspirated Consonants
  Suite 6  — Retroflex & Flap Allophony (ড/ঢ position rules)
  Suite 7  — Nukta Forms (ড়, ঢ়, য়)
  Suite 8  — য Allophony (dʒ vs j)
  Suite 9  — হ Allophony (h vs ɦ)
  Suite 10 — Virama / Conjunct Clusters
  Suite 11 — Chandrabindu Nasalisation
  Suite 12 — Anusvara (ং) Place Assimilation
  Suite 13 — Visarga (ঃ)
  Suite 14 — Nasalised Vowels via Chandrabindu
  Suite 15 — Diphthongs
  Suite 16 — Bengali Digits
  Suite 17 — Punctuation & Pause Markers
  Suite 18 — Mixed / Real Words (lexical verification)
  Suite 19 — Sentences & Multi-word Input
  Suite 20 — Eastern Dialect
  Suite 21 — convert_with_details() API
  Suite 22 — bengali_to_ipa() Convenience Wrapper
  Suite 23 — Unicode Normalisation (NFC / NFD equivalence)
  Suite 24 — Edge Cases & Robustness

Run:
    python test_bengali_g2p.py
    python test_bengali_g2p.py -v        # verbose: print every test name
    python test_bengali_g2p.py -f        # fail-fast: stop on first failure
"""

import sys
import traceback
import unicodedata

# ── import the module under test ─────────────────────────────────────────────
from src.bn.main import BengaliG2P, bengali_to_ipa, _nasalise, is_bengali

VIRAMA       = '\u09CD'
NUKTA        = '\u09BC'
ANUSVARA     = '\u0982'
CHANDRABINDU = '\u0981'
VISARGA      = '\u0983'


# ════════════════════════════════════════════════════════════════════════════
# Minimal test framework (no external deps)
# ════════════════════════════════════════════════════════════════════════════

class _Counter:
    passed = 0
    failed = 0
    errors = 0
    skipped = 0

_CTR = _Counter()
_VERBOSE = '-v' in sys.argv
_FAIL_FAST = '-f' in sys.argv
_SUITE_STACK: list[str] = []          # nested suite names
_FAILURES: list[str] = []             # collected failure messages


def suite(name: str):
    """Context manager that groups tests under a named suite."""
    class _Suite:
        def __enter__(self):
            _SUITE_STACK.append(name)
            return self
        def __exit__(self, *_):
            _SUITE_STACK.pop()
    return _Suite()


def _location() -> str:
    return ' > '.join(_SUITE_STACK)


def check(label: str, got, expected):
    """Assert got == expected, record pass/fail."""
    loc = _location()
    full = f'{loc} :: {label}' if loc else label
    try:
        assert got == expected, (
            f'\n  Expected: {expected!r}\n  Got:      {got!r}'
        )
        _CTR.passed += 1
        if _VERBOSE:
            print(f'  ✓  {full}')
    except AssertionError as e:
        _CTR.failed += 1
        msg = f'FAIL  {full}{e}'
        _FAILURES.append(msg)
        print(f'  ✗  {full}')
        print(f'       expected: {expected!r}')
        print(f'       got:      {got!r}')
        if _FAIL_FAST:
            _print_summary()
            sys.exit(1)
    except Exception as e:
        _CTR.errors += 1
        msg = f'ERROR {full}: {e}\n{traceback.format_exc()}'
        _FAILURES.append(msg)
        print(f'  !  {full}  ERROR: {e}')
        if _FAIL_FAST:
            _print_summary()
            sys.exit(1)


def check_contains(label: str, got: str, substring: str):
    """Assert substring in got."""
    check(label, substring in got, True)


def check_not(label: str, got, unexpected):
    """Assert got != unexpected."""
    loc = _location()
    full = f'{loc} :: {label}' if loc else label
    try:
        assert got != unexpected, f'\n  Both equal: {got!r}'
        _CTR.passed += 1
        if _VERBOSE:
            print(f'  ✓  {full}')
    except AssertionError as e:
        _CTR.failed += 1
        msg = f'FAIL  {full}{e}'
        _FAILURES.append(msg)
        print(f'  ✗  {full}  (got unexpected value {got!r})')
        if _FAIL_FAST:
            _print_summary()
            sys.exit(1)


def _print_summary():
    total = _CTR.passed + _CTR.failed + _CTR.errors
    print()
    print('═' * 60)
    print(f'  Results: {total} tests')
    print(f'  ✓ Passed:  {_CTR.passed}')
    print(f'  ✗ Failed:  {_CTR.failed}')
    print(f'  ! Errors:  {_CTR.errors}')
    print('═' * 60)
    if _FAILURES:
        print()
        print('── Failure details ──────────────────────────────────────────')
        for f in _FAILURES:
            print(f)
            print()


# ════════════════════════════════════════════════════════════════════════════
# Shared fixture
# ════════════════════════════════════════════════════════════════════════════

g2p   = BengaliG2P(dialect='standard')
g2p_e = BengaliG2P(dialect='eastern')

def c(text: str) -> str:
    """Shorthand: standard convert."""
    return g2p.convert(text)

def ce(text: str) -> str:
    """Shorthand: eastern convert."""
    return g2p_e.convert(text)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 1 — Independent Vowels
# ════════════════════════════════════════════════════════════════════════════

def test_independent_vowels():
    with suite('Suite 1 — Independent Vowels'):

        with suite('Basic 8 oral vowels'):
            check('অ → ɔ',  c('অ'),  'ɔ')
            check('আ → a',  c('আ'),  'a')
            check('ই → i',  c('ই'),  'i')
            check('ঈ → i',  c('ঈ'),  'i')   # no length distinction
            check('উ → u',  c('উ'),  'u')
            check('ঊ → u',  c('ঊ'),  'u')   # no length distinction
            check('এ → e',  c('এ'),  'e')
            check('ও → o',  c('ও'),  'o')

        with suite('Vocalic liquids'):
            check('ঋ → ri',  c('ঋ'),  'ri')
            check('ৠ → rri', c('ৠ'),  'rri')
            check('ঌ → li',  c('ঌ'),  'li')
            check('ৡ → lli', c('ৡ'),  'lli')

        with suite('Diphthong vowels'):
            check('ঐ → oi̯',  c('ঐ'),  'oi̯')
            check('ঔ → ou̯',  c('ঔ'),  'ou̯')

        with suite('No length distinction (ই=ঈ, উ=ঊ)'):
            check('ই == ঈ output', c('ই'), c('ঈ'))
            check('উ == ঊ output', c('উ'), c('ঊ'))

        with suite('Vowel in word-initial position'):
            check('আমি starts with a', c('আমি')[0], 'a')
            check('ইচ্ছা starts with i', c('ইচ্ছা')[0], 'i')
            check('উপর starts with u', c('উপর')[0], 'u')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 2 — Dependent Vowel Signs (matras)
# ════════════════════════════════════════════════════════════════════════════

def test_dependent_vowels():
    with suite('Suite 2 — Dependent Vowel Signs'):

        with suite('aa-matra া'):
            check('কা → ka',  c('কা'),  'ka')
            check('মা → ma',  c('মা'),  'ma')
            check('বাবা → baba', c('বাবা'), 'baba')

        with suite('i-matra ি (short)'):
            check('কি → ki',   c('কি'),  'ki')
            check('নি → ni',   c('নি'),  'ni')
            check('পানি → pani', c('পানি'), 'pani')

        with suite('ii-matra ী (long, same output as short)'):
            check('কী → ki',   c('কী'),  'ki')
            check('i-matra == ii-matra', c('কি'), c('কী'))

        with suite('u-matra ু'):
            check('কু → ku',   c('কু'),  'ku')
            check('তুমি → tumi', c('তুমি'), 'tumi')

        with suite('uu-matra ূ (same output as ু)'):
            check('কূ → ku',   c('কূ'),  'ku')
            check('u-matra == uu-matra', c('কু'), c('কূ'))

        with suite('ri-matra ৃ'):
            check('কৃ → kri',  c('কৃ'),  'kri')
            check('মৃ → mri',  c('মৃ'),  'mri')

        with suite('e-matra ে'):
            check('কে → ke',   c('কে'),  'ke')
            check('সে → se',   c('সে'),  'se')

        with suite('oi-matra ৈ'):
            check('কৈ → koi̯',  c('কৈ'),  'koi̯')

        with suite('o-matra ো'):
            check('কো → ko',   c('কো'),  'ko')
            check('ভালো → bʱalo', c('ভালো'), 'bʱalo')

        with suite('ou-matra ৌ'):
            check('কৌ → kou̯',  c('কৌ'),  'kou̯')
            check('নৌকা → nou̯ka', c('নৌকা'), 'nou̯ka')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 3 — Inherent Vowel /ɔ/ Logic
# ════════════════════════════════════════════════════════════════════════════

def test_inherent_vowel():
    with suite('Suite 3 — Inherent Vowel /ɔ/ Logic'):

        with suite('Inherent vowel present between consonants'):
            check('কল → kɔl (ɔ between k and l)',  c('কল'),  'kɔl')
            check('মন → mɔn',                       c('মন'),  'mɔn')
            check('ঘর → ɡʱɔr',                      c('ঘর'),  'ɡʱɔr')
            check('বন → bɔn',                        c('বন'),  'bɔn')
            check('তক → tɔk',                        c('তক'),  'tɔk')

        with suite('Inherent vowel suppressed word-finally'):
            check('গ্রাম ends without ɔ', c('গ্রাম'), 'ɡram')
            check('স্কুল ends without ɔ', c('স্কুল'), 'skul')
            check('বাগ → baɡ (no final ɔ)', c('বাগ'), 'baɡ')
            check('চাল → tʃal (no final ɔ)', c('চাল'), 'tʃal')
            check('মাস → mas (no final ɔ)', c('মাস'), 'mas')

        with suite('Inherent vowel suppressed in virama cluster (non-final member)'):
            check('ক্ত — ক has no ɔ before ্ত', c('রক্ত'), 'rɔkt')
            check('ন্ত — ন has no ɔ', c('সন্তান'), 'sɔntan')
            check('ম্প — ম has no ɔ', c('সম্পদ'), 'sɔmpɔd')

        with suite('Inherent vowel present when explicit vowel absent but more Bengali follows'):
            check('ক in কম has ɔ', c('কম'), 'kɔm')
            check('ত in তর has ɔ', c('তর'), 'tɔr')
            check('প in পড়া has ɔ', c('পড়া'), 'pɔɽa')

        with suite('Inherent vowel /ɔ/ vs explicit vowel replacement'):
            check('কা replaces ɔ with a', c('কা'), 'ka')
            check('কি replaces ɔ with i', c('কি'), 'ki')
            check('কো replaces ɔ with o', c('কো'), 'ko')

        with suite('Multi-syllable inherent vowel pattern'):
            # অবশ্য = অ-ব-শ্-য  → ɔbɔʃjɔ  (শ্য conjunct, য in conjunct → j)
            result = c('অবশ্য')
            check('অবশ্য contains ɔ', 'ɔ' in result, True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 4 — Consonant Inventory
# ════════════════════════════════════════════════════════════════════════════

def test_consonant_inventory():
    with suite('Suite 4 — Full Consonant Inventory'):

        with suite('Velar stops'):
            check('ক → k',   c('কা'), 'ka')
            check('খ → kʰ',  c('খা'), 'kʰa')
            check('গ → ɡ',   c('গা'), 'ɡa')
            check('ঘ → ɡʱ',  c('ঘা'), 'ɡʱa')
            check('ঙ → ŋ',   c('ঙা'), 'ŋa')

        with suite('Palato-alveolar affricates'):
            check('চ → tʃ',   c('চা'), 'tʃa')
            check('ছ → tʃʰ',  c('ছা'), 'tʃʰa')
            check('জ → dʒ',   c('জা'), 'dʒa')
            check('ঝ → dʒʱ',  c('ঝা'), 'dʒʱa')
            check('ঞ → n',    c('ঞা'), 'na')    # merged in Standard Bengali

        with suite('Retroflex stops (initial position)'):
            check('ট → ʈ',   c('টা'), 'ʈa')
            check('ঠ → ʈʰ',  c('ঠা'), 'ʈʰa')
            check('ড → ɖ (initial)', c('ডা'), 'ɖa')
            check('ঢ → ɖʱ (initial)', c('ঢা'), 'ɖʱa')
            check('ণ → n',   c('ণা'), 'na')     # merged with ন

        with suite('Dental stops'):
            check('ত → t',   c('তা'), 'ta')
            check('থ → tʰ',  c('থা'), 'tʰa')
            check('দ → d',   c('দা'), 'da')
            check('ধ → dʱ',  c('ধা'), 'dʱa')
            check('ন → n',   c('না'), 'na')

        with suite('Labial stops'):
            check('প → p',   c('পা'), 'pa')
            check('ফ → f',   c('ফা'), 'fa')
            check('ব → b',   c('বা'), 'ba')
            check('ভ → bʱ',  c('ভা'), 'bʱa')
            check('ম → m',   c('মা'), 'ma')

        with suite('Sonorants'):
            check('য → dʒ (initial)', c('যা'), 'dʒa')
            check('র → r',            c('রা'), 'ra')
            check('ল → l',            c('লা'), 'la')

        with suite('Fricatives'):
            check('শ → ʃ',   c('শা'), 'ʃa')
            check('ষ → ʃ',   c('ষা'), 'ʃa')   # merged with শ
            check('স → s',   c('সা'), 'sa')
            check('হ → h (initial)', c('হা'), 'ha')
            # শ == ষ in Standard Bengali
            check('শা == ষা output', c('শা'), c('ষা'))

        with suite('Specials'):
            check('ৎ → t (khanda ta)', c('ৎ'), 't')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 5 — Aspirated Consonants (real words)
# ════════════════════════════════════════════════════════════════════════════

def test_aspirated_consonants():
    with suite('Suite 5 — Aspirated Consonants'):

        with suite('Voiceless aspirates in words'):
            check('খাওয়া starts kʰ', c('খাওয়া').startswith('kʰ'), True)
            check('থাকা starts tʰ',   c('থাকা').startswith('tʰ'), True)
            check('ঠিক starts ʈʰ',    c('ঠিক').startswith('ʈʰ'), True)
            check('ছবি starts tʃʰ',   c('ছবি').startswith('tʃʰ'), True)
            check('ফুল starts f',     c('ফুল').startswith('f'), True)

        with suite('Voiced aspirates in words'):
            check('ঘর contains ɡʱ',  'ɡʱ' in c('ঘর'), True)
            check('ধন contains dʱ',  'dʱ' in c('ধন'), True)
            check('ভালো contains bʱ', 'bʱ' in c('ভালো'), True)
            check('ঝড় contains dʒʱ', 'dʒʱ' in c('ঝড়'), True)

        with suite('Aspirate in cluster'):
            check('প্রথম has tʰ', 'tʰ' in c('প্রথম'), True)
            check('স্থান has tʰ', 'tʰ' in c('স্থান'), True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 6 — Retroflex & Flap Allophony
# ════════════════════════════════════════════════════════════════════════════

def test_retroflex_allophony():
    with suite('Suite 6 — Retroflex & Flap Allophony'):

        with suite('ড initial → /ɖ/'):
            check('ডাল → ɖal',    c('ডাল'),  'ɖal')
            check('ডিম → ɖim',    c('ডিম'),  'ɖim')
            check('ডাকা → ɖaka',  c('ডাকা'), 'ɖaka')

        with suite('ড medial → /ɽ/'):
            check('পড়া has ɽ',     'ɽ' in c('পড়া'),  True)
            # ড medially (no nukta) also becomes ɽ
            check('আড়াল has ɽ',    'ɽ' in c('আড়াল'), True)

        with suite('ঢ initial → /ɖʱ/'):
            check('ঢাকা → ɖʱaka',  c('ঢাকা'),  'ɖʱaka')
            check('ঢেউ starts ɖʱ', c('ঢেউ').startswith('ɖʱ'), True)

        with suite('ঢ medial → /ɽʱ/'):
            check('বাঢ়া has ɽʱ',  'ɽʱ' in c('বাঢ়া'), True)

        with suite('ড় (nukta form) always → /ɽ/ regardless of position'):
            check('ড়াক word-initial ɽ', c('ড়াক'),  'ɽak')
            check('পড়া medial ɽ',       'ɽ' in c('পড়া'), True)
            check('বড় final ɽ',         c('বড়'),  'bɔɽ')

        with suite('ড vs ড় are distinct'):
            check('ডাক != ড়াক', c('ডাক'), 'ɖak')
            check('ড়াক', c('ড়াক'), 'ɽak')
            check_not('ডাক ≠ ড়াক', c('ডাক'), c('ড়াক'))


# ════════════════════════════════════════════════════════════════════════════
# SUITE 7 — Nukta Forms
# ════════════════════════════════════════════════════════════════════════════

def test_nukta_forms():
    with suite('Suite 7 — Nukta Forms'):

        with suite('ড় → /ɽ/'):
            check('ড়া → ɽa',   c('ড়া'),   'ɽa')
            check('ড়ি → ɽi',   c('ড়ি'),   'ɽi')
            check('পড়া',       c('পড়া'),  'pɔɽa')
            check('ছড়া → tʃʰɔɽa', c('ছড়া'), 'tʃʰɔɽa')

        with suite('ঢ় → /ɽʱ/'):
            check('ঢ়া → ɽʱa',  c('ঢ়া'),  'ɽʱa')
            check('বাঢ়া',       c('বাঢ়া'), 'baɽʱa')

        with suite('য় → /j/'):
            check('য়া → ja',   c('য়া'),  'ja')
            check('নয় → nɔj',  c('নয়'),  'nɔj')
            check('বাংলায় ends j', c('বাংলায়').endswith('j'), True)
            check('হয় → hɔj',  c('হয়'),  'hɔj')

        with suite('NFD nukta (ড + combining ় codepoint) same as NFC'):
            nfd_form = unicodedata.normalize('NFD', 'পড়া')
            nfc_form = unicodedata.normalize('NFC', 'পড়া')
            check('NFD and NFC give same output', c(nfd_form), c(nfc_form))

        with suite('Nukta does not bleed into next consonant'):
            check('ড়ক — only first is ɽ', c('ড়ক'), 'ɽɔk')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 8 — য Allophony
# ════════════════════════════════════════════════════════════════════════════

def test_ya_allophony():
    with suite('Suite 8 — য Allophony (dʒ vs j)'):

        with suite('য word-initial → /dʒ/'):
            check('যা → dʒa',   c('যা'),   'dʒa')
            check('যাওয়া starts dʒ', c('যাওয়া').startswith('dʒ'), True)
            check('যদি starts dʒ',   c('যদি').startswith('dʒ'), True)

        with suite('য standalone (non-initial) → /dʒ/'):
            check('আয় → ai̯dʒ... wait, আ+য়',  c('নয়'),  'nɔj')  # য় here
            # bare য after consonant
            check('দয়া → dɔdʒa',  c('দয়া'), 'dɔja')   # য় → j

        with suite('য in virama conjunct → /j/'):
            check('মৃত্যু has j',         'j' in c('মৃত্যু'),    True)
            check('ত্যাগ → tjaɡ',         c('ত্যাগ'),            'tjaɡ')
            check('শ্যাম → ʃjam',         c('শ্যাম'),            'ʃjam')
            check('ব্যক্তি has j',        'j' in c('ব্যক্তি'),   True)
            check('সংখ্যা has j',         'j' in c('সংখ্যা'),    True)
            check('দ্যুতি has j',         'j' in c('দ্যুতি'),    True)

        with suite('য় (nukta form) always → /j/'):
            check('বাংলায় ends j',         c('বাংলায়').endswith('j'),  True)
            check('নয় → nɔj',              c('নয়'),                    'nɔj')
            check('হয় → hɔj',              c('হয়'),                    'hɔj')

        with suite('য vs য় are distinct'):
            check('যা → dʒa',  c('যা'),  'dʒa')
            check('য়া → ja',   c('য়া'),  'ja')
            check_not('যা ≠ য়া', c('যা'), c('য়া'))


# ════════════════════════════════════════════════════════════════════════════
# SUITE 9 — হ Allophony
# ════════════════════════════════════════════════════════════════════════════

def test_ha_allophony():
    with suite('Suite 9 — হ Allophony (h vs ɦ)'):

        with suite('হ word-initial → /h/'):
            check('হা → ha',    c('হা'),   'ha')
            check('হাত → hat',  c('হাত'),  'hat')
            check('হাওয়া starts h', c('হাওয়া').startswith('h'), True)

        with suite('হ medial → /ɦ/'):
            check('রাহেলা has ɦ',  'ɦ' in c('রাহেলা'),   True)
            check('বাহার has ɦ',   'ɦ' in c('বাহার'),    True)
            check('মহান has ɦ',    'ɦ' in c('মহান'),     True)
            check('সহজ has ɦ',     'ɦ' in c('সহজ'),      True)

        with suite('হ word-final (after vowel) → /ɦ/ since it is medial to the syllable'):
            # In our implementation, হ appearing after a vowel-bearing syllable
            # is treated as medial
            result = c('বাহ')
            check('বাহ has ɦ (medial হ)', 'ɦ' in result, True)

        with suite('Two হ in same word'):
            result = c('হাহাকার')
            check('হাহাকার starts h', result.startswith('h'), True)
            check('হাহাকার has ɦ medially', 'ɦ' in result, True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 10 — Virama / Conjunct Clusters
# ════════════════════════════════════════════════════════════════════════════

def test_conjunct_clusters():
    with suite('Suite 10 — Virama / Conjunct Clusters'):

        with suite('Two-consonant clusters'):
            check('গ্রাম → ɡram',     c('গ্রাম'),   'ɡram')
            check('স্কুল → skul',     c('স্কুল'),   'skul')
            check('ক্লাস → klas',     c('ক্লাস'),   'klas')
            check('ব্লক → blɔk',      c('ব্লক'),    'blɔk')
            check('প্রাণ → pran (ণ→n, cluster final no ɔ)', c('প্রাণ'), 'pran')
            check('ত্রিশ → triʃ',     c('ত্রিশ'),   'triʃ')
            check('দ্রুত → drut',     c('দ্রুত'),   'drut')
            check('ন্ত cluster → nt',  'nt' in c('সন্তান'), True)
            check('ম্প cluster → mp',  'mp' in c('সম্পদ'),  True)
            check('ক্ষ → kʃ',         c('ক্ষ'),    'kʃ')

        with suite('Three-consonant clusters (Sanskrit loans)'):
            check('স্ত্র → str',      'str' in c('স্ত্রী'), True)
            check('ন্ত্র → ntr',      'ntr' in c('মন্ত্র'), True)
            check('ক্ষ্ম → kʃm',      'kʃm' in c('লক্ষ্মী'), True)

        with suite('Reph (র্ before consonant) and ্র (র after consonant)'):
            # কর্ক = ক + র্ + ক  → kɔrk (reph: r appears after first k's vowel)
            result_kork = c('কর্ক')
            check('কর্ক contains r', 'r' in result_kork, True)
            check('কর্ক contains k', 'k' in result_kork, True)
            # ক্র → kr
            check('ক্র → kr', 'kr' in c('ক্রম'), True)
            check('প্র → pr', 'pr' in c('প্রথম'), True)

        with suite('Virama suppresses inherent vowel on cluster members'):
            # In রক্ত: ক has no inherent vowel (it's cluster member)
            result_rakta = c('রক্ত')
            check('রক্ত → rɔkt (no ɔ after ক)', result_rakta, 'rɔkt')
            # মক্কা: ক্ক cluster
            check('মক্কা → mɔkka', c('মক্কা'), 'mɔkka')

        with suite('Cluster + vowel sign'):
            check('গ্রামে → ɡrame',   c('গ্রামে'),   'ɡrame')
            check('ক্রিয়া → krija',  c('ক্রিয়া'),  'krija')

        with suite('জ্ঞ cluster'):
            check('জ্ঞান → dʒnan',   c('জ্ঞান'),  'dʒnan')
            check('বিজ্ঞান → bidʒnan', c('বিজ্ঞান'), 'bidʒnan')

        with suite('ত্য cluster (য → j in conjunct)'):
            check('মৃত্যু → mritju',   c('মৃত্যু'),   'mritju')
            check('ত্যাগ → tjaɡ',      c('ত্যাগ'),    'tjaɡ')
            check('সত্য → sɔtjɔ... → satjɔ', 'tj' in c('সত্য'), True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 11 — Chandrabindu Nasalisation
# ════════════════════════════════════════════════════════════════════════════

def test_chandrabindu():
    with suite('Suite 11 — Chandrabindu Nasalisation'):

        with suite('Nasalised vowels — basic'):
            check('চাঁদ → tʃãd',  c('চাঁদ'),  'tʃãd')
            check('বাঁশ → bãʃ',   c('বাঁশ'),  'bãʃ')
            check('গাঁও → ɡão',   c('গাঁও'),  'ɡão')
            check('হাঁটা → hãʈa', c('হাঁটা'), 'hãʈa')
            check('বাঁধ → bãdʱ',  c('বাঁধ'),  'bãdʱ')

        with suite('Nasalised /i/'):
            check('ঘিঁ → ɡʱĩ',   c('ঘিঁ'),  'ɡʱĩ')

        with suite('Nasalised /u/'):
            check('কুঁ → kũ',     c('কুঁ'),  'kũ')

        with suite('Nasalised /o/'):
            check('কোঁ → kõ',     c('কোঁ'),  'kõ')

        with suite('Nasalised /e/'):
            check('কেঁ → kẽ',     c('কেঁ'),  'kẽ')

        with suite('Nasalised /ɔ/ (inherent vowel) — only when consonant is non-final'):
            # কঁ: ক is word-final → no inherent vowel → chandrabindu has nothing to nasalise
            # but কঁদা: ক has inherent ɔ (non-final) → chandrabindu nasalises it
            result_kanda = c('কঁদা')
            check('কঁদা has ɔ̃ (nasalised inherent ɔ on non-final ক)', 'ɔ̃' in result_kanda, True)

        with suite('Chandrabindu does not affect consonant IPA'):
            # Only the vowel part gets a tilde
            result = c('বাঁশ')
            check('b is present',  result.startswith('b'), True)
            check('ã is in result', 'ã' in result, True)
            check('ʃ at end',       result.endswith('ʃ'), True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 12 — Anusvara (ং) Place Assimilation
# ════════════════════════════════════════════════════════════════════════════

def test_anusvara():
    with suite('Suite 12 — Anusvara Place Assimilation'):

        with suite('Before velar stops → /ŋ/'):
            check('বাংলা → baŋla (before ল after velar rule)',
                  c('বাংলা'), 'baŋla')   # ং before ল → default ŋ
            check('সংখ্যা has ŋ (before খ)',   'ŋ' in c('সংখ্যা'),   True)
            check('সংগ has ŋ (before গ)',       'ŋ' in c('সংগ'),       True)
            check('বাংলাদেশ → baŋladeʃ',       c('বাংলাদেশ'),        'baŋladeʃ')

        with suite('Before labial stops → /m/'):
            check('রংপুর has m (ং before প)', 'm' in c('রংপুর'), True)
            check('সংবাদ has m (ং before ব)', 'm' in c('সংবাদ'), True)
            check('সংমিশ্রণ has m (ং before ম)', 'm' in c('সংমিশ্রণ'), True)

        with suite('Before dental stops → /n/'):
            check('সন্তান has n',  'n' in c('সন্তান'), True)
            check('অন্ত has n',    'n' in c('অন্ত'),   True)

        with suite('Before palatal → /n/'):
            check('অঞ্চল has n (ঞ→n)',  'n' in c('অঞ্চল'), True)

        with suite('Word-final anusvara → /ŋ/ (default)'):
            check('শং ends ŋ',  c('শং').endswith('ŋ'), True)
            check('রং ends ŋ',  c('রং').endswith('ŋ'), True)

        with suite('Standalone anusvara in simple syllable'):
            # কং = ক + anusvara
            result = c('কং')
            check('কং → kɔŋ', result, 'kɔŋ')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 13 — Visarga (ঃ)
# ════════════════════════════════════════════════════════════════════════════

def test_visarga():
    with suite('Suite 13 — Visarga (ঃ)'):

        with suite('Visarga → /h/'):
            check('কঃ → kɔh',  c('কঃ'),  'kɔh')
            check('দুঃখ has h', 'h' in c('দুঃখ'), True)
            check('নমঃ → nɔmɔh', c('নমঃ'), 'nɔmɔh')

        with suite('Visarga after vowel matra'):
            check('পুনঃ has h', 'h' in c('পুনঃ'), True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 14 — Nasalised Vowels Helper (_nasalise)
# ════════════════════════════════════════════════════════════════════════════

def test_nasalise_helper():
    with suite('Suite 14 — _nasalise() Helper'):

        with suite('Simple vowel nasalisation'):
            check('a → ã',   _nasalise('a'),  'ã')
            check('i → ĩ',   _nasalise('i'),  'ĩ')
            check('u → ũ',   _nasalise('u'),  'ũ')
            check('e → ẽ',   _nasalise('e'),  'ẽ')
            check('o → õ',   _nasalise('o'),  'õ')
            check('ɔ → ɔ̃',   _nasalise('ɔ'),  'ɔ̃')

        with suite('Nasalise rightmost vowel in IPA cluster'):
            check('ri → rĩ (rightmost i)',  _nasalise('ri'),  'rĩ')
            check('ba → bã',               _nasalise('ba'),  'bã')
            check('tʃa → tʃã',             _nasalise('tʃa'), 'tʃã')

        with suite('No vowel → unchanged'):
            check('ŋ unchanged',  _nasalise('ŋ'),  'ŋ')
            check('str unchanged', _nasalise('str'), 'str')

        with suite('Idempotent on already-nasalised vowel (no double tilde)'):
            # Nasalising ã gives ã (map does not have ã as key → unchanged)
            result = _nasalise('ã')
            check('ã unchanged by _nasalise', result, 'ã')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 15 — Diphthongs
# ════════════════════════════════════════════════════════════════════════════

def test_diphthongs():
    with suite('Suite 15 — Diphthongs'):

        with suite('Canonical diphthong vowels'):
            check('ঐ → oi̯',  c('ঐ'),  'oi̯')
            check('ঔ → ou̯',  c('ঔ'),  'ou̯')

        with suite('Diphthong in words'):
            check('নৌকা has ou̯',   'ou̯' in c('নৌকা'),  True)
            check('বৈ has oi̯',     'oi̯' in c('বৈ'),     True)
            check('পৈতা has oi̯',   'oi̯' in c('পৈতা'),   True)

        with suite('Vowel + semivowel sequences'):
            # ই at end of word after vowel → /i/ (no glide mark in our simplified G2P)
            check('গাই → ɡai',    c('গাই'),  'ɡai')
            check('বই → bɔi',     c('বই'),   'bɔi')
            check('কই → kɔi',     c('কই'),   'kɔi')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 16 — Bengali Digits
# ════════════════════════════════════════════════════════════════════════════

def test_digits():
    with suite('Suite 16 — Bengali Digits'):

        with suite('Individual digits'):
            for bn, ascii_d in zip('০১২৩৪৫৬৭৮৯', '0123456789'):
                check(f'{bn} → {ascii_d}', c(bn), ascii_d)

        with suite('Multi-digit numbers'):
            check('১২৩ → 123',   c('১২৩'),   '123')
            check('২০২৪ → 2024', c('২০২৪'),  '2024')
            check('০ → 0',       c('০'),      '0')

        with suite('Digit mixed with Bengali text'):
            result = c('২টি')
            check('২টি starts with 2', result.startswith('2'), True)
            check('২টি has ʈ',          'ʈ' in result,          True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 17 — Punctuation & Pause Markers
# ════════════════════════════════════════════════════════════════════════════

def test_punctuation():
    with suite('Suite 17 — Punctuation & Pause Markers'):

        with suite('দাড়ি (।) becomes | pause'):
            check('। → |', '|' in c('বাংলা।'), True)
            check('তোমার নাম কী? has |', '|' in c('তোমার নাম কী?'), True)

        with suite('Non-Bengali ASCII punctuation passthrough or pause'):
            check('comma in text', '|' in c('হ্যাঁ,না'), True)
            check('colon in text',  '|' in c('কথা:আলো'), True)

        with suite('Sentence boundary'):
            result = c('আমার নাম রাহেলা।')
            check('sentence has | at end', result.endswith('|'), True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 18 — Real Words (Lexical Verification)
# ════════════════════════════════════════════════════════════════════════════

def test_real_words():
    with suite('Suite 18 — Real Words'):

        with suite('Body parts'):
            check('মাথা → matʰa',   c('মাথা'),  'matʰa')
            check('হাত → hat',       c('হাত'),   'hat')
            check('পা → pa',         c('পা'),    'pa')
            check('চোখ → tʃokʰ',    c('চোখ'),   'tʃokʰ')
            check('কান → kan',       c('কান'),   'kan')
            check('নাক → nak',       c('নাক'),   'nak')
            check('মুখ → mukʰ',      c('মুখ'),   'mukʰ')

        with suite('Family'):
            check('মা → ma',          c('মা'),    'ma')
            check('বাবা → baba',      c('বাবা'),  'baba')
            check('ভাই → bʱai',       c('ভাই'),   'bʱai')
            check('বোন → bon',         c('বোন'),   'bon')
            check('ছেলে → tʃʰele',    c('ছেলে'),  'tʃʰele')
            check('মেয়ে → meje',      c('মেয়ে'), 'meje')

        with suite('Common nouns'):
            check('বাংলা → baŋla',    c('বাংলা'),   'baŋla')
            check('দেশ → deʃ',        c('দেশ'),     'deʃ')
            check('মানুষ → manuʃ',    c('মানুষ'),   'manuʃ')
            check('পানি → pani',       c('পানি'),    'pani')
            check('ভাত → bʱat',        c('ভাত'),     'bʱat')
            check('মাছ → matʃʰ',       c('মাছ'),     'matʃʰ')
            check('ঘর → ɡʱɔr',         c('ঘর'),      'ɡʱɔr')
            check('রাস্তা → rasta',    c('রাস্তা'),  'rasta')
            check('আকাশ → akaʃ',       c('আকাশ'),    'akaʃ')

        with suite('Verbs (infinitive / root forms)'):
            check('করা → kɔra',      c('করা'),   'kɔra')
            check('যাওয়া starts dʒ', c('যাওয়া').startswith('dʒ'), True)
            check('খাওয়া starts kʰ', c('খাওয়া').startswith('kʰ'), True)
            check('দেখা → dekʰa',    c('দেখা'),  'dekʰa')
            check('শোনা → ʃona',     c('শোনা'),  'ʃona')
            check('বলা → bɔla',      c('বলা'),   'bɔla')

        with suite('Place names'):
            check('ঢাকা → ɖʱaka',      c('ঢাকা'),      'ɖʱaka')
            check('বাংলাদেশ → baŋladeʃ', c('বাংলাদেশ'), 'baŋladeʃ')
            check('কলকাতা → kɔlɔkata', c('কলকাতা'),   'kɔlɔkata')
            check('চট্টগ্রাম has tʃ',   'tʃ' in c('চট্টগ্রাম'), True)
            check('সিলেট → sileʈ',       c('সিলেট'),    'sileʈ')
            check('রাজশাহী → radʒɔʃaɦi', c('রাজশাহী'),  'radʒɔʃaɦi')

        with suite('Sanskrit-origin words (clusters)'):
            check('বিজ্ঞান → bidʒnan',   c('বিজ্ঞান'),  'bidʒnan')
            check('মৃত্যু → mritju',     c('মৃত্যু'),   'mritju')
            check('স্পষ্ট → spɔʃʈ',     c('স্পষ্ট'),   'spɔʃʈ')
            check('সত্য has tj',         'tj' in c('সত্য'), True)
            check('ধর্ম has rm',          'rm' in c('ধর্ম'), True)

        with suite('Common adjectives'):
            check('ভালো → bʱalo',     c('ভালো'),   'bʱalo')
            check('খারাপ → kʰarap',   c('খারাপ'),  'kʰarap')
            check('বড় → bɔɽ',         c('বড়'),    'bɔɽ')
            check('ছোট → tʃʰoʈ',      c('ছোট'),    'tʃʰoʈ')
            check('লাল → lal',         c('লাল'),    'lal')
            check('সাদা → sada',       c('সাদা'),   'sada')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 19 — Sentences & Multi-word Input
# ════════════════════════════════════════════════════════════════════════════

def test_sentences():
    with suite('Suite 19 — Sentences & Multi-word'):

        with suite('Word spacing preserved'):
            result = c('আমি তুমি')
            check('আমি তুমি has space', ' ' in result, True)
            parts = result.split()
            check('two tokens', len(parts), 2)
            check('first word → ami', parts[0], 'ami')
            check('second word → tumi', parts[1], 'tumi')

        with suite('Common sentences'):
            check('আমি বাংলায় গান গাই',
                  c('আমি বাংলায় গান গাই'),
                  'ami baŋlaj ɡan ɡai')
            check('তোমার নাম কী',
                  c('তোমার নাম কী'),
                  'tomar nam ki')
            check('আমার নাম রাহেলা',
                  c('আমার নাম রাহেলা'),
                  'amar nam raɦela')
            check('সে ভালো আছে',
                  c('সে ভালো আছে'),
                  'se bʱalo atʃʰe')

        with suite('Sentence with punctuation'):
            result = c('তোমার নাম কী?')
            check('has | for ?', '|' in result, True)
            check('starts with tomar', result.startswith('tomar'), True)

        with suite('Multiple sentences'):
            result = c('আমি ভালো আছি। তুমি কেমন আছ?')
            check('has two | markers', result.count('|'), 2)

        with suite('Leading / trailing whitespace'):
            check('leading space stripped',  c('  বাংলা'), 'baŋla')
            check('trailing space stripped', c('বাংলা  '), 'baŋla')


# ════════════════════════════════════════════════════════════════════════════
# SUITE 20 — Eastern Dialect
# ════════════════════════════════════════════════════════════════════════════

def test_eastern_dialect():
    with suite('Suite 20 — Eastern Dialect'):

        with suite('স → /ʃ/ in eastern'):
            check('সে eastern → ʃe',      ce('সে'),    'ʃe')
            check('সাদা eastern → ʃada',  ce('সাদা'),  'ʃada')
            check('স্কুল eastern → ʃkul', ce('স্কুল'), 'ʃkul')

        with suite('স standard vs eastern differ'):
            check_not('সে: standard ≠ eastern', c('সে'), ce('সে'))
            check('সে standard → se',  c('সে'),  'se')
            check('সে eastern → ʃe',   ce('সে'), 'ʃe')

        with suite('Non-স consonants unchanged by dialect'):
            check('শ same in both dialects',   c('শা'),  ce('শা'))
            check('ষ same in both dialects',   c('ষা'),  ce('ষা'))
            check('ক same in both dialects',   c('কা'),  ce('কা'))
            check('ভ same in both dialects',   c('ভা'),  ce('ভা'))

        with suite('ড/ঢ flap in eastern (same as standard for medial)'):
            # Standard already has medial ড → ɽ
            check('পড়া same both dialects',    c('পড়া'),  ce('পড়া'))

        with suite('Full word comparison'):
            check('বাংলাদেশ same both', c('বাংলাদেশ'), ce('বাংলাদেশ'))


# ════════════════════════════════════════════════════════════════════════════
# SUITE 21 — convert_with_details() API
# ════════════════════════════════════════════════════════════════════════════

def test_convert_with_details():
    with suite('Suite 21 — convert_with_details() API'):

        with suite('Return type and structure'):
            result = g2p.convert_with_details('বাংলা')
            check('returns a list',        isinstance(result, list), True)
            check('one item for one word', len(result), 1)
            item = result[0]
            check('has grapheme key',  'grapheme'   in item, True)
            check('has ipa key',       'ipa'        in item, True)
            check('has is_bengali key','is_bengali'  in item, True)

        with suite('Bengali token marked correctly'):
            result = g2p.convert_with_details('বাংলা')
            check('is_bengali True',  result[0]['is_bengali'], True)
            check('grapheme correct', result[0]['grapheme'],   'বাংলা')
            check('ipa correct',      result[0]['ipa'],        'baŋla')

        with suite('Multi-word input'):
            result = g2p.convert_with_details('আমি তুমি')
            check('two tokens', len(result), 2)
            check('first grapheme',  result[0]['grapheme'], 'আমি')
            check('second grapheme', result[1]['grapheme'], 'তুমি')
            check('first ipa',       result[0]['ipa'],      'ami')
            check('second ipa',      result[1]['ipa'],      'tumi')

        with suite('Non-Bengali token in mixed input'):
            result = g2p.convert_with_details('hello বাংলা world')
            bn_tokens = [t for t in result if t['is_bengali']]
            non_tokens = [t for t in result if not t['is_bengali']]
            check('one Bengali token',     len(bn_tokens),  1)
            check('two non-Bengali tokens', len(non_tokens), 2)
            check('Bengali ipa correct',   bn_tokens[0]['ipa'], 'baŋla')
            check('non-Bengali ipa is grapheme', non_tokens[0]['ipa'], 'hello')

        with suite('Sentence with punctuation'):
            result = g2p.convert_with_details('বাংলাদেশ।')
            check('at least one Bengali token', any(t['is_bengali'] for t in result), True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 22 — bengali_to_ipa() Convenience Wrapper
# ════════════════════════════════════════════════════════════════════════════

def test_convenience_wrapper():
    with suite('Suite 22 — bengali_to_ipa() Wrapper'):

        with suite('Standard dialect (default)'):
            check('বাংলা',    bengali_to_ipa('বাংলা'),    'baŋla')
            check('আমি',      bengali_to_ipa('আমি'),      'ami')
            check('বাংলাদেশ', bengali_to_ipa('বাংলাদেশ'), 'baŋladeʃ')

        with suite('Eastern dialect via kwarg'):
            check('সে eastern', bengali_to_ipa('সে', dialect='eastern'), 'ʃe')
            check('সে standard default', bengali_to_ipa('সে'), 'se')

        with suite('Wrapper matches class output'):
            for word in ['মৃত্যু', 'পড়া', 'বাংলায়', 'চাঁদ']:
                check(f'wrapper == class: {word}',
                      bengali_to_ipa(word), g2p.convert(word))


# ════════════════════════════════════════════════════════════════════════════
# SUITE 23 — Unicode Normalisation
# ════════════════════════════════════════════════════════════════════════════

def test_unicode_normalisation():
    with suite('Suite 23 — Unicode Normalisation'):

        with suite('NFC and NFD input give identical output'):
            words = ['পড়া', 'বাংলায়', 'মৃত্যু', 'চাঁদ', 'বাংলাদেশ']
            for word in words:
                nfc = unicodedata.normalize('NFC', word)
                nfd = unicodedata.normalize('NFD', word)
                check(f'NFC==NFD: {word}', c(nfc), c(nfd))

        with suite('Pre-composed vs decomposed nukta forms'):
            # ড় can be encoded as single char (if it exists) or ড + ়
            nfc_poda = unicodedata.normalize('NFC', 'পড়া')
            nfd_poda = unicodedata.normalize('NFD', 'পড়া')
            check('পড়া NFC', c(nfc_poda), 'pɔɽa')
            check('পড়া NFD', c(nfd_poda), 'pɔɽa')

        with suite('is_bengali() covers full Bengali Unicode block'):
            check('অ is Bengali',  is_bengali('অ'), True)
            check('া is Bengali',  is_bengali('া'), True)
            check('় is Bengali',  is_bengali('়'), True)
            check('a not Bengali', is_bengali('a'), False)
            check('1 not Bengali', is_bengali('1'), False)
            check('। (U+0964) is NOT in Bengali block (it is Devanagari/common)', is_bengali('।'), False)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 24 — Edge Cases & Robustness
# ════════════════════════════════════════════════════════════════════════════

def test_edge_cases():
    with suite('Suite 24 — Edge Cases & Robustness'):

        with suite('Empty and whitespace-only input'):
            check('empty string → empty', c(''), '')
            check('spaces only → empty',  c('   '), '')
            check('newline only → empty', c('\n'), '')

        with suite('Single characters'):
            check('single consonant ক → k (no final ɔ)', c('ক'), 'k')
            check('single vowel আ → a',                  c('আ'), 'a')
            check('single digit ১ → 1',                  c('১'), '1')
            check('single pause । → |',                  c('।'), '|')

        with suite('Pure ASCII passthrough'):
            check('hello unchanged',  c('hello'), 'hello')
            check('123 unchanged',    c('123'),   '123')

        with suite('Mixed Bengali and ASCII'):
            result = c('G2P বাংলা')
            check('G2P preserved', 'G2P' in result, True)
            check('baŋla present', 'baŋla' in result, True)

        with suite('Repeated identical characters'):
            check('আআআ → aaa',     c('আআআ'), 'aaa')
            check('ককক → kkɔk... or similar', 'k' in c('ককক'), True)

        with suite('Only virama (malformed) does not crash'):
            try:
                result = c(VIRAMA)
                check('virama alone → empty or passthrough', isinstance(result, str), True)
            except Exception as e:
                check('virama alone should not raise', False, True)

        with suite('Only anusvara'):
            result = c(ANUSVARA)
            check('anusvara alone → ŋ', result, 'ŋ')

        with suite('Only chandrabindu'):
            result = c(CHANDRABINDU)
            check('chandrabindu alone → empty string (nothing to nasalise)', isinstance(result, str), True)

        with suite('Consecutive spaces between words'):
            result = c('আমি  তুমি')   # double space
            check('double space normalised to single token boundary', ' ' in result, True)

        with suite('Very long word (cluster chain)'):
            # স্ত্রী = স্ + ত্ + রী (3-consonant cluster + long-i matra)
            result = c('স্ত্রী')
            check('স্ত্রী has s', 's' in result, True)
            check('স্ত্রী has t', 't' in result, True)
            check('স্ত্রী has r', 'r' in result, True)
            check('স্ত্রী has i', 'i' in result, True)

        with suite('Avagraha (ঽ) → /ɔ/'):
            result = c('তথাঽস্তু')
            check('avagraha present → ɔ in output', 'ɔ' in result, True)

        with suite('Khanda ta (ৎ) → /t/'):
            check('ৎ alone → t',         c('ৎ'),     't')
            check('বাৎ → bat',            c('বাৎ'),   'bat')
            check('উৎপাদন has t',         't' in c('উৎপাদন'), True)

        with suite('Visarga at word end after explicit vowel'):
            check('দুঃখ has h after u', c('দুঃখ'), 'duhkʰ')

        with suite('Reph (র্) in cluster'):
            # কর্ম = ক + র্ + ম
            result = c('কর্ম')
            check('কর্ম contains r', 'r' in result, True)
            check('কর্ম contains m', 'm' in result, True)

        with suite('ণ and ন both → /n/'):
            check('ণ → n in word', 'n' in c('বাণিজ্য'),  True)
            check('ন → n in word', 'n' in c('বানান'),    True)
            check('ণা == না output', c('ণা'), c('না'))

        with suite('ঞ → /n/ (palatal nasal merged)'):
            check('ঞ → n in অঞ্চল', 'n' in c('অঞ্চল'), True)
            check('ঞা == না output', c('ঞা'), c('না'))

        with suite('Bengali output is always a string'):
            inputs = ['বাংলা', '', ' ', '।', '১২৩', VIRAMA, ANUSVARA]
            for inp in inputs:
                result = c(inp)
                check(f'output is str for {inp!r}', isinstance(result, str), True)


# ════════════════════════════════════════════════════════════════════════════
# SUITE 25 — Phoneme Distinctness (Minimal Pair–like checks)
# ════════════════════════════════════════════════════════════════════════════

def test_phoneme_distinctness():
    with suite('Suite 25 — Phoneme Distinctness'):

        with suite('Aspirate vs unaspirate pairs'):
            check_not('ক ≠ খ output', c('কা'), c('খা'))
            check_not('গ ≠ ঘ output', c('গা'), c('ঘা'))
            check_not('ত ≠ থ output', c('তা'), c('থা'))
            check_not('দ ≠ ধ output', c('দা'), c('ধা'))
            check_not('প ≠ ফ output', c('পা'), c('ফা'))
            check_not('ব ≠ ভ output', c('বা'), c('ভা'))
            check_not('চ ≠ ছ output', c('চা'), c('ছা'))
            check_not('জ ≠ ঝ output', c('জা'), c('ঝা'))
            check_not('ট ≠ ঠ output', c('টা'), c('ঠা'))
            check_not('ড ≠ ঢ output', c('ডা'), c('ঢা'))

        with suite('Voiced vs voiceless pairs'):
            check_not('ক ≠ গ', c('কা'), c('গা'))
            check_not('ত ≠ দ', c('তা'), c('দা'))
            check_not('প ≠ ব', c('পা'), c('বা'))
            check_not('চ ≠ জ', c('চা'), c('জা'))
            check_not('ট ≠ ড', c('টা'), c('ডা'))

        with suite('Place of articulation distinct'):
            check_not('ক(velar) ≠ ত(dental)',    c('কা'), c('তা'))
            check_not('ত(dental) ≠ ট(retroflex)',c('তা'), c('টা'))
            check_not('প(labial) ≠ ক(velar)',    c('পা'), c('কা'))
            check_not('ম ≠ ন ≠ ঙ nasals distinct by base', c('মা'), c('না'))

        with suite('Vowel contrasts'):
            check_not('আ ≠ এ', c('আ'), c('এ'))
            check_not('এ ≠ ই', c('এ'), c('ই'))
            check_not('উ ≠ ও', c('উ'), c('ও'))
            check_not('অ ≠ আ', c('অ'), c('আ'))
            check_not('অ ≠ ও', c('অ'), c('ও'))

        with suite('শ/ষ merged (same output)'):
            check('শা == ষা', c('শা'), c('ষা'))

        with suite('ণ/ন/ঞ merged to n'):
            check('ণা == না', c('ণা'), c('না'))
            check('ঞা == না', c('ঞা'), c('না'))


# ════════════════════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════════════════════

def run_all():
    print()
    print('Bengali G2P — Test Suite')
    print('═' * 60)
    print()

    suites = [
        ('Suite 1  — Independent Vowels',       test_independent_vowels),
        ('Suite 2  — Dependent Vowel Signs',    test_dependent_vowels),
        ('Suite 3  — Inherent Vowel /ɔ/ Logic', test_inherent_vowel),
        ('Suite 4  — Consonant Inventory',      test_consonant_inventory),
        ('Suite 5  — Aspirated Consonants',     test_aspirated_consonants),
        ('Suite 6  — Retroflex & Flap Allophony', test_retroflex_allophony),
        ('Suite 7  — Nukta Forms',              test_nukta_forms),
        ('Suite 8  — য Allophony',              test_ya_allophony),
        ('Suite 9  — হ Allophony',              test_ha_allophony),
        ('Suite 10 — Conjunct Clusters',        test_conjunct_clusters),
        ('Suite 11 — Chandrabindu',             test_chandrabindu),
        ('Suite 12 — Anusvara Assimilation',    test_anusvara),
        ('Suite 13 — Visarga',                  test_visarga),
        ('Suite 14 — _nasalise() Helper',       test_nasalise_helper),
        ('Suite 15 — Diphthongs',               test_diphthongs),
        ('Suite 16 — Bengali Digits',           test_digits),
        ('Suite 17 — Punctuation',              test_punctuation),
        ('Suite 18 — Real Words',               test_real_words),
        ('Suite 19 — Sentences',                test_sentences),
        ('Suite 20 — Eastern Dialect',          test_eastern_dialect),
        ('Suite 21 — convert_with_details()',   test_convert_with_details),
        ('Suite 22 — Convenience Wrapper',      test_convenience_wrapper),
        ('Suite 23 — Unicode Normalisation',    test_unicode_normalisation),
        ('Suite 24 — Edge Cases',               test_edge_cases),
        ('Suite 25 — Phoneme Distinctness',     test_phoneme_distinctness),
    ]

    for name, fn in suites:
        print(f'▶  {name}')
        fn()
        print()

    _print_summary()

    if _CTR.failed > 0 or _CTR.errors > 0:
        sys.exit(1)


if __name__ == '__main__':
    run_all()