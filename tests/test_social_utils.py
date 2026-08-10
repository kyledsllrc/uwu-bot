import pytest
from social_utils import (
    extract_json_ld,
    parse_counts_from_description,
    get_instagram_counts_from_html,
)

SAMPLE_LD = '<script type="application/ld+json">{"@context":"http://schema.org","@type":"Person","name":"Test","description":"1,234 Followers, 56 Following, 78 Posts - Example"}</script>'
SAMPLE_SHARED = 'window._sharedData = {"entry_data": {"ProfilePage": [{"graphql": {"user": {"edge_followed_by": {"count": 1234}, "edge_follow": {"count": 56}, "edge_owner_to_timeline_media": {"count":78}}}]}}};'


def test_extract_json_ld():
    obj = extract_json_ld(SAMPLE_LD)
    assert isinstance(obj, dict)
    assert obj.get('name') == 'Test'


def test_extract_window_shared_data():
    counts = get_instagram_counts_from_html(SAMPLE_SHARED)
    assert counts.get('followers') in ('1234', '1,234', '1234')


def test_parse_counts_from_description():
    counts = parse_counts_from_description('1,234 Followers, 56 Following, 78 Posts - Example')
    assert counts['followers'] == '1,234'
    assert counts['following'] == '56'
    assert counts['posts'] == '78'

if __name__ == '__main__':
    pytest.main([__file__])
