"""A mock for openedx site_configuration.helpers"""


configurations = {"GRADE_FETCHER": {'USERNAME': 'foo', 'PASSWORD': 'bar'}}


def get_value(value, default=None):
    return configurations.get(value, default)
