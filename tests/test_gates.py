"""Deterministic gate tests. Run: python3 -m unittest discover -s tests -v"""
import json
import unittest
from datetime import datetime, timedelta, timezone
from helpers import Sandbox, MEDSPA_NUMBER


class GateTests(unittest.TestCase):
    def setUp(self):
        self.s = Sandbox()

    def tearDown(self):
        self.s.close()

    def precheck(self, path):
        return self.s.script("precheck.py", path)

    def test_good_medspa_draft_clears(self):
        code, out = self.precheck(self.s.draft())
        self.assertEqual(code, 0, out)
        self.assertIn("CLEARED", out)

    def test_missing_marker_blocks(self):
        p = self.s.draft(body="Hi [[MISSING: owner name]], quick note about calls.")
        code, out = self.precheck(p)
        self.assertEqual(code, 2)
        self.assertIn("placeholder_scan", out)

    def test_curly_placeholder_blocks(self):
        code, out = self.precheck(self.s.draft(subject="{{company}} calls"))
        self.assertEqual(code, 2)

    def test_medspa_number_on_dealer_draft_blocks(self):
        p = self.s.draft(lead="lone-star-motors", vertical="dealers", campaign_id="dealers-test",
                         recipient="sales@lonestarmotors.com")
        code, out = self.s.script("demo_number_check.py", p)
        self.assertEqual(code, 2, out)
        self.assertIn("wrong vertical", out)

    def test_unknown_vertical_with_number_blocks(self):
        p = self.s.draft(vertical="", campaign_id="first-touch-2026-07")
        code, out = self.s.script("demo_number_check.py", p)
        self.assertEqual(code, 2)
        self.assertIn("vertical is unknown", out)

    def test_vertical_resolved_from_index(self):
        self.s.index(**{"aurora-medspa": {"vertical": "medspa", "state": "drafting"}})
        p = self.s.draft(vertical="", campaign_id="first-touch-2026-07")
        code, out = self.s.script("demo_number_check.py", p)
        self.assertEqual(code, 0, out)

    def test_number_free_dealer_draft_passes(self):
        p = self.s.draft(lead="lone-star-motors", vertical="dealers", recipient="sales@lonestarmotors.com",
                         body="Hi,\n\nYour lot closes at 7pm but your listings ship nationwide, so a "
                              "buyer in Ohio asking about the 2019 911 at 10pm waits until morning. I build "
                              "an agent that answers those messages and books the call back. Worth a reply?\n\nthe operator")
        code, out = self.precheck(p)
        self.assertEqual(code, 0, out)

    def test_phone_shapes(self):
        import sys, os
        sys.path.insert(0, self.s.path("scripts"))
        from demo_number_check import find_numbers
        for t in ["the 2019 911 GT3", "2018-2021 models", "2015 2016 2017 2018 models",
                  "$45,900 and 120,000 miles", "on 2026-07-01", "12345 Main St 78701"]:
            self.assertEqual(find_numbers(t), [], t)
        for t in ["+1 (555) 010-0100", "555.010.0123", "1-800-555-0199", "02 9876 5432",
                  "0412 345 678", "+61 2 9876 5432", "(403) 918-8936"]:
            self.assertEqual(len(find_numbers("call " + t + " today")), 1, t)

    def test_wrong_number_blocks(self):
        p = self.s.draft(body="Call our demo at +1 (555) 010-9999 and reply if useful. " * 3)
        code, out = self.s.script("demo_number_check.py", p)
        self.assertEqual(code, 2)

    def test_banned_phrase_blocks(self):
        p = self.s.draft(body="I hope this email finds you well. " + "Worth a reply? " + "word " * 50)
        code, out = self.s.script("content_check.py", p)
        self.assertEqual(code, 2)
        self.assertIn("banned phrase", out)

    def test_link_in_first_touch_blocks_but_not_followup(self):
        body = "Here is a short Loom: https://loom.com/share/abc " + "word " * 50 + "Worth a reply?"
        code, out = self.s.script("content_check.py", self.s.draft(body=body))
        self.assertEqual(code, 2)
        self.assertIn("link", out)
        code, out = self.s.script("content_check.py", self.s.draft(body=body, touch="followup"))
        self.assertEqual(code, 0, out)

    def test_malformed_recipient_blocks(self):
        code, out = self.s.script("content_check.py", self.s.draft(recipient="frontdesk@"))
        self.assertEqual(code, 2)

    def test_em_dash_is_advisory(self):
        p = self.s.draft(subject="calls — after hours")
        code, out = self.s.script("content_check.py", p)
        self.assertEqual(code, 0, out)
        self.assertIn("em dash", out)

    def test_ai_tell_is_advisory(self):
        p = self.s.draft(body="It's not about the software, it's about the missed calls. " + "word " * 50)
        code, out = self.s.script("content_check.py", p)
        self.assertEqual(code, 0)
        self.assertIn("contrast reveal", out)

    def test_required_footer_blocks_when_enabled(self):
        self.s.write("references/sender-profile.md",
                     "<!-- SENDER-PROFILE\npostal_address: 1 Main St, Austin TX 78701\n"
                     "optout_line: Not relevant? Reply \"no thanks\" and I won't email again.\n"
                     "require_footer: true\n-->\n")
        code, out = self.s.script("content_check.py", self.s.draft())
        self.assertEqual(code, 2)
        self.assertIn("compliance footer", out)
        body = self.s.read_json("state/draft/aurora-medspa.json")["body"] + \
            "\n\n1 Main St, Austin TX 78701\nNot relevant? Reply \"no thanks\" and I won't email again."
        code, out = self.s.script("content_check.py", self.s.draft(body=body))
        self.assertEqual(code, 0, out)

    def test_suppression_address_and_domain(self):
        self.s.write("data/suppression.txt", "optout@a.com  # optout\n@blocked.com\n")
        self.assertEqual(self.s.script("suppression_check.py", "OptOut@A.com")[0], 2)
        self.assertEqual(self.s.script("suppression_check.py", "anyone@blocked.com")[0], 2)
        self.assertEqual(self.s.script("suppression_check.py", "fine@ok.com")[0], 0)

    def test_dedup_window(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        self.s.write_json("data/outreach-log.json", [
            {"recipient": "frontdesk@auroramedspa.com", "status": "sent_by_user", "sent_date": recent},
            {"recipient": "old@x.com", "status": "sent_by_user", "sent_date": old}])
        self.assertEqual(self.s.script("dedup_check.py", "frontdesk@auroramedspa.com", "14")[0], 2)
        self.assertEqual(self.s.script("dedup_check.py", "old@x.com", "14")[0], 0)
        code, out = self.precheck(self.s.draft())
        self.assertEqual(code, 2)

    def test_precheck_json_output(self):
        code, out = self.s.script("precheck.py", self.s.draft(), "--json")
        data = json.loads(out)
        self.assertEqual(data["verdict"], "CLEARED")
        self.assertIn("content", data["gates"])


if __name__ == "__main__":
    unittest.main()
