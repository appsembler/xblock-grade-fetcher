# Grade Fetcher XBlock

By adding this XBlock to a course unit you can fetch grades from an external system for a corresponding problem(s) in Open edX and another system and grade users in Open edX based on what recieved from the external system.

## Fields
1. Display Name: Title of the XBlock in the Studio
2. Title: Title of the XBlock in the LMS (Title that appears to the students)
3. Button Text: Text that appears on the button that triggers the grader endpoint
4. User Identifier: The external system needs to recognize the user by this identifier, you can choose email, username, user_id or anonyomous_student_id. The actual value comes from what we have in Open edX.
5. User identifier parameter name: This is the parameter name that we wrap the user identifier in.
6. Authentication Endpoint: If your system requieres authentication you should set this. If not the call will be made directly to the grader endpoint.
7. Client ID: OAuth2 Client ID for Auth endpoint
8. Client Secret: OAuth2 Client Secret for Auth endpoint
9. Authentication Username: Username for Auth endpoint
10. Authentication Password: Password for Auth endpoint
11. API Key: If the grader enpoint requieres an API key in the header as `X-API-Key` you should set this.
12. Grader Endpoint: The endpoint that will be called to fetch grades.
13. Activity Identifier: The identifier of the problem in the external system. If you need to fetch grades for multiple problems you have to setup your system in a way to interpret this parameter as a range of problems. For example if the value is `4` your system can send back assignment 1 to 4 grades
14. Activity Identifier parameter name: This is the parameter name that we wrap the activity identifier in.
15. Extra Parameters: Any extra parameters that you want to send to the grader endpoint.

## Workflow

### Authentication
TO-DO

### Fetching grades

After filling all the required fields in studio by clicking on Grade me button if the authentication is requiered we first make an call the auth endpoint, recieve a token and after that we construct an HTTP request to the grader endpoint based on the parameters and their values you have set in studio.

The external system should return a JSON with the following structure:

```json
{
    "results": [
        {
            "assignment_id": 1,
            "grade": 1,
            "assignment_title": "Create Org Unit Group Sets and Assign OU Groups to them.",
            "reason": "User created at least one child org unit under their root."
        },
        {
            "assignment_id": 2,
            "grade": 0,
            "assignment_title": "Create Org Units and Assign OU Groups to them.",
            "reason": "All of the user's org units are assigned to 1 or more of their org unit groups."
        },
        {
            "assignment_id": 3,
            "grade": 1,
            "assignment_title": "Create Org Unit Group Sets and Assign OU Groups to them.",
            "reason": "User Created at least two organisation unit group sets and they have 2 or more (>= 2) Org Unit Groups Assigned."
        },
        {
            "assignment_id": 4,
            "grade": 1,
            "assignment_title": "Create the six specified data elements.",
            "reason": "User created the six specified data elements."
        }
    ]
}
```

`assignment_id` , `grade` and `reason` are required in the response. Please make sure your system returns these parameters.

[Here](https://48oj7cnxk4.execute-api.us-east-1.amazonaws.com/default/external-grading-system?unit_id=4) is an example of the response. By filling the fields 4, 5, 12, 13 and 14 in the [Fields](#Fields) section, you can see a demo of how this XBlock works.


## How to add translation

- If you made any changes in the translation files make sure to run `msgfmt text.po -o text.mo` locally in the `gradefetcher/translations/fr_CA/LC_MESSAGES/` folder or other languages folder to update the language files and after that push the changes to the branch.
- Make a deployment via ansible using the ansible tag `install:app-requirements`.
- Restart Open edX services on the server.

# Changelog

See [CHANGELOG.md](CHANGELOG.md)
