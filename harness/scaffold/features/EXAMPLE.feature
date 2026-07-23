# Example behaviour spec. One .feature per story; @story maps to the Jira key and
# @ac maps each scenario to the acceptance criterion it proves. The suite is
# cumulative (all stories run every time) so regressions surface. Delete this once
# you have real features. Written by `harness init`.
@story:PROJ-0000
Feature: Example — replace with your story

  @ac:AC1
  Scenario: Authorized user reaches the happy path
    Given a user "u1" with scope "example:read"
    When they invoke the feature
    Then the expected tool is called
