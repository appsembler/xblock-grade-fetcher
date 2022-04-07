import unittest

from gradefetcher.gradefetcher import grade_from_list


class GradeFetcherHelperTests(unittest.TestCase):
    def test_grade_from_list(self):
        assert grade_from_list([0]) == 0
        assert grade_from_list([1]) == 100
        assert grade_from_list([2]) == 200
        assert grade_from_list([0, 0]) == 0
        assert grade_from_list([1, 1]) == 100
        assert grade_from_list([1, 0]) == 50
