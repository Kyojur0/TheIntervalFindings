"""Parser regression tests: invalid counts must not turn into pathways."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

try:
    import build_cache as bc
except ImportError:
    bc = None


def names(last=104):
    return [f"Gt {i:02d} To {i+1:02d} Weeks SUM 1" for i in range(last)] + [f"Gt {last} Weeks SUM 1"]


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(bc, "The parser module must exist")
        base = Path(__file__).resolve().parents[1] / "results" / "test-work"
        base.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def source(self, overrides=None, last=104):
        bands = names(last)
        def row(code, commissioner="A", part="Part_2", value=3):
            return {"Provider Org Code":"P", "Provider Org Name":"Provider", "Commissioner Org Code":commissioner,
                    "RTT Part Type":part, "Treatment Function Code":code, "Treatment Function Name":code,
                    **dict.fromkeys(bands, 0), bands[0]:value, "Total":"", "Total All":value,
                    "Patients with unknown clock start date":""}
        rows=[row("C_100"),row("C_999"),row("C_100", "B",value=2),row("C_999", "B",value=2),
              row("C_100", "NONC",value=97),row("C_100", "A",part="Part_2A",value=91)]
        if overrides:
            overrides(rows,bands)
        path=self.root/"raw.csv"
        with path.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
        return path

    def build(self,path,kind="monthly"):
        return bc.build_source(path, "2024-01", kind, self.root/"cache")

    def test_exact_scope_and_commissioner_pooling_preserve_total_code(self):
        got=self.build(self.source())
        self.assertEqual(got.index.code.tolist(), ["C_100","C_999"])
        np.testing.assert_array_equal(got.bands.sum(axis=1), [5,5])
        self.assertEqual(got.audit["filters"]["raw_rows"],6)
        self.assertEqual(got.audit["filters"]["retained_rows"],4)
        self.assertEqual(got.audit["specialty_total_reconciliation"]["mismatched_provider_parts"],0)

    def test_missing_negative_fractional_counts_are_rejected_with_audit(self):
        for bad in ["",-1,0.25]:
            with self.subTest(bad=bad):
                path=self.source(lambda rows,bands: rows[0].__setitem__(bands[0],bad))
                with self.assertRaises(bc.DataQualityError):
                    self.build(path)
                self.assertTrue(list((self.root/"cache").glob("*.audit.json")))

    def test_blank_zero_requires_independent_total_reconciliation(self):
        got=self.build(self.source(lambda rows,bands: rows[0].__setitem__(bands[2],"")))
        self.assertEqual(got.audit["blank_band_resolution"]["certified_zero_cells"],1)
        self.assertEqual(got.bands[0].sum(),5)

    def test_cache_reuse_and_source_change_invalidation(self):
        path=self.source(); first=self.build(path)
        again=self.build(path)
        self.assertTrue(again.cache_hit)
        self.assertEqual(first.audit["source"]["sha256"],again.audit["source"]["sha256"])
        self.source(lambda rows,bands: (rows[0].__setitem__(bands[0],4),rows[0].__setitem__("Total All",4)))
        changed=self.build(path)
        self.assertFalse(changed.cache_hit)
        self.assertEqual(changed.bands[0].sum(),6)

    def test_baseline_keeps_53_bands_and_modern_rejects_it(self):
        path=self.source(last=52)
        got=self.build(path,kind="baseline")
        self.assertEqual(got.bands.shape[1],53)
        with self.assertRaises(bc.DataQualityError):
            self.build(path,kind="monthly")

    def test_duplicates_and_unknown_clock_totals_are_audited(self):
        def change(rows,bands):
            rows.append(rows[0].copy())
            rows[0]["Patients with unknown clock start date"]=2
            rows[0]["Total All"]=5
            rows[0]["Total"]=3
        got=self.build(self.source(change))
        self.assertEqual(got.audit["duplicate_raw_keys"]["duplicate_groups"],1)
        self.assertEqual(got.audit["row_totals"]["Total All"]["unexplained_mismatch_rows"],0)
        self.assertEqual(got.audit["row_totals"]["Total All"]["explained_by_known_unknown_clock_rows"],1)


if __name__ == "__main__":
    unittest.main()
