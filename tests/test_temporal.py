import unittest
from itertools import product
from contracts.temporal import Bound, Extent, Match, historical_year, display_year


def b(lo, hi=None):
    return Bound('bounded', lo, lo if hi is None else hi)


def extent(start, end):
    return Extent(start, end, 'synthetic fixture', 'CE', 'year', 'fixture')


class TemporalContractTests(unittest.TestCase):
    def test_exact_inclusive(self):
        e = extent(b(10), b(20))
        self.assertEqual([e.as_of(y) for y in (9, 10, 20, 21)], [Match.NONE, Match.CERTAIN, Match.CERTAIN, Match.NONE])

    def test_uncertainty(self):
        e = extent(b(401, 500), b(600, 650))
        self.assertEqual([e.as_of(y) for y in (400, 450, 500, 600, 625, 651)], [Match.NONE, Match.POSSIBLE, Match.CERTAIN, Match.CERTAIN, Match.POSSIBLE, Match.NONE])

    def test_open_and_unknown(self):
        self.assertEqual(extent(Bound('open'), b(50)).as_of(-10**20), Match.CERTAIN)
        self.assertEqual(extent(b(50), Bound('open')).as_of(10**20), Match.CERTAIN)
        self.assertEqual(extent(Bound('unknown'), b(50)).as_of(40), Match.POSSIBLE)
        self.assertEqual(extent(Bound('unknown'), b(50)).as_of(51), Match.NONE)
        self.assertEqual(extent(Bound('unknown'), Bound('unknown')).as_of(0), Match.UNDATED)

    def test_bce_and_deep_time(self):
        for n, era in ((1, 'BCE'), (2, 'BCE'), (1, 'CE'), (10**20, 'BCE')):
            self.assertEqual(display_year(historical_year(n, era)), (n, era))
        self.assertEqual(historical_year(1, 'BCE'), 0)
        self.assertEqual(extent(b(-10**20), b(-10**19)).as_of(-10**20), Match.CERTAIN)

    def test_invalid(self):
        for args in [('bounded', 2, 1), ('bounded', True, 2), ('open', 0, None), ('invalid', None, None)]:
            with self.assertRaises(ValueError):
                Bound(*args)
        with self.assertRaises(ValueError):
            extent(b(5), b(4))
        with self.assertRaises(ValueError):
            extent(b(1), b(2)).overlap(2, 1)
        with self.assertRaises(ValueError):
            historical_year(0, 'CE')

    def test_original_metadata(self):
        e = Extent(b(-100), b(-90), 'BP sample', 'cal BP', 'decade', 'fixture only')
        self.assertEqual((e.original_text, e.calendar), ('BP sample', 'cal BP'))
        with self.assertRaises(ValueError):
            Extent(b(1), b(2), '', 'CE', 'year', 'fixture')

    def test_exhaustive_finite_intervals(self):
        years = range(-2, 3)
        pairs = [(a, z) for a in years for z in years if a <= z]
        for (sl, sh), (el, eh), (ql, qh) in product(pairs, repeat=3):
            feasible = [(s, e) for s in range(sl, sh+1) for e in range(el, eh+1) if s <= e]
            if not feasible:
                continue
            matches = [s <= qh and e >= ql for s, e in feasible]
            want = Match.CERTAIN if all(matches) else Match.POSSIBLE if any(matches) else Match.NONE
            self.assertEqual(extent(b(sl, sh), b(el, eh)).overlap(ql, qh), want)


if __name__ == '__main__':
    unittest.main()
