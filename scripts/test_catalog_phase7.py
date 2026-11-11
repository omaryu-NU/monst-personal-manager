import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from technophere_catalog import plan_listing_pages, next_listing_cursor


class ListingCoverageTest(unittest.TestCase):
    def setUp(self):
        self.state = json.loads((Path(__file__).parent / 'fixtures_phase7' / 'catalog-update-state.json').read_text(encoding='utf-8'))
        self.visited = set(self.state['visitedPages'])

    def test_real_state_prioritizes_unvisited_page_46(self):
        pages = plan_listing_pages(50, self.visited, 46, 5)
        self.assertEqual(pages, [1, 46, 47, 48, 49])

    def test_wrap_around_to_early_missing_pages(self):
        visited = self.visited | {46, 47, 48, 49}
        pages = plan_listing_pages(50, visited, 50, 5)
        self.assertEqual(pages, [1, 50, 2, 3, 4])

    def test_fill_after_missing_pages_exhausted(self):
        pages = plan_listing_pages(5, {1, 2, 3, 4}, 4, 5)
        self.assertEqual(pages, [1, 5, 4, 2, 3])

    def test_first_page_only_on_one_slot(self):
        self.assertEqual(plan_listing_pages(50, set(), 2, 1), [1])

    def test_cursor_advances_from_last_planned(self):
        self.assertEqual(next_listing_cursor(50, [1, 50, 2, 3, 4], 50), 5)
        self.assertEqual(next_listing_cursor(50, [1, 46, 47, 48, 49], 46), 50)
        self.assertEqual(next_listing_cursor(50, [1, 49, 50], 49), 2)

    def test_all_pages_revisit_rotation(self):
        pages = plan_listing_pages(50, set(range(1, 51)), 46, 5)
        self.assertEqual(pages, [1, 46, 47, 48, 49])


if __name__ == '__main__':
    unittest.main()
