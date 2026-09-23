import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.address_parser import parse_address


class ParserAliasTests(unittest.TestCase):
    def test_saravanampatty_alias_is_normalized(self):
        parsed, parser = parse_address('saravanampatty cbe tn')
        self.assertEqual(parser, 'fallback')
        self.assertEqual(parsed['locality'], 'Saravanampatti')
        self.assertEqual(parsed['district'], 'Coimbatore')
        self.assertEqual(parsed['state'], 'Tamil Nadu')

    def test_kgisl_landmark_keeps_known_capitalization(self):
        parsed, _ = parse_address('near KGiSL college, Saravanampatti, cbe, tamilnadu')
        self.assertEqual(parsed['landmark'], 'KGiSL College')
        self.assertEqual(parsed['locality'], 'Saravanampatti')


if __name__ == '__main__':
    unittest.main()
