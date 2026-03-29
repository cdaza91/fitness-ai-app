Feature: Workout Generation
  Scenario: Generate a running workout plan
    Given a user with a goal of "marathon" and a pace of "5:45"
    When the user requests a "running" workout
    Then the system should generate a plan with a focus on "running"
    And the plan should have MM:SS formatted paces

  Scenario: Generate a strength workout plan
    Given a user with a goal of "muscle gain" and "Full Gym" access
    When the user requests a "strength" workout
    Then the system should generate a plan with a focus on "strength"
    And the plan should have exercises with "reps" or "duration_s"
