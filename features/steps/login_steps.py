"""Step definitions for the already-shipped login story (PROJ-1000)."""

from behave import given, then, when

from app.services.session import login


@given('the credentials "{user_id}" / "{password}"')
def step_creds(context, user_id, password):
    context.creds = (user_id, password)


@when("the user logs in")
def step_login(context):
    context.login = login(*context.creds)


@then("a session token is returned")
def step_token(context):
    assert context.login["ok"], "expected login to succeed"
    assert context.login["token"].startswith("sess_")
