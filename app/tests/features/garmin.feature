Feature: Garmin Integration
  Scenario: Successfully link Garmin account
    Given a user "carlos@example.com"
    When the user submits valid Garmin credentials "carlos@hotmail.com" and "pass123"
    Then the user's Garmin email should be "carlos@hotmail.com"
    And the system should confirm the sync started

  Scenario: Attempt to push workout without linking account
    Given a user "ana@example.com"
    When the user "ana@example.com" tries to push a workout without Garmin link
    Then the system should return an error "Su cuenta de Garmin no está vinculada"
