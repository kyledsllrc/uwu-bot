import unittest
from social_utils import (
    extract_json_ld,
    parse_counts_from_description,
    get_instagram_counts_from_html,
)

SAMPLE_LD = '<script type="application/ld+json">{"@context":"http://schema.org","@type":"Person","name":"Test","description":"1,234 Followers, 56 Following, 78 Posts - Example"}</script>'
SAMPLE_SHARED = 'window._sharedData = {"entry_data": {"ProfilePage": [{"graphql": {"user": {"edge_followed_by": {"count": 1234}, "edge_follow": {"count": 56}, "edge_owner_to_timeline_media": {"count":78}}}]}}};'


class TestSocialUtils(unittest.TestCase):
    def test_extract_json_ld(self):
        obj = extract_json_ld(SAMPLE_LD)
        self.assertIsInstance(obj, dict)
        self.assertEqual(obj.get('name'), 'Test')

    def test_extract_window_shared_data(self):
        counts = get_instagram_counts_from_html(SAMPLE_SHARED)
        self.assertIn(counts.get('followers'), ('1234', '1,234'))

    def test_parse_counts_from_description(self):
        counts = parse_counts_from_description('1,234 Followers, 56 Following, 78 Posts - Example')
        self.assertEqual(counts['followers'], '1,234')
        self.assertEqual(counts['following'], '56')
        self.assertEqual(counts['posts'], '78')


if __name__ == '__main__':
    unittest.main()
