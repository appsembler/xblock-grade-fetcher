import json
import unittest

import django
from django.conf import settings
from mock import Mock
from xblock.field_data import DictFieldData
from xblock.test.tools import TestRuntime

from gradefetcher.gradefetcher import GradeFetcherXBlock, grade_from_list

settings.configure(Debug=True)
django.setup()


class GradeFetcherHelperTests(unittest.TestCase):
    def setUp(self):
        self.runtime = TestRuntime(
            services={"field-data": DictFieldData({}), "i18n": StubI18n()}
        )
        self.block = GradeFetcherXBlock(
            self.runtime,
            DictFieldData({}),
            Mock(),
        )
        self.user_data = {"username": "test@example.com"}
        self.settings_bucket = {
            "proxies": {"http": "http://example.com", "https": "https://example.com"},
        }

    def test_default_fields_values(self):
        self.assertEqual(self.block.display_name, "Grade Fetcher")
        self.assertEqual(self.block.title, "Grade Fetcher")
        self.assertEqual(self.block.button_text, "Grade Me")
        self.assertEqual(self.block.user_identifier, "email")
        self.assertEqual(self.block.user_identifier_parameter, "email")
        self.assertEqual(self.block.authentication_endpoint, "")
        self.assertEqual(self.block.client_id, "")
        self.assertEqual(self.block.client_secret, "")
        self.assertEqual(self.block.authentication_username, "")
        self.assertEqual(self.block.authentication_password, "")
        self.assertEqual(self.block.api_key, "")
        self.assertEqual(self.block.grader_endpoint, "")
        self.assertEqual(self.block.activity_identifier, "")
        self.assertEqual(self.block.activity_identifier_parameter, "unit_id")
        self.assertEqual(self.block.extra_params, "")

    def test_set_fields_values(self):
        fields = {
            "display_name": "Test Grade Fetcher",
            "title": "Grade Fetcher Title",
            "button_text": "Fetch My Grade",
            "user_identifier": "username",
            "user_identifier_parameter": "username",
            "authentication_endpoint": "https://www.authentication-endpoint.com/",
            "client_id": "my_client_id",
            "client_secret": "my_client_secret",
            "authentication_username": "my_username",
            "authentication_password": "my_password",
            "api_key": "my_api_key",
            "grader_endpoint": "https://www.grader-endpoint.com/",
            "activity_identifier": "my_activity_id",
            "activity_identifier_parameter": "activity_id",
            "extra_params": "my_extra_params",
        }
        self.block.submit_studio_edits(
            Mock(
                method="POST",
                body=json.dumps(
                    {"values": fields, "defaults": [self.block.editable_fields]}
                ).encode("utf-8"),
            )
        )
        self.assertEqual(self.block.display_name, "Test Grade Fetcher")
        self.assertEqual(self.block.title, "Grade Fetcher Title")
        self.assertEqual(self.block.button_text, "Fetch My Grade")
        self.assertEqual(self.block.user_identifier, "username")
        self.assertEqual(self.block.user_identifier_parameter, "username")
        self.assertEqual(
            self.block.authentication_endpoint,
            "https://www.authentication-endpoint.com/",
        )
        self.assertEqual(self.block.client_id, "my_client_id")
        self.assertEqual(self.block.client_secret, "my_client_secret")
        self.assertEqual(self.block.authentication_username, "my_username")
        self.assertEqual(self.block.authentication_password, "my_password")
        self.assertEqual(self.block.api_key, "my_api_key")
        self.assertEqual(self.block.grader_endpoint, "https://www.grader-endpoint.com/")
        self.assertEqual(self.block.activity_identifier, "my_activity_id")
        self.assertEqual(self.block.activity_identifier_parameter, "activity_id")
        self.assertEqual(self.block.extra_params, "my_extra_params")

    def test_grade_from_list(self):
        self.assertEqual(grade_from_list([0]), 0)
        self.assertEqual(grade_from_list([1]), 100)
        self.assertEqual(grade_from_list([2]), 200)
        self.assertEqual(grade_from_list([0, 0]), 0)
        self.assertEqual(grade_from_list([1, 1]), 100)
        self.assertEqual(grade_from_list([1, 0]), 50)
        self.assertEqual(grade_from_list([]), 0)

    def test_is_valid_url(self):
        self.assertTrue(self.block.is_valid_url("https://www.example.com/"))
        self.assertTrue(self.block.is_valid_url("http://www.example.com/"))
        self.assertFalse(self.block.is_valid_url("htt://www.example.com/"))
        self.assertFalse(self.block.is_valid_url("https://example/"))

    def test_get_settings(self):
        self.block.runtime.service = Mock(
            return_value=Mock(
                get_settings_bucket=Mock(return_value=self.settings_bucket),
            )
        )
        assert self.block.get_settings() == self.settings_bucket

    def test_grade_user_no_proxies(self):
        self.block.get_settings = Mock(return_value={})
        assert self.block.get_settings() == {}

    def test_grade_user_invalid_auth_endpoint(self):
        runtime = TestRuntime(
            services={"field-data": DictFieldData({}), "i18n": StubI18n()}
        )
        block = GradeFetcherXBlock(runtime=runtime, scope_ids=None)
        block.authentication_endpoint = "None"
        block.get_settings = Mock(return_value=self.settings_bucket)
        response = block.grade_user(request_wrap())
        assert response.json["message"] == "Authentication endpoint is not a valid url"
        assert response.json["status"] == "error"

    def test_grade_user_invalid_grader_endpoint(self):
        runtime = TestRuntime(
            services={"field-data": DictFieldData({}), "i18n": StubI18n()}
        )
        block = GradeFetcherXBlock(runtime=runtime, scope_ids=None)
        block.grader_endpoint = "None"
        block.get_settings = Mock(return_value=self.settings_bucket)
        response = block.grade_user(request_wrap())
        assert response.json["message"] == "Grader endpoint is not a valid url"
        assert response.json["status"] == "error"

    def test_grader_response_failed(self):
        grader_response = Mock()
        grader_response.json = Mock(
            return_value={
                "errorMessage": "local variable 'users_object' referenced before assignment",
                "errorType": "UnboundLocalError",
                "status": "error",
            }
        )
        grader_response.status_code = 500
        response = self.block.grader_response_failed(grader_response)
        assert response["status"] == "error"
        assert (
            response["msg"]
            == "local variable 'users_object' referenced before assignment"
        )

    def test_grade_without_account(self):
        grader_response = Mock()
        grader_response.json = Mock(
            return_value={
                "errorMessage": "We couldn't find your account",
                "errorType": "accountDoesNotExist",
                "status": "error",
            }
        )
        grader_response.status_code = 404
        response = self.block.grader_response_failed(grader_response)
        assert response["status"] == "error"
        assert (
            response["msg"]
            == """
                    We cannot find your account. Please make sure
                    that you have created your account. If you need
                    assistance, please contact the course team.
                    """
        )

    def test_grade_user_sucess(self):
        grader_response = Mock()
        grader_response.json = Mock(
            return_value={
                "results": [
                    {
                        "resultOrder": 1,
                        "resultName": "Create one or more organisation units under root hierarchy.",
                        "assignment_id": 1,
                        "grade": 1,
                        "reason": "Passed",
                    },
                    {
                        "resultOrder": 2,
                        "resultName": "Create a Data Set.",
                        "assignment_id": 2,
                        "grade": 0,
                        "reason": "It seems that your data set is not yet assigned to any organisation units.",
                    },
                    {
                        "resultOrder": 3,
                        "resultName": "Enter data on the data set.",
                        "assignment_id": 3,
                        "grade": 0,
                        "reason": "It seems that you have not yet assigned your data elements to your data set, therefore you can't enter data. Check that data elements are assigned to the data set that was created for you. ",
                    },
                ],
                "username": "test@example.com",
            }
        )
        grader_response.status_code = 200
        grade, reasons = self.block.process_grader_response(grader_response)
        assert grade == 33
        assert len(reasons) == 3


def request_wrap():
    """
    Wrapper for sending data to a json handler
    """
    request = Mock()
    request.method = "POST"
    request.body = b"{}"
    return request


class StubI18n(object):
    """a fake i18n service that just passes the input back out"""

    def ugettext(self, text):
        return text

    def gettext(self, text):
        return text
