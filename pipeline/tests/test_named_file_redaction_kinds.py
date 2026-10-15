"""Typed redaction kinds added 2026-09-29 for semantic-review privacy findings that
no existing kind covered: a hard-coded secret literal (a-015), a named health
self-disclosure (a-017), and a Telegram export's participant names, phone numbers,
meeting links and hospital-stay messages (a-002). Each is a pure function of the
file's content (replayed by `verify`), applied only to NAMED files through
`redaction.apply`, and moves nothing but the private value."""
import json
import unittest

from pipeline.ledger.redaction import (
    HOSPITAL_PLACEHOLDER, KINDS, MEETING_PLACEHOLDER, PHONE_PLACEHOLDER, SECRET_PLACEHOLDER,
    CONDITION_PLACEHOLDER, transform)


class SecretLiteral(unittest.TestCase):
    def test_only_the_literal_moves(self):
        src = 'local SECRET_SALT = "k3y-S4lt-9x"\nlocal SAVE_VERSION = "1.2.0"\n'
        out, changes = transform(src, ["source-code-secret-literal"])
        self.assertEqual(out, f'local SECRET_SALT = "{SECRET_PLACEHOLDER}"\nlocal SAVE_VERSION = "1.2.0"\n')
        self.assertEqual(len(changes), 1)

    def test_names_that_do_not_say_secret_are_left(self):
        with self.assertRaises(ValueError):
            transform('local SAVE_VERSION = "1.2.0"\nlocal PLAYER = "abcd"\n', ["source-code-secret-literal"])


class HealthSelfDisclosure(unittest.TestCase):
    def test_latin_and_persian_forms(self):
        out, changes = transform("I have ADHD, so deadlines matter. بیش‌فعالی دارم.", ["health-self-disclosure"])
        self.assertNotIn("ADHD", out)
        self.assertNotIn("فعالی", out)
        self.assertEqual(out.count(CONDITION_PLACEHOLDER), 2)
        self.assertEqual(len(changes), 2)

    def test_letters_inside_a_word_are_not_a_mention(self):
        with self.assertRaises(ValueError):
            transform("sadhd adhdx", ["health-self-disclosure"])


HTML = ('<div class="from_name">\nAlex Morgan\n       </div>\n<div class="text"> hi team </div>\n'
        '<div class="from_name">\n[PERSON_NAME_3] Doemer <span class="date details" title="x"> 1</span>\n</div>\n'
        '<div class="from_name">\n[PERSON_NAME_2]\n       </div>\n'
        '<div class="from_name">\nAlex Morgan\n       </div>\n<div class="text"> thanks Alex Morgan </div>\n')
ARCHIVE = json.dumps({"telegramArchive": [
    {"sender": "Alex Morgan", "text": "call me 09121234567 or join https://meet.google.com/abc-defg-hij"},
    {"sender": "", "text": "channel post"},
    {"sender": "[PERSON_NAME_2]", "text": "من بیمارستان بستری شدم"},
    {"sender": "Sam Lee", "text": "Preply بستری ایده‌آل است"}]}, ensure_ascii=False, indent=1)


