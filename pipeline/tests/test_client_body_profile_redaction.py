"""client-body-profile: a coaching programme's one-line client body profile is
replaced by a placeholder; the rule that follows it (a protein floor) stays."""
import unittest

from pipeline.ledger.redaction import KINDS, client_profile_changes, transform, BODY_PROFILE_PLACEHOLDER


FOOTER = ('<div class="footer-note">47 ans · 92 kg · Prothèse genou droit · '
          '200g protéines/jour non négociable</div>')


class ClientBodyProfile(unittest.TestCase):
    def test_kind_is_registered(self):
        self.assertIn("client-body-profile", KINDS)

    def test_profile_run_becomes_placeholder_and_rule_stays(self):
        out, changes = transform(FOOTER, ["client-body-profile"])
        self.assertEqual(out, '<div class="footer-note">' + BODY_PROFILE_PLACEHOLDER
                         + ' · 200g protéines/jour non négociable</div>')
        self.assertEqual(len(changes), 1)
        self.assertNotIn("92 kg", out)
        self.assertNotIn("Prothèse", out)

    def test_height_and_condition_variant(self):
        text = "41 ans · 65 kg · 1m58 · Arthrose genou droit · 115–125g protéines/jour"
        out, _ = transform(text, ["client-body-profile"])
        self.assertEqual(out, BODY_PROFILE_PLACEHOLDER + " · 115–125g protéines/jour")

    def test_age_without_weight_or_a_load_is_not_a_profile(self):
        for text in ("Non négociable à 41 ans avec arthrose",
                     "Semaine 4   63–64 kg  Taille en baisse",
                     "3 × 8–12  2 × 8–12 kg  Genoux légèrement fléchis",
                     "47 ans · Cruise Ready"):
            self.assertEqual(client_profile_changes(text), [], text)

    def test_needs_a_following_separator(self):
        self.assertEqual(client_profile_changes("47 ans · 92 kg"), [])

    def test_replay_is_deterministic(self):
        self.assertEqual(transform(FOOTER, ["client-body-profile"]),
                         transform(FOOTER, ["client-body-profile"]))

    def test_joint_watch_pointer_is_removed(self):
        text = "C'est la semaine de déficit le plus profond. Important : surveiller énergie et genou. Si fatigue"
        out, changes = transform(text, ["client-body-profile"])
        self.assertEqual(out, "C'est la semaine de déficit le plus profond. Important : surveiller énergie. Si fatigue")
        self.assertEqual(len(changes), 1)

    def test_joint_word_elsewhere_is_left_alone(self):
        for text in ("Genoux légèrement fléchis · Hanches vers l'arrière",
                     "surveiller énergie et sommeil.", "renforcer autour du genou sans agression"):
            self.assertEqual(client_profile_changes(text), [], text)


if __name__ == "__main__":
    unittest.main()
