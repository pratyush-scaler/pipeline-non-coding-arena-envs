"""Reproducible data minimization against a recovered, hash-bound source.

Policies compute their own edits. An author cannot submit arbitrary replacement
text or offsets and receive anonymized-source credit. Private originals remain
in the recovered trace; reviewer receipts omit the removed values.
"""
from __future__ import annotations
import hashlib
import re
from pathlib import Path, PurePosixPath

from ..author.contracts import contained, strict_json
from ..dump import recover as rec
from ..privacy import ABSENCE_NOTE, SSH_EXAMPLE, health_absence_spans, ssh_endpoints, web_access_default_spans
from .anonymization import _keys, sha

MANIFEST = "provenance/privacy-redaction.json"
SCHEMA = "arena-pipeline/privacy-redaction/1"
KINDS = {"ssh-access-metadata", "exam-attempt-metadata", "exam-item-performance", "health-absence-metadata",
         "web-access-default-metadata", "network-device-identifiers", "course-lecturer-name",
         "person-name-example", "client-body-profile", "source-code-secret-literal",
         "health-self-disclosure", "chat-participant-identity", "chat-handle", "contact-number",
         "meeting-link", "hospital-stay-disclosure", "email"}


def email_changes(content: str) -> list[dict]:
    """Replace every real email address with `contact-N@example.com`, the same N for
    the same address within one file, so cross-references inside the file survive."""
    from ..privacy import PATTERNS, _not_an_address
    seen: dict[str, int] = {}
    changes = []
    for match in PATTERNS["email"].finditer(content):
        if _not_an_address(match.group(1)):
            continue
        address = match.group(0).lower()
        number = seen.setdefault(address, len(seen) + 1)
        changes.append({"start": match.start(), "end": match.end(),
                        "line": content.count("\n", 0, match.start()) + 1,
                        "kind": "email", "replacement": f"contact-{number}@example.com"})
    return changes

# -- source-code-secret-literal -----------------------------------------------
# A recovered source file hard-codes a secret -- a save-integrity salt, an API
# key, a password -- as a string literal assigned to a name that says so. The
# value answers no graded question and ships to every solver. The assignment and
# its name stay; only the literal's characters become a placeholder, inside the
# same quotes. Applied only on explicit request to NAMED files (`apply`), never
# by `minimize`, because a name pattern alone is not proof of a secret
# (a-015, semantic review 2026-09-29: `local SECRET_SALT = "..."`).
_SECRET_ASSIGN = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*(?:SECRET|SALT|TOKEN|PASSWORD|PASSWD|API_?KEY|PRIVATE_?KEY)[A-Za-z0-9_]*\b"
    r"\s*[:=]\s*(?P<q>[\"'])(?P<value>[^\"'\n]{4,})(?P=q)")
SECRET_PLACEHOLDER = "REDACTED_SECRET"


def secret_literal_changes(content: str) -> list:
    return [{"start": m.start("value"), "end": m.end("value"),
             "line": content.count("\n", 0, m.start("value")) + 1,
             "kind": "source-code-secret-literal", "replacement": SECRET_PLACEHOLDER}
            for m in _SECRET_ASSIGN.finditer(content)]

# -- health-self-disclosure --------------------------------------------------
# A recovered client message names a diagnosis the client gave about herself, and
# a brief question repeats it (a-017, semantic review 2026-09-29). It answers no
# graded question. Only the condition's name moves; the sentence around it stays,
# so a reader still sees that something personal was said and withheld. The
# pattern is deliberately narrow (one condition, Latin and Persian spellings):
# widen it only with the case that needs it.
_CONDITION = re.compile(r"(?<![A-Za-z])(?:ADHD|adhd|A\.D\.H\.D\.?)(?![A-Za-z])"
                        r"|بیش[\u200c ]?فعالی(?:[\u200c ]+و[\u200c ]+نقص[\u200c ]+توجه)?")
CONDITION_PLACEHOLDER = "[health condition]"


def health_self_disclosure_changes(content: str) -> list:
    return [{"start": m.start(), "end": m.end(), "line": content.count("\n", 0, m.start()) + 1,
             "kind": "health-self-disclosure", "replacement": CONDITION_PLACEHOLDER}
            for m in _CONDITION.finditer(content)]

# -- chat-participant-identity -------------------------------------------------
# A recovered Telegram export names its participants twice over: the HTML page
# prints each sender in `<div class="from_name">`, and the archive JSON the
# session built from it carries a `"sender"` value per message (a-002, semantic
# review 2026-09-29: `identifiable_group_discussions`). No graded question reads
# a sender. Each distinct display name becomes `[PARTICIPANT_n]`, numbered by
# first appearance WITHIN THE FILE (a pure function of the file, so `verify`
# replays it; numbers are not comparable across files), and every whole-string
# mention of that full name elsewhere in the same file takes the same
# placeholder. An empty sender, an existing `[PERSON_NAME_n]` / `[PARTICIPANT_n]`
# placeholder and the trailing date span of a forwarded header are left alone.
# The same names also sit in three more structural places, all covered: the
# avatar's tooltip (`<div class="initials" ... title="...">`), the actor and the
# invitee of a service line ("<name> joined group by link", "<name> invited
# <name>"), and a salutation in message text ("Dear <Name> <Name>"). First names
# alone are never matched elsewhere: in these archives they are also ordinary
# words, and replacing them would rewrite message text.
_FROM_NAME = re.compile(r'(<div class="from_name">\s*)(?P<name>[^<\n]*?)(?=\s*(?:<span\b|</div>))')
_SENDER = re.compile(r'("sender"\s*:\s*")(?P<name>(?:[^"\\]|\\.)*)(")')
_INITIALS_TITLE = re.compile(r'(<div class="initials"[^>]*?\btitle=")(?P<name>[^"]*)(")')
_SERVICE_ACTOR = re.compile(
    r'(<div class="body details">[ \t]*\r?\n?[ \t]*)(?P<name>[^<\n]+?)'
    r'(?=[ \t]+(?:joined group by link from|joined group|joined the group|left the group|invited|removed|pinned'
    r'|changed group|changed the group|created group|converted|set the|deleted)\b)')
