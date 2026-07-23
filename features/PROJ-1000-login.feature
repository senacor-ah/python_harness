# Already-shipped story. Runs on EVERY verify (the suite is cumulative). If new
# work breaks this, the acceptance worker reports it as a regression.
@story:PROJ-1000
Feature: Login

  @ac:AC1
  Scenario: Valid credentials create a session
    Given the credentials "alice" / "secret"
    When the user logs in
    Then a session token is returned
