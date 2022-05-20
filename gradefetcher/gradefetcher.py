import logging
import os
import urllib.parse
from operator import truediv

import pkg_resources
import requests
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.template import Context
from django.utils.translation import ugettext_lazy as _
from markupsafe import Markup
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Integer, Scope, String
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

LOGGER = logging.getLogger(__name__)

loader = ResourceLoader(__name__)


def grade_from_list(grades):
    """take a list of integers and calculate grade from them"""
    if len(grades) > 1:
        total_grade = sum(grades)
        grade = int(truediv(total_grade * 100, len(grades)))
    elif len(grades) == 1:
        grade = grades[0] * 100
    else:
        grade = 0
    return grade


@XBlock.needs("i18n", "user")
@XBlock.wants("settings")
class GradeFetcherXBlock(XBlock, StudioEditableXBlockMixin):
    """
    Get users grade from external systems
    """

    loader = ResourceLoader(__name__)
    has_score = True
    editable_fields = [
        "display_name",
        "title",
        "button_text",
        "user_identifier",
        "user_identifier_parameter",
        "authentication_endpoint",
        "client_id",
        "client_secret",
        "authentication_username",
        "authentication_password",
        "api_key",
        "grader_endpoint",
        "activity_identifier",
        "activity_identifier_parameter",
        "extra_params",
    ]
    # Defining the models
    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Grade Fetcher",
        scope=Scope.settings,
    )
    title = String(
        display_name=_("Title"),
        help=_("Title to show to the users"),
        default="Grade Fetcher",
        scope=Scope.settings,
    )
    button_text = String(
        display_name=_("Button text"),
        help=_("Text to show for the button"),
        default="Grade Me",
        scope=Scope.settings,
    )
    user_identifier = String(
        display_name=_("User Identifier"),
        help=_("This is the parameter we send to the grader to identify the user"),
        values=(
            {"display_name": _("email"), "value": "email"},
            {"display_name": _("username"), "value": "username"},
            {"display_name": _("user_id"), "value": "user_id"},
            {
                "display_name": _("anonymous_student_id"),
                "value": "anonymous_student_id",
            },
        ),
        default="email",
    )
    user_identifier_parameter = String(
        display_name=_("User identifier parameter name"),
        help=_(
            "this is a parameter we use in HTTP call to send user_identifier"
            "to the grader system, for example email or username."
            "If your system use custom parameter feel free to change it "
            "accordingly for example if your system uses, user_id to identify"
            "the user you should set this to user_id"
        ),
        default="email",
        scope=Scope.settings,
        null=False,
    )
    grade = Integer(
        display_name=_("User's Grade"),
        help=_("User's score in the activity"),
        default=0,
        scope=Scope.user_state,
    )
    reason = String(
        display_name=_(
            """
            An explanation from the external grader system
            about the user's score
            """
        ),
        help=_("Explanation from external grader"),
        scope=Scope.user_state,
        default="",
    )
    authentication_endpoint = String(
        display_name=_("Authentication Endpoint"),
        help=_("The endpoint that gives us authorized token"),
        scope=Scope.settings,
        default="",
    )
    client_id = String(
        display_name=_("Client ID"),
        help=_("OAuth2 client id to use for the authentication endpoint"),
        scope=Scope.settings,
        default="",
    )
    client_secret = String(
        display_name=_("Client Secret"),
        help=_("OAuth2 client password to use for the authentication endpoint"),
        scope=Scope.settings,
        default="",
    )
    api_key = String(
        display_name=_("API Key"),
        help=_(
            """
            API Key to include in the header of the request
            as X-API-Key in the grader api
            """
        ),
        scope=Scope.settings,
        default="",
    )
    authentication_username = String(
        display_name=_("Authentication Username"),
        help=_("Authentication endpoint Username"),
        scope=Scope.settings,
        default="",
    )
    authentication_password = String(
        display_name=_("Authentication Password"),
        help=_("Authentication endpoint Password"),
        scope=Scope.settings,
        default="",
    )
    grader_endpoint = String(
        display_name=_("Grader Endpoint "),
        help=_("This is an endpoint we call (with parameter) to get user's score"),
        scope=Scope.settings,
        default="",
        null=False,
    )
    http_method = String(
        display_name=_("HTTP call method"),
        help=_("Method we should use to call grader endpoint"),
        values=(
            {"display_name": _("get"), "value": "get"},
            {"display_name": _("post"), "value": "post"},
        ),
        default="get",
    )
    activity_identifier = String(
        display_name=_("Activity Identifier "),
        help=_(
            """
            An identifier to send to the grader to
            recognize the activity's unit
            """
        ),
        scope=Scope.settings,
        default="",
        null=False,
    )
    activity_identifier_parameter = String(
        display_name=_("Activity identifier parameter name"),
        help=_(
            "this is a parameter we use in HTTP call to send"
            "activity_identifier value to the grader system"
        ),
        default="unit_id",
        scope=Scope.settings,
        null=False,
    )
    extra_params = String(
        display_name=_("Extra Parameters:"),
        default="",
        scope=Scope.settings,
        help=_(
            "Here you can add extra parameters to include in the request url. "
            "you can add set of parameters and their value like:"
            "example_param_1=example_value_1&example_param_2=example_value_2"
            "Make sure it doesn't start with &"
            "If blank, extra parameters are ommitted from the url."
        ),
    )

    def is_valid_url(self, url):
        """
        Helper function used to check if a string is a valid url.

        Args:
            url (str): the url string to be validated

        Returns:
            bool: whether the url is valid or not
        """
        validate = URLValidator()
        try:
            validate(url)
            return True
        except ValidationError:
            return False

    def user_data(self):
        """
        This method initializes user's parameters
        """
        runtime = self.runtime  # pylint: disable=no-member
        user = runtime.service(self, "user").get_current_user()
        user_data = {}
        user_data["user_id"] = user.opt_attrs["edx-platform.user_id"]
        user_data["email"] = user.emails[0]
        user_data["role"] = runtime.get_user_role()
        user_data["username"] = user.opt_attrs["edx-platform.username"]
        user_data["anonymous_student_id"] = runtime.anonymous_student_id
        return user_data

    def grader_response_failed(self, grader_response):
        if "results" not in grader_response.json():
            if grader_response.status_code == 500:
                msg = grader_response.json()["errorMessage"]
                msg = self.i18n_service.gettext(msg)
            else:
                msg = self.i18n_service.gettext(
                    """
                    We cannot find your account. Please make sure
                    that you have created your account. If you need
                    assistance, please contact the course team.
                    """
                )
            htmlFormat = Markup("<span>{message}</span>")
            return {
                "status": "error",
                "msg": msg,
                "grade": "",
                "reason": "",
                "results": "",
                "htmlFormat": htmlFormat.format(message=msg),
            }
        else:
            return False

    def process_grader_response(self, grader_response):
        grades = []
        for result in grader_response.json()["results"]:
            if "grade" in result:
                grades.append(result["grade"])
        grade = grade_from_list(grades)
        reasons = []
        for result in grader_response.json()["results"]:
            if "grade" in result:
                if result["grade"] > 0:
                    reason = self.i18n_service.gettext(
                        "Assignment {assignment_id}: <b>Passed</b>"
                    ).format(
                        assignment_id=result.get("assignment_id", ""),
                    )
                    reasons.append(reason)
                elif result["grade"] == 0:
                    reason_api_text = self.i18n_service.gettext(result["reason"])
                    reason = self.i18n_service.gettext(
                        "Assignment {id}: <b>Failed</b> - {reason}"
                    ).format(
                        id=result["assignment_id"],
                        reason=reason_api_text,
                    )
                    reasons.append(reason)
            elif "grade" not in result:
                reason_api_text = self.i18n_service.gettext(result["reason"])
                reason = self.i18n_service.gettext(
                    "Assignment {assignment_id}: {reason_api_text}"
                ).format(
                    assignment_id=result.get("assignment_id", ""),
                    reason_api_text=reason_api_text,
                )
                reasons.append(reason)
        return grade, reasons

    def get_settings(self):
        """
        Get the XBlock settings bucket via the SettingsService.
        """
        settings_service = self.runtime.service(self, "settings")
        if settings_service:
            return settings_service.get_settings_bucket(self)
        return {}

    def load_resource(self, resource_path):
        """
        Gets the content of a resource
        """
        resource_content = pkg_resources.resource_string(__name__, resource_path)
        return resource_content.decode("utf8")

    def render_template(self, path, context=None):
        """
        Evaluate a template by resource path, applying the provided context
        """

        return self.loader.render_django_template(
            os.path.join("static/html", path),
            context=Context(context or {}),
            i18n_service=self.runtime.service(self, "i18n"),
        )

    def student_view(self, context=None):
        """
        The primary view of the GradeFetcherXBlock, shown to students
        when viewing courses.
        """
        context = {
            "display_name": self.display_name,
            "title": self.title,
            "button_text": self.button_text,
            "grade": self.grade,
            "reason": self.reason,
            "authentication_endpoint": self.authentication_endpoint,
            "grader_endpoint": self.grader_endpoint,
            "extra_params": "&{}".format(Markup(self.extra_params)),
        }
        html = self.render_template("gradefetcher.html", context)
        frag = Fragment(html)
        frag.add_css(self.load_resource("static/css/gradefetcher.css"))
        frag.add_javascript(self.load_resource("static/js/src/gradefetcher.js"))
        frag.initialize_js("GradeFetcherXBlock")
        return frag

    def studio_view(self, context=None):
        fragment = Fragment()
        context = {"fields": []}
        # Build a list of all the fields that can be edited:
        for field_name in self.editable_fields:
            field = self.fields[field_name]
            if field.scope not in (Scope.content, Scope.settings):
                raise ValueError(
                    "Only Scope.content or Scope.settings fields can be used "
                    "with StudioEditableXBlockMixin. Other scopes are for  "
                    "user-specific data and are not generally"
                    "created/configured by content authors in Studio."
                )
            field_info = self._make_field_info(field_name, field)
            if field_info is not None:
                context["fields"].append(field_info)
        fragment.content = self.render_template("studio_edit.html", context)
        fragment.add_javascript(self.load_resource("static/js/src/studio_edit.js"))
        fragment.initialize_js("StudioEditableXBlockMixin")
        return fragment

    @property
    def i18n_service(self):
        """Obtains translation service"""
        i18n_service = self.runtime.service(self, "i18n")
        if i18n_service:
            return i18n_service

    @XBlock.json_handler
    def grade_user(self, data, suffix=""):
        """
        Make a call to an external grader and retreive user's grade
        """

        if not self.is_valid_url(self.grader_endpoint):
            LOGGER.warning(
                "Grader endpoint is not a valid url: %s",
                self.grader_endpoint,
            )
            msg = self.i18n_service.gettext("Grader endpoint is not a valid url")
            htmlFormat = Markup("<span>{message}</span>")
            return {
                "status": "error",
                "msg": msg,
                "grade": "",
                "reason": "",
                "results": "",
                "htmlFormat": htmlFormat.format(message=msg),
            }

        # 1. If user in studio set authentication endpoint we call it
        try:
            # Get EXTERNAL_GRADER from configuration
            proxies = self.get_settings()["proxies"]
            grader_headers = {"Content-Type": "application/json"}
            if self.authentication_endpoint:
                # 2. Make call to auth endpoint and get the token
                if self.is_valid_url(self.authentication_endpoint):
                    # 2. Make call to auth endpoint and get the token
                    auth_response = requests.post(
                        self.authentication_endpoint,
                        proxies=proxies,
                        auth=(
                            self.client_id,
                            self.client_secret,
                        ),
                        headers={"Accept": "application/json"},
                        data={
                            "grant_type": "password",
                            "username": self.authentication_username,
                            "password": self.authentication_password,
                        },
                        timeout=10,
                    )
                    # get the token from the call
                    token = auth_response.json()["access_token"]
                    # add the token to the headers
                    grader_headers["Authorization"] = "Bearer {token}".format(
                        token=token
                    )
                    # add api key in the headers if it's set in studio
                    if self.api_key:
                        grader_headers["x-api-key"] = self.api_key
                else:
                    LOGGER.warning(
                        "Authentication endpoint is not a valid url: %s",
                        self.authentication_endpoint,
                    )
                    return {
                        "status": "error",
                        "message": self.i18n_service.ugettext(
                            "Authentication endpoint is not a valid url"
                        ),
                    }
            # 3. Make a call to the grader endpoint
            if self.http_method == "get":
                query = {
                    self.user_identifier_parameter: self.user_data()[
                        self.user_identifier
                    ]
                }
                if self.activity_identifier_parameter and self.activity_identifier:
                    query[self.activity_identifier_parameter] = self.activity_identifier
                if self.extra_params:
                    query.update(urllib.parse.parse_qs(self.extra_params))
                grader_response = requests.get(
                    self.grader_endpoint,
                    params=query,
                    proxies=proxies,
                    headers=grader_headers,
                    timeout=25,
                )
                grader_failed = self.grader_response_failed(grader_response)
                if grader_failed:
                    return grader_failed
                else:
                    grade, reasons = self.process_grader_response(grader_response)
        except Exception as e:
            LOGGER.exception(e)
            msg = self.i18n_service.gettext(
                """
                Something went wrong, please contact the course team.
                """
            )
            htmlFormat = Markup("<span>{message}</span>")
            return {
                "msg": "Something went wrong, please contact the course team.",
                "grade": "",
                "reason": "",
                "results": "",
                "htmlFormat": htmlFormat.format(message=msg),
            }

        reasons_msg = ""
        for reason in reasons:
            reasons_msg += "<li>{reason}</li>".format(reason=reason)
        self.htmlFormat = self.i18n_service.gettext(
            "You got <span class='grade'>{grade}% </span>"
            "score for this activity.<br />Explanation: <span class='reason'>"
            "<ul>{reasons_msg}</ul></span>"
        ).format(grade=grade, reasons_msg=reasons_msg)
        # grade the user
        if grade >= 0:
            grade_event = {"value": grade * 1.00 / 100, "max_value": 1}
            self.runtime.publish(self, "grade", grade_event)

        return {
            "grade": grade,
            "reason": reasons,
            "htmlFormat": self.htmlFormat,
        }

    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            (
                "GradeFetcherXBlock",
                """<gradefetcher/>
             """,
            ),
            (
                "Multiple GradeFetcherXBlock",
                """<vertical_demo>
                <gradefetcher/>
                <gradefetcher/>
                <gradefetcher/>
                </vertical_demo>
             """,
            ),
        ]