_SERVICE_INVITEE = re.compile(r'(<div class="body details">\s*[^<\n]*?\binvited[ \t]+)(?P<name>[^<\n]+?)(?=[ \t]*(?:\r?\n|<))')
_SALUTATION = re.compile(
    r'\b(?:Dear|Hi|Hello|Hey|Thanks|Thank you)[ \t]+'
    r'(?P<name>[A-Z][a-z]{2,}(?:[ \t]+[A-Z][a-z]{2,})?)(?![a-z])')
_NOT_A_NAME = {"Customer", "Customers", "Team", "Support", "Sir", "Madam", "Friend", "Friends", "All",
               "Everyone", "Colleague", "Colleagues", "Preply", "User", "Users", "Tutor", "Tutors",
               "Teacher", "Teachers", "Student", "Students", "Admin", "Guys", "There", "You", "Again"}
_EXISTING = re.compile(r"^\[(?:PERSON_NAME|PARTICIPANT)(?:_\d+)?\]$")


def chat_participant_changes(content: str) -> list:
    order: dict[str, str] = {}
    spans = []
    for pattern in (_FROM_NAME, _SENDER, _INITIALS_TITLE, _SERVICE_ACTOR, _SERVICE_INVITEE):
        for m in pattern.finditer(content):
            name = m.group("name").strip()
            if not name or _EXISTING.match(name):
                continue
            start = m.start("name") + (len(m.group("name")) - len(m.group("name").lstrip()))
            spans.append((start, start + len(name), name))
    for m in _SALUTATION.finditer(content):
        words = m.group("name").split()
        while words and words[-1] in _NOT_A_NAME:
            words.pop()
        if words and words[0] not in _NOT_A_NAME:
            name = " ".join(words)
            spans.append((m.start("name"), m.start("name") + len(name), name))
    spans = sorted(set(spans))
    for start, _, name in sorted(spans):
        order.setdefault(name, f"[PARTICIPANT_{len(order) + 1}]")
    taken = {(s, e) for s, e, _ in spans}
    changes = [{"start": s, "end": e, "line": content.count("\n", 0, s) + 1,
                "kind": "chat-participant-identity", "replacement": order[n]} for s, e, n in spans]
    for name, placeholder in order.items():
        if len(name) < 4:
            continue
        for m in re.finditer(r"(?<![^\W_])" + re.escape(name) + r"(?![^\W_])", content):
            if not any(s <= m.start() < e for s, e in taken):
                changes.append({"start": m.start(), "end": m.end(),
                                "line": content.count("\n", 0, m.start()) + 1,
                                "kind": "chat-participant-identity", "replacement": placeholder})
    return changes

# -- chat-handle -------------------------------------------------------------------
# Participants also address each other by Telegram username ("@someone", and the
# same name inside a `t.me/someone` link), a stable identifier of the person
# (a-002). Each distinct @handle becomes `@participant_n`, numbered by first
# appearance within the file, and a `t.me/<handle>` link takes the same
# pseudonym only when that handle is @-mentioned in the file: a channel's own
# post links (`t.me/<channel>/<id>`) name the organisation, not a person, and stay.
# An e-mail address is not a handle (the character before "@" must not be a word
# character, a dot, "@" or "/").
_HANDLE = re.compile(r"(?<![\w.@/])@(?P<h>[A-Za-z][A-Za-z0-9_]{4,31})\b")
_TME = re.compile(r"(?<=t\.me/)(?P<h>[A-Za-z][A-Za-z0-9_]{4,31})\b")


def chat_handle_changes(content: str) -> list:
    order: dict[str, str] = {}
    changes = []
    for m in _HANDLE.finditer(content):
        key = m.group("h").lower()
        order.setdefault(key, f"participant_{len(order) + 1}")
        changes.append({"start": m.start("h"), "end": m.end("h"), "line": content.count("\n", 0, m.start()) + 1,
                        "kind": "chat-handle", "replacement": order[key]})
    for m in _TME.finditer(content):
        key = m.group("h").lower()
        if key in order:
            changes.append({"start": m.start("h"), "end": m.end("h"), "line": content.count("\n", 0, m.start()) + 1,
                            "kind": "chat-handle", "replacement": order[key]})
    return changes

