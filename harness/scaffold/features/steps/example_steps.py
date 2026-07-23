"""Example step definitions. Drive your REAL MAF agent/tool code here so a green
scenario is genuine evidence. In Phase 4, assert tool calls via MAF
``LocalEvaluator.tool_called_check`` instead of the placeholder below. Delete this
once you have real steps. Written by `harness init`.
"""

from behave import given, then, when


@given('a user "{uid}" with scope "{scope}"')
def step_user(context, uid, scope):
    # TODO: build your real User/context and drive your agent.
    context.user = {"id": uid, "scopes": {scope}}


@when("they invoke the feature")
def step_invoke(context):
    # TODO: call your workflow/agent, e.g. context.result = handle(context.user, "...")
    context.result = {"tool_calls": ["expected_tool"]}


@then("the expected tool is called")
def step_tool(context):
    assert "expected_tool" in context.result["tool_calls"]
