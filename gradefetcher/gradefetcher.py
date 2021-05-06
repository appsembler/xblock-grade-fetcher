from django.template import Context, Template
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Integer, Scope, String
from xblockutils.studio_editable import StudioEditableXBlockMixin
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
import pkg_resources
import requests
import logging

LOGGER = logging.getLogger(__name__)


@XBlock.needs('i18n', 'user')
class GradeFetcherXBlock(XBlock, StudioEditableXBlockMixin):
    """
    Get users grade from external systems
    """
    has_score = True
    editable_fields = [
        'display_name',
        'description',
        'button_text',
        'user_identifier',
        'user_identifier_parameter',
        'authentication_endpoint',
        'grader_endpoint',
        'http_method',
        'activity_identifier',
        'activity_identifier_parameter',
        'extra_params'
    ]
    # Defining the models
    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Grade Fetcher",
        scope=Scope.settings,
    )
    description = String(
        display_name=_("Description"),
        help=_("Description to show to the users"),
        default="Description",
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
            {'display_name': _('email'), 'value': 'email'},
            {'display_name': _('username'), 'value': 'username'},
            {'display_name': _('user_id'), 'value': 'user_id'},
            {'display_name': _('anonymous_student_id'), 'value': 'anonymous_student_id'}
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
    )
    grade = Integer(
        display_name=_("User's Grade"),
        help=_("User's score in the activity"),
        default=0,
        scope=Scope.user_state
    )
    reason = String(
        display_name=_(
            "An explanation from the external grader system "
            "about the user's score"
        ),
        help=_("Explanation from external grader"),
        scope=Scope.user_state,
        default=""
    )
    authentication_endpoint = String(
        display_name=_("Authentication Endpoint"),
        help=_("The endpoint that gives us authorized token"),
        scope=Scope.settings,
        default=""
    )
    grader_endpoint = String(
        display_name=_("Grader Endpoint "),
        help=_(
            "This is an endpoint we call (with parameter) to get user's score"
        ),
        scope=Scope.settings,
        default=""
    )
    http_method = String(
        display_name=_("HTTP call method"),
        help=_("Method we should use to call grader endpoint"),
        values=(
            {'display_name': _('get'), 'value': 'get'},
            {'display_name': _('post'), 'value': 'post'}
        ),
        default="get",
    )
    activity_identifier = String(
        display_name=_("Activity Identifier "),
        help=_(
            "An identifier to send to the grader to recognize the activity's unit"
        ),
        scope=Scope.settings,
        default=""
    )
    activity_identifier_parameter = String(
        display_name=_("Activity identifier parameter name"),
        help=_(
            "this is a parameter we use in HTTP call to send"
            "activity_identifier value to the grader system"
        ),
        default="unit_id",
        scope=Scope.settings,
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
        )
    )

    def user_data(self):
        """
        This method initializes user's parameters
        """
        runtime = self.runtime  # pylint: disable=no-member
        user = runtime.service(self, 'user').get_current_user()
        user_data = {}
        user_data["user_id"] = user.opt_attrs["edx-platform.user_id"]
        user_data["email"] = user.emails[0]
        user_data["role"] = runtime.get_user_role()
        user_data["username"] = user.opt_attrs['edx-platform.username']
        user_data["anonymous_student_id"] = runtime.anonymous_student_id
        return user_data

    def load_resource(self, resource_path):
        """
        Gets the content of a resource
        """
        resource_content = pkg_resources.resource_string(__name__, resource_path)
        return resource_content.decode("utf8")

    def render_template(self, template_path, context={}):
        """
        Evaluate a template by resource path, applying the provided context
        """
        template_str = self.load_resource(template_path)
        return Template(template_str).render(Context(context))

    def student_view(self, context=None):
        """
        The primary view of the GradeFetcherXBlock, shown to students
        when viewing courses.
        """
        context = {
            'display_name': self.display_name,
            'description': self.description,
            'button_text': self.button_text,
            'grade': self.grade,
            'reason': self.reason,
            'authentication_endpoint': self.authentication_endpoint,
            'grader_endpoint': self.grader_endpoint,
            'extra_params': mark_safe("&{}".format(self.extra_params))
        }
        html = self.render_template("static/html/gradefetcher.html", context)
        frag = Fragment(html)
        frag.add_css(self.load_resource("static/css/gradefetcher.css"))
        frag.add_javascript(self.load_resource("static/js/src/gradefetcher.js"))
        frag.initialize_js('GradeFetcherXBlock')
        return frag

    @XBlock.json_handler
    def grade_user(self, data, suffix=''):
        """
        Make a call to an external grader and retreive user's grade
        """
        # Get EXTERNAL_GRADER from site configuration
        grade_fetcher_settings = configuration_helpers.get_value(
            "GRADE_FETCHER", ""
            )
        # 1. If user in studio set authentication endpoint we call it
        if self.authentication_endpoint:
            try:
                # 2. Make call to auth endpoint and get the token
                auth_response = requests.post(
                    self.authentication_endpoint,
                    auth=(
                        grade_fetcher_settings["AUTH_ENDPOINT_USERNAME"], 
                        grade_fetcher_settings["AUTH_ENDPOINT_PASSWORD"]
                        ),
                    headers={
                        "Accept": "application/json"
                    },
                    data={
                        "grant_type": "password",
                        "username": grade_fetcher_settings["USERNAME"],
                        "password": grade_fetcher_settings["PASSWORD"]
                    }
                )
                # get the token from the call
                token = auth_response.json()["access_token"]
                # 3. Call graded endpoint
                grader_headers = {
                    "Content-Type": "application/json"
                }
                grader_headers["Authorization"] = "Bearer {token}".format(token=token)
                # add api key in the headers if it's set in site configurations
                if grade_fetcher_settings["API-KEY"]:
                    grader_headers["x-api-key"] = grade_fetcher_settings["API-KEY"]
                # Make call based on the method in the studio xblock
                if self.http_method == "get":
                    get_query_string = "?"
                    get_query_string += self.user_identifier_parameter
                    get_query_string += "=" + self.user_data().get(self.user_identifier, "")
                    if self.activity_identifier_parameter:
                        get_query_string += "&" + self.activity_identifier_parameter
                    if self.activity_identifier:
                        get_query_string += "=" + self.activity_identifier
                    if self.extra_params:
                        get_query_string += "&" + self.extra_params
                    LOGGER.info(self.grader_endpoint + get_query_string)
                    LOGGER.info(grader_headers)
                    grader_response = requests.get(
                        self.grader_endpoint + get_query_string,
                        headers=grader_headers
                    )
                    LOGGER.info(grader_response.json())
                    calculate_grade = False
                    grades = []
                    for result in grader_response.json()["results"]:
                        if "grade" in result:
                            grades.append(result["grade"])
                    if len(grades) > 1:
                        from operator import truediv
                        total_grade = 0
                        for g in grades:
                            total_grade += g
                        grade = round(truediv(total_grade,len(grades)),1)
                    reasons = ""
                    for result in grader_response.json()["results"]:
                        reasons += "Assignment {assignment_id} - {reason} ".format(
                            assignment_id = result["assignment_id"],
                            reason = result["reason"]
                        )
                elif self.http_method == "post":
                    grader_response = requests.post(
                        self.grader_endpoint,
                        headers=grader_headers
                    )
            except Exception as e:
                LOGGER.exception(e)
        else:
            try:
                # 3. Call graded endpoint
                grader_headers = {
                    "Content-Type": "application/json"
                }
                # Make call based on the method in the studio xblock
                if self.http_method == "get":
                    grader_response = requests.get(
                        self.grader_endpoint,
                        headers=grader_headers
                    )
                elif self.http_method == "post":
                    grader_response = requests.post(
                        self.grader_endpoint,
                        headers=grader_headers
                    )
            except Exception as e:
                LOGGER.exception(e)

        self.htmlFormat = '''
        <span>
        You got <span class="grade">{grade}</span> score for this activity.<br />
        Explanation: <span class="reason">{reasons}</span>
        <span>
        '''.format(grade=grade, reasons=reasons)
        # grade the user
        if grade:
            grade_event = {'value': grade, 'max_value': 1}
            self.runtime.publish(self, 'grade', grade_event)

        return {
            'grade': grade,
            'reason': reasons,
            'htmlFormat': self.htmlFormat
        }

    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("GradeFetcherXBlock",
             """<gradefetcher/>
             """),
            ("Multiple GradeFetcherXBlock",
             """<vertical_demo>
                <gradefetcher/>
                <gradefetcher/>
                <gradefetcher/>
                </vertical_demo>
             """),
        ]