# -- contact-number ------------------------------------------------------------
# A participant posted a personal mobile number (a-002: `09...` in message text
# and in `tel:` links of the HTML export). It answers no graded question. Iranian
# mobile numbers in national (09 + 9 digits) and international (+98 9.. / 0098 9..)
# form become one placeholder, including inside a `tel:` link.
_PHONE = re.compile(r"(?<![\d+])(?:0|\+98[ \t-]?|0098[ \t-]?)9\d{2}[ \t-]?\d{3}[ \t-]?\d{4}(?!\d)")
PHONE_PLACEHOLDER = "[PHONE_NUMBER]"


def contact_number_changes(content: str) -> list:
    return [{"start": m.start(), "end": m.end(), "line": content.count("\n", 0, m.start()) + 1,
             "kind": "contact-number", "replacement": PHONE_PLACEHOLDER}
            for m in _PHONE.finditer(content)]

# -- meeting-link --------------------------------------------------------------
# A reusable video-meeting join link recurs across a group's messages (a-002,
# `unnecessary_contact_and_meeting_access`): anyone holding it can join. Google
# Meet, Zoom and Teams join links become one placeholder, query string included;
# the surrounding text and markup stay.
_MEETING = re.compile(
    r"https?://(?:meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}"
    r"|(?:[\w-]+\.)?zoom\.us/j/\d+"
    r"|teams\.microsoft\.com/l/meetup-join/[^\s\"'<>]+)"
    r"(?:\?[^\s\"'<>]*)?")
MEETING_PLACEHOLDER = "[MEETING_LINK]"


def meeting_link_changes(content: str) -> list:
    return [{"start": m.start(), "end": m.end(), "line": content.count("\n", 0, m.start()) + 1,
             "kind": "meeting-link", "replacement": MEETING_PLACEHOLDER}
            for m in _MEETING.finditer(content)]

# -- hospital-stay-disclosure -----------------------------------------------------
# A participant tells the group they are in, or have just left, hospital (a-002:
# four Persian messages naming بیمارستان). The disclosure answers no graded
# question, and the words around it (admitted, discharged, the bill) are the
# disclosure itself, so the whole message text goes, not a word: a JSON
# `"text"` value, or the body of an HTML `<div class="text">`, that names a
# hospital becomes a fixed note. The record, its sender field, date and id stay,
# so every count over records is unchanged. Text that never names a hospital is
# never touched (`بستری` alone also means "a platform" in these files).
_HOSPITAL = "بیمارستان"
_JSON_TEXT = re.compile(r'("text"\s*:\s*")(?P<body>(?:[^"\\]|\\.)*)(")')
_HTML_TEXT = re.compile(r'(<div class="text">)(?P<body>.*?)(</div>)', re.S)
HOSPITAL_PLACEHOLDER = "[personal health message withheld]"


def hospital_stay_changes(content: str) -> list:
    changes = []
    for pattern in (_JSON_TEXT, _HTML_TEXT):
        for m in pattern.finditer(content):
            if _HOSPITAL in m.group("body"):
                changes.append({"start": m.start("body"), "end": m.end("body"),
                                "line": content.count("\n", 0, m.start("body")) + 1,
                                "kind": "hospital-stay-disclosure", "replacement": HOSPITAL_PLACEHOLDER})
    return changes

# -- course-lecturer-name ----------------------------------------------------
# A recovered course handout names its lecturer ("محاضر المادة/د.<name>"), and a
# scenario that invents the course's conduct would then pin that conduct on a
# real person (a-067, semantic review 2026-09-27). The name answers no graded
# question. Anchored on the lecturer label, so nothing else in the file moves:
# the label, the separator and any academic title stay; the name becomes a role
# placeholder.
_LECTURER = re.compile(
    r"(?P<label>(?:محاضر|أستاذ|مدرس|مدرّس)\s+المادة|\b(?:Course\s+)?(?:Lecturer|Instructor)\b)"
    r"(?P<sep>[ \t]*[:/\-–][ \t]*)"
    r"(?P<title>(?:أ\.[ \t]?د\.|د\.|الدكتور|الأستاذ|Dr\.?|Prof\.?)[ \t]*)?"
    r"(?P<name>[^\s\d()،,:;/\[\]{}<>|*]+(?:[ \t]+[^\s\d()،,:;/\[\]{}<>|*]+){0,3})",
    re.IGNORECASE)
LECTURER_PLACEHOLDER = {"ar": "[اسم المحاضر]", "en": "[lecturer name]"}


def lecturer_name_changes(content: str) -> list:
    changes = []
    for m in _LECTURER.finditer(content):
        arabic = not m.group("label").isascii()
        changes.append({"start": m.start("name"), "end": m.end("name"),
                        "line": content.count("\n", 0, m.start()) + 1,
                        "kind": "course-lecturer-name",
                        "replacement": LECTURER_PLACEHOLDER["ar" if arabic else "en"]})
    return changes

