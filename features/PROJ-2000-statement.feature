# Future story, not implemented yet. Its step has no definition, so the scenario
# is UNDEFINED -> treated as pending. Pending scenarios of OTHER stories are
# informational only, never a regression (AC13).
@story:PROJ-2000
Feature: Kontoauszug per E-Mail

  @ac:AC1
  Scenario: A statement can be emailed
    Given a user "u1" with scope "invoice:read"
    When they request their statement by email
    Then an email with the statement attached is sent
