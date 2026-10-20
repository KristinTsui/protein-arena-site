import math
import unittest
from ranking import confidence, physics_percentile, combined, competition_ranks, modeled_escape, escape_rate


class RankingTests(unittest.TestCase):
    def test_missing_is_not_zero_or_reweighted(self):
        self.assertIsNone(confidence(.9, None))
        self.assertIsNone(combined(90, None))
        self.assertEqual(confidence(0, 0), 0)
        self.assertEqual(confidence(.8, .4), 60.00000000000001)

    def test_invalid_values_rejected(self):
        for bad in [math.nan, math.inf, -1, 2, True, ".8"]:
            with self.assertRaises(ValueError):
                confidence(bad, .5)
        with self.assertRaises(ValueError):
            physics_percentile(-10, [-20, None])

    def test_physics_direction_ties_and_fixed_reference(self):
        ref = [-30, -20, -20, -10]
        self.assertEqual(physics_percentile(-20, ref), 50)
        self.assertEqual(physics_percentile(-40, ref), 100)
        self.assertEqual(physics_percentile(0, ref), 0)
        self.assertIsNone(physics_percentile(-20, [-20]))
        self.assertIsNone(physics_percentile(-20, [-20, -20]))
        self.assertLess(combined(70, physics_percentile(-10, ref)),
                        combined(70, physics_percentile(-30, ref)))

    def test_shared_ranks_not_id_tiebreak(self):
        rows = [{"id": "z", "s": 80}, {"id": "a", "s": 80}, {"id": "b", "s": 20},
                {"id": "missing", "s": None}]
        self.assertEqual(competition_ranks(rows, "s"), {"a": 1, "z": 1, "b": 3})
        with self.assertRaises(ValueError):
            competition_ranks([rows[0], rows[0]], "s")

    def test_modeled_escape_requires_identity_review_and_all_channels(self):
        wt = dict(binding_supported=True, target_integrity_passed=True, protocol_id="p", binder_id="b",
                  score_valid=True, iptm=.8, ipsae_binder_to_target=.8, ipsae_target_to_binder=.8,
                  interface_dg_reu=-30, physics_score=80, physics_reference_sha256="a"*64)
        variant = dict(target_integrity_passed=True, protocol_id="p", binder_id="b",
                       score_valid=True, iptm=.5, ipsae_binder_to_target=.5, ipsae_target_to_binder=.5,
                       interface_dg_reu=-10, physics_score=20, physics_reference_sha256="a"*64)
        self.assertTrue(modeled_escape(wt, variant))
        self.assertFalse(modeled_escape(wt, dict(variant, physics_score=70)))
        self.assertFalse(modeled_escape(wt, dict(variant, ipsae_target_to_binder=.79)))
        self.assertFalse(modeled_escape(wt, dict(variant, interface_dg_reu=-40)))
        self.assertIsNone(modeled_escape(wt, dict(variant, binder_id="wrong")))
        self.assertIsNone(modeled_escape(wt, dict(variant, target_integrity_passed=False)))
        self.assertIsNone(modeled_escape(dict(wt, binding_supported=False), variant))
        self.assertIsNone(modeled_escape(dict(wt, target_integrity_passed=False), variant))

    def test_escape_exact_thresholds_and_just_below(self):
        wt = dict(binding_supported=True, target_integrity_passed=True, protocol_id="p", binder_id="b",
                  score_valid=True, interface_dg_reu=-30, physics_score=80, physics_reference_sha256="a"*64)
        variant = dict(target_integrity_passed=True, protocol_id="p", binder_id="b",
                       score_valid=True, interface_dg_reu=-10, physics_score=55, physics_reference_sha256="a"*64)
        keys = ("iptm", "ipsae_binder_to_target", "ipsae_target_to_binder")
        for start, end in [(.6, .45), (.3, .2)]:
            w = dict(wt, **{k: start for k in keys})
            v = dict(variant, **{k: end for k in keys})
            self.assertTrue(modeled_escape(w, v))
            self.assertFalse(modeled_escape(w, dict(v, iptm=end + .0000001)))

    def test_incomplete_coverage_never_improves_escape_rank(self):
        self.assertEqual(escape_rate([True, False], 2)["score"], 50)
        self.assertIsNone(escape_rate([True, None], 2)["score"])
        self.assertIsNone(escape_rate([], 0)["score"])
        self.assertIsNone(escape_rate([None, None], 2)["escape_count"])


if __name__ == "__main__":
    unittest.main()