# -- person-name-example -----------------------------------------------------
# A recovered design document illustrates a memory feature with a real person:
# the dump's own redaction replaced the name with [PERSON_NAME_n] in the prose
# sentence it came from, but left it in the worked examples -- a JSON sample's
# "person_name", an SQL comment, a prompt template -- and every sentence that
# re-quotes them (a-001, semantic review 2026-09-28: a relative's given name,
# relation and death year). Anchored on the example's own label: a value of a
# `person_name` / `person` key (JSON, dict literal, SQL comparison or the SQL
# column's trailing comment) is a person-name example; that name, and each
# whole-word mention of it elsewhere in the same file, becomes the file's
# placeholder. Nothing else moves. A value that is already a placeholder, or is
# not a word of letters (None, null, `...`), is left alone.
_PERSON_KEY = re.compile(
    r"""(?P<key>\bperson(?:_name)?\b)"""
    r"""(?:[\"']?[ \t]*(?:[:=]|==)[ \t]*|[ \t]+TEXT\b[^\n]*?--[ \t]*)"""
    r"""(?P<q>[\"'])(?P<name>[^\"'\n]{1,60})(?P=q)""")
_LETTERS = re.compile(r"^[^\W\d_]+(?:[ \t][^\W\d_]+){0,2}$")
_PLACEHOLDER = re.compile(r"\[PERSON_NAME(?:_(\d+))?\]")
_DIACRITICS = re.compile(r"[ً-ْٰ]")


def person_example_changes(content: str) -> list:
    names = []
    for m in _PERSON_KEY.finditer(content):
        name = m.group("name").strip()
        if _LETTERS.match(name) and not _PLACEHOLDER.search(name) and name.lower() not in {"none", "null", "unknown"}:
            if name not in names:
                names.append(name)
    if not names:
        return []
    indices = {m.group(0) for m in _PLACEHOLDER.finditer(content)}
    replacement = indices.pop() if len(indices) == 1 else "[PERSON_NAME]"
    changes = []
    for name in names:
        # Whole word: no letter (or Arabic diacritic) on either side.
        for m in re.finditer(r"(?<![^\W\d_])" + re.escape(name) + r"(?![^\W\d_]|[ً-ْٰ])", content):
            changes.append({"start": m.start(), "end": m.end(),
                            "line": content.count("\n", 0, m.start()) + 1,
                            "kind": "person-name-example", "replacement": replacement})
    return changes

# -- client-body-profile -----------------------------------------------------
# A recovered coaching programme prints its client's body profile as one
# "·"-separated run -- "47 ans · 92 kg · Prothèse genou droit · 200g
# protéines/jour non négociable" -- in a header or footer line (a-013/a-020,
# semantic review 2026-09-29). Age, weight, height and a joint condition answer
# no graded question; the rule that follows them (the protein floor) may.
# Anchored on the run itself: it must open with an age ("NN ans") followed by a
# weight ("NN kg"), may carry a height ("1m58") and one joint-condition item
# (Prothèse/Arthrose ... genou|hanche|épaule ...), and must be followed by a
# separator. Only that run becomes the placeholder; the separator and every
# following item (e.g. the protein rule) stay byte-identical.
_BODY_PROFILE = re.compile(
    r"(?<![\w])(?P<run>\d{2}[ \t]?ans[ \t]*·[ \t]*\d{2,3}(?:[.,]\d)?[ \t]?kg"
    r"(?:[ \t]*·[ \t]*\d[m.,]\d{2}(?:[ \t]?m)?)?"
    r"(?:[ \t]*·[ \t]*(?:Proth[èe]se|Arthrose|Tendinite|Hernie)[ \t]+"
    r"(?:du[ \t]+|de[ \t]+la[ \t]+|de[ \t]+l'|d')?"
    r"(?:genou|hanche|épaule|epaule|dos|cheville|poignet|coude)s?"
    r"(?:[ \t]+(?:droit|gauche|droite)s?)?)?)"
    r"(?P<sep>[ \t]*·[ \t]*)", re.IGNORECASE)
BODY_PROFILE_PLACEHOLDER = "[profil client retiré]"
# The same programme also points at the joint in its advice ("Important :
# surveiller énergie et genou."). A second review (2026-09-29) flagged that
# pointer once the profile run was gone. Anchored on "surveiller <item> et
# <joint>" ending the clause: only " et <joint>" is removed, so the advice keeps
# its first item and its punctuation.
_JOINT_WATCH = re.compile(
    r"(?P<head>\bsurveiller[ \t]+[^\s.,;:<]+)"
    r"(?P<tail>[ \t]+et[ \t]+(?:(?:le|la|les)[ \t]+|l['’])?"
    r"(?:genou|hanche|épaule|epaule|cheville|coude|poignet|dos)s?)(?=[ \t]*[.,;:<])",
    re.IGNORECASE)


def client_profile_changes(content: str) -> list:
    changes = []
    for m in _BODY_PROFILE.finditer(content):
        changes.append({"start": m.start("run"), "end": m.end("run"),
                        "line": content.count("\n", 0, m.start()) + 1,
                        "kind": "client-body-profile",
                        "replacement": BODY_PROFILE_PLACEHOLDER})
    for m in _JOINT_WATCH.finditer(content):
        changes.append({"start": m.start("tail"), "end": m.end("tail"),
                        "line": content.count("\n", 0, m.start()) + 1,
                        "kind": "client-body-profile", "replacement": ""})
    return changes