class ChatParticipantIdentity(unittest.TestCase):
    def test_html_names_numbered_by_first_appearance(self):
        out, _ = transform(HTML, ["chat-participant-identity"])
        self.assertNotIn("Alex Morgan", out)
        self.assertNotIn("Doemer", out)
        self.assertEqual(out.count("[PARTICIPANT_1]"), 3)     # two headers + one full-name mention
        self.assertIn("[PARTICIPANT_2]", out)                 # placeholder-plus-surname value
        self.assertIn("[PERSON_NAME_2]", out)                 # an existing placeholder stays
        self.assertIn('<span class="date details" title="x"> 1</span>', out)

    def test_json_senders_and_empty_sender(self):
        out, _ = transform(ARCHIVE, ["chat-participant-identity"])
        data = json.loads(out)["telegramArchive"]
        self.assertEqual([m["sender"] for m in data], ["[PARTICIPANT_1]", "", "[PERSON_NAME_2]", "[PARTICIPANT_2]"])

    def test_replay_is_deterministic(self):
        self.assertEqual(transform(HTML, ["chat-participant-identity"]), transform(HTML, ["chat-participant-identity"]))

    def test_avatar_title_service_lines_and_salutations(self):
        src = ('<div class="initials" style="line-height: 20px" title="Kim Novak">\nK\n</div>\n'
               '<div class="body details">\nRiver Stone joined group by link from Group\n</div>\n'
               '<div class="body details">\n[PERSON_NAME_2] invited Elena Park\n</div>\n'
               '<div class="body details">\n[PERSON_NAME_2] pinned <a href="#go_to_message5">this message</a>\n</div>\n'
               '<div class="text"> Dear Maria Lopez, thanks. Dear Customer, hi Team. </div>\n')
        out, _ = transform(src, ["chat-participant-identity"])
        for leaked in ("Kim Novak", "River Stone", "Elena Park", "Maria Lopez"):
            self.assertNotIn(leaked, out)
        self.assertIn("[PERSON_NAME_2] pinned", out)          # service verb and placeholder stay
        self.assertIn("Dear Customer, hi Team.", out)          # not-a-name salutations stay
        self.assertIn(">\nK\n</div>", out)                    # the single initial stays


class ChatHandle(unittest.TestCase):
    def test_handles_and_their_links_share_a_pseudonym(self):
        src = ('ask @river_stone or <a href="https://t.me/river_stone">@river_stone</a>; '
               'channel post https://t.me/PreplyNews/123; mail a.b@example.org; @Kim_Novak_1 thanks')
        out, _ = transform(src, ["chat-handle"])
        self.assertNotIn("river_stone", out)
        self.assertEqual(out.count("participant_1"), 3)
        self.assertIn("@participant_2 thanks", out)
        self.assertIn("t.me/PreplyNews/123", out)       # a channel link that is never @-mentioned stays
        self.assertIn("a.b@example.org", out)           # an e-mail address is not a handle


class ContactMeetingHospital(unittest.TestCase):
    def test_composed_kinds_leave_valid_json_and_counts(self):
        kinds = ["chat-participant-identity", "contact-number", "meeting-link", "hospital-stay-disclosure"]
        out, _ = transform(ARCHIVE, kinds)
        data = json.loads(out)["telegramArchive"]
        self.assertEqual(len(data), 4)
        self.assertIn(PHONE_PLACEHOLDER, data[0]["text"])
        self.assertIn(MEETING_PLACEHOLDER, data[0]["text"])
        self.assertEqual(data[2]["text"], HOSPITAL_PLACEHOLDER)
        self.assertEqual(data[3]["text"], "Preply بستری ایده‌آل است")   # 'platform' sense stays

    def test_tel_link_and_international_forms(self):
        src = '<a href="tel:09121234567">09121234567</a> +98 912 123 4567 order #0912345'
        out, changes = transform(src, ["contact-number"])
        self.assertEqual(out.count(PHONE_PLACEHOLDER), 3)
        self.assertIn("order #0912345", out)

    def test_meeting_links_with_query(self):
        src = "join https://meet.google.com/abc-defg-hij?authuser=0 or https://us02web.zoom.us/j/123456789?pwd=x ok"
        out, _ = transform(src, ["meeting-link"])
        self.assertEqual(out, f"join {MEETING_PLACEHOLDER} or {MEETING_PLACEHOLDER} ok")

    def test_html_text_div_with_hospital_is_withheld_whole(self):
        src = '<div class="text"> درود <br>من بیمارستان بستری شدم </div><div class="text"> سلام </div>'
        out, _ = transform(src, ["hospital-stay-disclosure"])
        self.assertEqual(out, f'<div class="text">{HOSPITAL_PLACEHOLDER}</div><div class="text"> سلام </div>')

    def test_kinds_are_registered(self):
        for kind in ("source-code-secret-literal", "health-self-disclosure", "chat-participant-identity", "chat-handle",
                     "contact-number", "meeting-link", "hospital-stay-disclosure",
                     "client-body-profile", "exam-item-performance"):
            self.assertIn(kind, KINDS)


if __name__ == "__main__":
    unittest.main()
