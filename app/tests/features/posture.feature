Feature: Posture Analysis
  Scenario: Analyze a correct squat posture
    Given the database has an exercise "squat" with valid rules
    When the user uploads a valid image for "squat"
    Then the status should be "success"
    And the stage should be "down"
    And the feedback should be "¡Buen movimiento!"