# -- network-device-identifiers --------------------------------------------
# A recovered SNMP walk carries the client MACs of a real network (as SNMP
# Hex-STRING values and as six-octet OID index suffixes), the controller's
# private address, the shell prompt's host and directory, and the SNMP user.
# a-062 (build 2026-09-26) was blocked on exactly that and no policy could clear
# it: recovered files are read-only to the author. Pseudonyms are a pure
# function of the file's content, so `verify` replays them exactly: MACs map
# into the RFC 7042 documentation block 00-00-5E-00-53-00/24 and private IPv4
# into TEST-NET-1 (192.0.2.0/24), one real value to one pseudonym in every form
# within a file. Placeholders (all-equal bytes, AA:BB:CC:DD:EE:FF ...) stay.
_HEX6 = re.compile(r"(?<=Hex-STRING:)(\s*)((?:[0-9A-Fa-f]{2}\s){5}[0-9A-Fa-f]{2})")
_OID_MAC = re.compile(r"(?<=\d\.)(\d{1,3}(?:\.\d{1,3}){5})(?=\s*=\s*Hex-STRING:\s*((?:[0-9A-Fa-f]{2}\s){5}[0-9A-Fa-f]{2}))")
_DEC6 = re.compile(r"(?<![\d.])\.?(\d{1,3}(?:\.\d{1,3}){5})(?![\d.])")
_COLON_MAC = re.compile(r"(?<![0-9A-Fa-f:-])[0-9A-Fa-f]{2}([:-])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){4}(?![0-9A-Fa-f:-])")
# Two more spellings a Fable review found surviving in a-062's poller: a bare
# quoted hex string ("00 17 C8 D2 60 4D") and a Python octet list
# ([0,23,200,210,96,77]).
_BARE_HEX6 = re.compile(r"(?<![0-9A-Fa-f])((?:[0-9A-Fa-f]{2} ){5}[0-9A-Fa-f]{2})(?![0-9A-Fa-f])")
_INT_LIST6 = re.compile(r"\[\s*((?:\d{1,3}\s*,\s*){5}\d{1,3})\s*\]")
_PRIVATE_V4 = re.compile(r"(?<![\d.])(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}(?![\d.])")
_PROMPT = re.compile(r"([A-Za-z0-9._-]*)@([A-Za-z0-9._-]+):([~/][^\s$#\"\\]*)([$#])(?=\s)")
# The value is a literal name, never a format placeholder or variable (`%s`, `$USER`, `{u}`).
_SNMP_USER = re.compile(r"(?<![A-Za-z])(user|securityName|secName)=([^\s,)\"\\%${<][^\s,)\"\\]*)")
_PLACEHOLDER_MACS = {bytes.fromhex(h) for h in (
    "aabbccddeeff", "001122334455", "112233445566", "0123456789ab", "123456789abc")}
_DOC_MAC_PREFIX = bytes.fromhex("00005e0053")


def _logical_line(content: str, index: int) -> str:
    starts = [content.rfind(sep, 0, index) + len(sep) for sep in ("\n", "\\n")]
    ends = [e for e in (content.find("\n", index), content.find("\\n", index)) if e != -1]
    return content[max(starts):min(ends) if ends else len(content)]


def network_identifier_changes(content: str) -> list:
    """Typed, content-derived edits for network-device identifiers."""
    macs: dict[bytes, int] = {}
    ips: dict[str, int] = {}

    def mac_slot(raw: bytes) -> int:
        if raw not in macs:
            slot = hashlib.sha256(b"arena-mac:" + raw).digest()[0]
            while slot in macs.values():
                slot = (slot + 1) % 256
            macs[raw] = slot
        return macs[raw]

    def keep(raw: bytes) -> bool:
        return len(set(raw)) == 1 or raw in _PLACEHOLDER_MACS or raw.startswith(_DOC_MAC_PREFIX)

    def pseudo(raw: bytes) -> bytes:
        return _DOC_MAC_PREFIX + bytes([mac_slot(raw)])

    changes = []

    def add(start, end, kind_value):
        changes.append({"start": start, "end": end, "line": content.count("\n", 0, start) + 1,
                        "kind": "network-device-identifiers", "replacement": kind_value})

    for m in _HEX6.finditer(content):
        raw = bytes(int(x, 16) for x in m.group(2).split())
        if not keep(raw):
            add(m.start(2), m.end(2), " ".join(f"{b:02X}" for b in pseudo(raw)))
    for m in _OID_MAC.finditer(content):
        octets = [int(x) for x in m.group(1).split(".")]
        raw = bytes(int(x, 16) for x in m.group(2).split())
        if all(o < 256 for o in octets) and bytes(octets) == raw and not keep(raw):
            add(m.start(1), m.end(1), ".".join(str(b) for b in pseudo(raw)))
    taken = [(c["start"], c["end"]) for c in changes]
    for m in _DEC6.finditer(content):
        octets = [int(x) for x in m.group(1).split(".")]
        if (all(o < 256 for o in octets) and not keep(bytes(octets))
                and not any(s < m.end(1) and m.start(1) < e for s, e in taken)):
            add(m.start(1), m.end(1), ".".join(str(b) for b in pseudo(bytes(octets))))
    taken = [(c["start"], c["end"]) for c in changes]
    for m in _BARE_HEX6.finditer(content):
        raw = bytes(int(x, 16) for x in m.group(1).split())
        if not keep(raw) and not any(s < m.end(1) and m.start(1) < e for s, e in taken):
            add(m.start(1), m.end(1), " ".join(f"{b:02X}" for b in pseudo(raw)))
    for m in _INT_LIST6.finditer(content):
        octets = [int(x) for x in re.split(r"\s*,\s*", m.group(1).strip())]
        if all(o < 256 for o in octets) and not keep(bytes(octets)):
            sep = ", " if ", " in m.group(1) else ","
            add(m.start(1), m.end(1), sep.join(str(b) for b in pseudo(bytes(octets))))
    for m in _COLON_MAC.finditer(content):
        raw = bytes(int(x, 16) for x in re.split(r"[:-]", m.group(0)))
        if not keep(raw):
            sep, upper = m.group(1), m.group(0)[0:2].isupper() or m.group(0)[0:2].isdigit()
            add(m.start(), m.end(), sep.join((f"{b:02X}" if upper else f"{b:02x}") for b in pseudo(raw)))
    for m in _PRIVATE_V4.finditer(content):
        if m.group(0) not in ips:
            n = 1 + int.from_bytes(hashlib.sha256(b"arena-ipv4:" + m.group(0).encode()).digest()[:2]) % 254
            while n in ips.values():
                n = n % 254 + 1
            ips[m.group(0)] = n
        add(m.start(), m.end(), f"192.0.2.{ips[m.group(0)]}")
    for m in _PROMPT.finditer(content):
        add(m.start(), m.end(), f"{'user' if m.group(1) else ''}@host:~/work{m.group(4)}")
    for m in _SNMP_USER.finditer(content):
        if "snmp" in _logical_line(content, m.start()).lower():
            add(m.start(2), m.end(2), "snmp-user")
    return changes


