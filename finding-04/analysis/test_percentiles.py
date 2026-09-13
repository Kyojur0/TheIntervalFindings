"""Hand-calculable tests guarding meaningful percentile failure modes."""
import unittest
import numpy as np

try:
    from percentiles import percentile, summary
except ImportError:
    percentile = summary = None


class PercentileTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(percentile, 'Percentile engine has not been implemented')

    def test_interpolation_weights_pathways_not_bands(self):
        # 30 pathways in the first band and 70 in the second: the median
        # is 20/70 of the way through the second band.
        self.assertAlmostEqual(percentile([30, 70, 0], .5), 1 + 20 / 70)

    def test_exact_cumulative_boundary_does_not_divide_by_empty_band(self):
        self.assertEqual(percentile([50, 0, 50, 0], .5), 1)

    def test_open_band_is_unbounded_not_a_one_week_bin(self):
        self.assertTrue(np.isnan(percentile([50, 50], .92)))
        self.assertEqual(percentile([50, 50], .5), 1)

    def test_historical_catchall_has_no_fictitious_upper_limit(self):
        counts = np.zeros(53); counts[6] = 95; counts[-1] = 5
        self.assertAlmostEqual(percentile(counts, .92), 6 + 92 / 95)
        counts[6] = 90; counts[-1] = 10
        self.assertTrue(np.isnan(percentile(counts, .92)))

    def test_empty_population_is_missing(self):
        self.assertTrue(np.isnan(percentile([0, 0, 0], .5)))

    def test_invalid_counts_fail_closed(self):
        for counts in ([1, -1, 0], [1, float('nan'), 0], [1, .5, 0]):
            with self.assertRaises(ValueError):
                percentile(counts, .5)

    def test_middle_boundary_and_exhaustive_partition(self):
        counts = np.zeros(105, dtype=int)
        counts[17] = 40; counts[18] = 20; counts[51] = 30; counts[52] = 10
        got = summary(counts)
        self.assertEqual(got['within18_count'], 40)
        self.assertEqual(got['middle_count'], 50)
        self.assertEqual(got['over52_count'], 10)
        self.assertEqual(got['total'], 100)
        self.assertAlmostEqual(sum(got[k] for k in ['within18_share','middle_share','over52_share']), 1)


if __name__ == '__main__':
    unittest.main()
