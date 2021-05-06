from django.template import Context, Template
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Integer, Scope, String
from xblockutils.studio_editable import StudioEditableXBlockMixin
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
import pkg_resources
import requests


@XBlock.needs('i18n', 'user')
class GradeMeXBlock(XBlock, StudioEditableXBlockMixin):
    """
    Get users grade from external systems
    """
    has_score = True
    editable_fields = [
        'authentication_endpoint',
        'grader_endpoint',
        'extra_params'


    ]
    # Defining the mode
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
    extra_params = String(
        display_name=_("Extra Parameters:"),
        default="example_param_1=example_value_1&example_param_2=example_value_2",
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
        The primary view of the GradeMeXBlock, shown to students
        when viewing courses.
        """
        context = {
            'grade': self.grade,
            'reason': self.reason,
            'authentication_endpoint': self.authentication_endpoint,
            'grader_endpoint': self.grader_endpoint,
            'extra_params': mark_safe("&{}".format(self.extra_params))
        }
        html = self.render_template("static/html/grademe.html", context)
        frag = Fragment(html)
        frag.add_css(self.load_resource("static/css/grademe.css"))
        frag.add_javascript(self.load_resource("static/js/src/grademe.js"))
        frag.initialize_js('GradeMeXBlock')
        return frag

    @XBlock.json_handler
    def grade_user(self, data, suffix=''):
        """
        Make a call to an external grader and retreive user's grade
        """
        self.response = requests.post(
            "https://us-central1-appsembler-testing.cloudfunctions.net/external_grader_test_endpoint",
            data={
                "email": self.user_data().get("email", ""),
                "username": self.user_data().get("username", ""),
                "role": self.user_data().get("role", ""),
                "anonymous_student_id": self.user_data().get(
                    "anonymous_student_id", ""
                ),
                "user_id": self.user_data().get("user_id", "")
            }
        )
        self.grade = 1
        self.reason = "You completed this activity with high score."
        self.htmlFormat = '''
        <span>
        You got <span class="grade">{grade}</span> score for this activity.<br />
        Explanation: <span class="reason">{reason}</span>
        <span>
        '''.format(grade=self.grade, reason=self.reason)
        # grade the user
        if self.grade:
            grade_event = {'value': self.grade, 'max_value': 1}
            self.runtime.publish(self, 'grade', grade_event)

        return {
            'grade': self.grade,
            'reason': self.reason,
            'htmlFormat': self.htmlFormat
        }

    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("GradeMeXBlock",
             """<grademe/>
             """),
            ("Multiple GradeMeXBlock",
             """<vertical_demo>
                <grademe/>
                <grademe/>
                <grademe/>
                </vertical_demo>
             """),
        ]