def transform(content: str, kinds: list) -> tuple[str, list]:
    if (not isinstance(kinds, list) or not kinds or any(not isinstance(kind, str) for kind in kinds)
            or len(set(kinds)) != len(kinds)
            or any(kind not in KINDS for kind in kinds)):
        raise ValueError("unsupported or repeated redaction kind")
    changes = []
    if 'web-access-default-metadata' in kinds:
        for start, end, replacement in web_access_default_spans(content):
            changes.append({'start': start, 'end': end,
                'line': content.count('\n', 0, start) + 1,
                'kind': 'web-access-default-metadata', 'replacement': replacement})
    if "health-absence-metadata" in kinds:
        for start, end in health_absence_spans(content):
            changes.append({"start": start, "end": end,
                "line": content.count("\n", 0, start) + 1,
                "kind": "health-absence-metadata", "replacement": ABSENCE_NOTE})
    if "exam-attempt-metadata" in kinds:
        from .exam_privacy import changes as exam_changes
        changes.extend(exam_changes(content))
    if "exam-item-performance" in kinds:
        from .exam_privacy import item_performance_changes
        changes.extend(item_performance_changes(content))
    if "network-device-identifiers" in kinds:
        changes.extend(network_identifier_changes(content))
    if "course-lecturer-name" in kinds:
        changes.extend(lecturer_name_changes(content))
    if "person-name-example" in kinds:
        changes.extend(person_example_changes(content))
    if "client-body-profile" in kinds:
        changes.extend(client_profile_changes(content))
    if "source-code-secret-literal" in kinds:
        changes.extend(secret_literal_changes(content))
    if "health-self-disclosure" in kinds:
        changes.extend(health_self_disclosure_changes(content))
    if "chat-participant-identity" in kinds:
        changes.extend(chat_participant_changes(content))
    if "chat-handle" in kinds:
        changes.extend(chat_handle_changes(content))
    if "contact-number" in kinds:
        changes.extend(contact_number_changes(content))
    if "meeting-link" in kinds:
        changes.extend(meeting_link_changes(content))
    if "hospital-stay-disclosure" in kinds:
        changes.extend(hospital_stay_changes(content))
    if "email" in kinds:
        changes.extend(email_changes(content))
    if "ssh-access-metadata" in kinds:
        for match in ssh_endpoints(content):
            changes.append({"start": match.start(), "end": match.end(),
                "line": content.count("\n", 0, match.start()) + 1,
                "kind": "ssh-access-metadata", "replacement": SSH_EXAMPLE})
    if not changes:
        raise ValueError("redaction policy found no supported private data")
    result, cursor = [], 0
    for change in sorted(changes, key=lambda row: row["start"]):
        if change["start"] < cursor:
            raise ValueError("redaction policies overlap")
        result.extend((content[cursor:change["start"]], change["replacement"]))
        cursor = change["end"]
    result.append(content[cursor:])
    return "".join(result), changes


