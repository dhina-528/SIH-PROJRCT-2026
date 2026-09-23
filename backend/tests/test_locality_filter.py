import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.db import search_candidates


class SearchCandidatesLocalityTests(unittest.TestCase):
    def test_locality_filters_results(self):
        rows = search_candidates(locality='Peelamedu', district='Coimbatore', state='Tamil Nadu', limit=20)
        self.assertTrue(rows)
        self.assertTrue(all(row['locality'].lower() == 'peelamedu' for row in rows))

    def test_locality_is_not_ignored_for_other_area(self):
        rows = search_candidates(locality='RS Puram', district='Coimbatore', state='Tamil Nadu', limit=20)
        self.assertTrue(rows)
        self.assertTrue(all('rs puram' in row['locality'].lower() for row in rows))


if __name__ == '__main__':
    unittest.main()
