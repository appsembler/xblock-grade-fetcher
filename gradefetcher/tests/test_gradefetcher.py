import unittest

from gradefetcher.gradefetcher import GradeFetcherXBlock, grade_from_list


class GradeFetcherHelperTests(unittest.TestCase):
    def test_grade_from_list(self):
        assert grade_from_list([0]) == 0
        assert grade_from_list([1]) == 100
        assert grade_from_list([2]) == 200
        assert grade_from_list([0, 0]) == 0
        assert grade_from_list([1, 1]) == 100
        assert grade_from_list([1, 0]) == 50

    def test_is_valid_url(self):
        block = GradeFetcherXBlock(runtime=None, scope_ids=None)
        assert block.is_valid_url("https://www.example.com/")
        assert block.is_valid_url("http://www.example.com/")
        assert not block.is_valid_url("htt://www.example.com/")
        assert not block.is_valid_url("https://example/")