def verify(bundle: Path, fixture: Path, ws: rec.Workspace, session_id: str) -> dict:
    path = contained(bundle, MANIFEST)
    if not path.exists():
        return {}
    fixture = contained(bundle, fixture.relative_to(bundle).as_posix())
    raw = path.read_bytes()
    manifest = strict_json(raw.decode())
    _keys(manifest, {"schema", "files"}, "redaction manifest")
    if manifest["schema"] != SCHEMA or not isinstance(manifest["files"], list) or not manifest["files"]:
        raise ValueError("unsupported or empty privacy redaction manifest")
    verified = {}
    for row in manifest["files"]:
        _keys(row, {"path", "citation", "source_sha256", "public_sha256", "kinds"}, "redaction file")
        rel = row["path"]
        public = contained(fixture, rel)
        if PurePosixPath(rel).as_posix() != rel or rel in verified:
            raise ValueError("redaction file paths must be canonical and unique")
        source = next((revision for revision in ws.provenance_revisions()
            if row["citation"] == f"{session_id}::msg{revision.msg_index}::{revision.path}"
            and sha(revision.content.encode()) == row["source_sha256"]), None)
        if source is None:
            raise ValueError(f"{rel}: redaction source hash/citation is absent from the trusted trace")
        transformed, changes = transform(source.content, row["kinds"])
        public_bytes = public.read_bytes()
        if transformed.encode() != public_bytes or sha(public_bytes) != row["public_sha256"]:
            raise ValueError(f"{rel}: fixture differs from the verified privacy redaction")
        verified[rel] = {"citation": row["citation"], "source_sha256": row["source_sha256"],
                         "public_sha256": row["public_sha256"], "changes": changes}
    return {"manifest_sha256": sha(raw), "policy": SCHEMA, "files": verified}


def audit(bundle: Path) -> dict:
    if not contained(bundle, MANIFEST).exists():
        return {}
    spec = strict_json((bundle / "authoring/spec.json").read_text())
    session = spec["source"]["session_id"]
    fixture = next(bundle / "environment" / name for name in ("files", "fixtures")
                   if (bundle / "environment" / name).is_dir())
    return verify(bundle, fixture, rec.recover(rec.load_trace(session), rec.sessions_root()), session)


def minimize(bundle: Path, session_id: str, root: Path | None = None) -> dict:
    """Apply supported policies before authoring; never accept an unbound edit.

    Call on an extracted working draft, before building/versioning evidence.
    All sources and transforms are checked before the first file is changed.
    Unsupported private data or ambiguous source shapes stop the build.
    """
    from ..artifacts import atomic_json
    from ..privacy import scan
    bundle = bundle.resolve()
    fixture = contained(bundle, "environment/files")
    findings = scan(fixture)
    if not findings and not contained(bundle, MANIFEST).exists():
        return {}
    # Unscannable content (an image) is not something redaction can repair; it
    # is staged and stays an open privacy finding until a visual review of its
    # exact bytes is recorded (privacy.VISUAL_REVIEW). Release blocks until then.
    findings = [row for row in findings if row["kind"] != "unscannable"]
    if any(row["kind"] not in KINDS for row in findings):
        raise ValueError(f"source needs an unsupported privacy repair: {findings}")
    root = root or rec.sessions_root()
    ws = rec.recover(rec.load_trace(session_id, root), root)
    from ..dump.evidence import replay_selections
    replay_selections(ws, bundle, rec.load_trace(session_id, root), root)
    proof = verify(bundle, fixture, ws, session_id)
    if not findings:
        return proof
    manifest_path = contained(bundle, MANIFEST)
    manifest = strict_json(manifest_path.read_text()) if manifest_path.exists() else {"schema": SCHEMA, "files": []}
    by_file = {}
    for finding in findings:
        by_file.setdefault(finding["file"], set()).add(finding["kind"])
    plans = []
    for rel, kinds in sorted(by_file.items()):
        if rel in proof.get("files", {}):
            raise ValueError("existing privacy transformation needs explicit policy composition")
        path = contained(fixture, rel)
        original = path.read_bytes()
        source = next((rev for rev in reversed(ws.provenance_revisions()) if rev.content.encode() == original), None)
        if source is None:
            raise ValueError(f"{rel}: cannot minimize a fixture without an exact recovered source")
        public, _ = transform(source.content, sorted(kinds))
        plans.append((path, public.encode()))
        manifest["files"].append({"path": rel,
            "citation": f"{session_id}::msg{source.msg_index}::{source.path}",
            "source_sha256": sha(original), "public_sha256": sha(public.encode()), "kinds": sorted(kinds)})
    # Calendar and text redaction on the same source require explicit replay
    # composition, not sequential credit inferred from two unrelated proofs.
    from .anonymization import verify as verify_calendar
    calendar = verify_calendar(bundle, fixture, ws, session_id)
    if set(calendar.get("files", {})) & set(by_file):
        raise ValueError("calendar and redaction edits on the same file need explicit composition")
    for path, public in plans:
        path.write_bytes(public)
    atomic_json(manifest_path, manifest)
    remaining = scan(fixture)
    if remaining:
        raise ValueError(f"supported minimization left private material: {remaining}")
    return verify(bundle, fixture, ws, session_id)


def compose_row(row: dict, source_content: str, kinds: list) -> tuple[str, dict]:
    """Add policy kinds to a file that already carries a verified redaction.

    The public bytes are recomputed from the SAME recovered source the manifest
    row cites, under the union of its recorded kinds and the new ones, so the
    receipt stays replayable by `verify`. Refuses a composition that adds nothing.
    """
    if sha(source_content.encode()) != row["source_sha256"]:
        raise ValueError(f"{row['path']}: composition source differs from the recorded source")
    merged = sorted(set(row["kinds"]) | set(kinds))
    if merged == sorted(row["kinds"]):
        raise ValueError(f"{row['path']}: composition adds no redaction kind")
    public, _ = transform(source_content, merged)
    return public, {**row, "kinds": merged, "public_sha256": sha(public.encode())}


def apply(bundle: Path, session_id: str, paths: list, kinds: list, root: Path | None = None,
          compose: bool = False) -> dict:
    """Apply a typed policy to NAMED fixture files on explicit request.

    `minimize` acts only on what `privacy.scan` flags; a semantic reviewer can
    find private data no scan pattern covers (a-062's network identifiers), and
    the author may not edit recovered bytes. This takes the same guarantees:
    an exact recovered source per file, edits computed by the policy (never
    supplied), everything planned before the first write, a replayable manifest
    entry, the scenario receipt re-bound to the public bytes, and `verify` last.
    """
    from ..artifacts import atomic_json
    bundle = bundle.resolve()
    fixture = contained(bundle, "environment/files")
    root = root or rec.sessions_root()
    trace = rec.load_trace(session_id, root)
    ws = rec.recover(trace, root)
    from ..dump.evidence import replay_selections
    replay_selections(ws, bundle, trace, root)
    proof = verify(bundle, fixture, ws, session_id)
    manifest_path = contained(bundle, MANIFEST)
    manifest = strict_json(manifest_path.read_text()) if manifest_path.exists() else {"schema": SCHEMA, "files": []}
    plans = []
    for rel in sorted(set(paths)):
        if rel in proof.get("files", {}):
            # Explicit composition only: the caller names the file AND asks for it.
            if not compose:
                raise ValueError(f"{rel}: existing privacy transformation needs explicit policy composition")
            index = next(i for i, row in enumerate(manifest["files"]) if row["path"] == rel)
            row = manifest["files"][index]
            source = next((rev for rev in ws.provenance_revisions()
                           if row["citation"] == f"{session_id}::msg{rev.msg_index}::{rev.path}"
                           and sha(rev.content.encode()) == row["source_sha256"]), None)
            if source is None:
                raise ValueError(f"{rel}: redaction source hash/citation is absent from the trusted trace")
            public, manifest["files"][index] = compose_row(row, source.content, kinds)
            plans.append((rel, contained(fixture, rel), public.encode()))
            continue
        path = contained(fixture, rel)
        original = path.read_bytes()
        source = next((rev for rev in reversed(ws.provenance_revisions()) if rev.content.encode() == original), None)
        if source is None:
            raise ValueError(f"{rel}: cannot redact a fixture without an exact recovered source")
        public, _ = transform(source.content, sorted(kinds))
        plans.append((rel, path, public.encode()))
        manifest["files"].append({"path": rel,
            "citation": f"{session_id}::msg{source.msg_index}::{source.path}",
            "source_sha256": sha(original), "public_sha256": sha(public.encode()), "kinds": sorted(kinds)})
    from .anonymization import verify as verify_calendar
    if set(verify_calendar(bundle, fixture, ws, session_id).get("files", {})) & {rel for rel, _, _ in plans}:
        raise ValueError("calendar and redaction edits on the same file need explicit composition")
    from ..author.scenario import MANIFEST as SCENARIO_MANIFEST, verify as verify_scenario
    scenario_path = contained(bundle, SCENARIO_MANIFEST)
    scenario = strict_json(scenario_path.read_text()) if scenario_path.exists() else None
    if scenario is not None:
        verify_scenario(bundle)
    before = {rel: path.read_bytes() for rel, path, _ in plans}
    scenario_raw = scenario_path.read_bytes() if scenario is not None else None
    manifest_raw = manifest_path.read_bytes() if manifest_path.exists() else None
    try:
        for rel, path, public in plans:
            path.write_bytes(public)
            if scenario is not None and rel in scenario["base"]:
                scenario["base"][rel] = {"sha256": sha(public), "bytes": len(public)}
        atomic_json(manifest_path, manifest)
        if scenario is not None:
            atomic_json(scenario_path, scenario)
            verify_scenario(bundle)
        return verify(bundle, fixture, ws, session_id)
    except Exception:
        for rel, path, _ in plans:
            path.write_bytes(before[rel])
        if scenario_raw is not None:
            scenario_path.write_bytes(scenario_raw)
        if manifest_raw is None:
            manifest_path.unlink(missing_ok=True)
        else:
            manifest_path.write_bytes(manifest_raw)
        raise


def combine(*proofs: dict) -> dict:
    active = [proof for proof in proofs if proof]
    if not active:
        return {}
    if len(active) == 1:
        return active[0]
    files = {}
    for proof in active:
        if set(files) & set(proof["files"]):
            raise ValueError("multiple privacy policies on the same file need an explicit composition policy")
        files.update(proof["files"])
    import json
    manifests = [{key: proof[key] for key in ("policy", "manifest_sha256")} for proof in active]
    return {"policy": "arena-pipeline/privacy-composition/1", "files": files,
            "manifest_sha256": hashlib.sha256(json.dumps(manifests, sort_keys=True).encode()).hexdigest()}
