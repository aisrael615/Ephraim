# Testing Ephraim

This document outlines the overall testing strategy for **Ephraim**, covering unit tests, integration tests, and LLM-assisted testing approaches.

---

## Overall Testing Structure

- Testing is built on **pytest** infrastructure:
  - Fixtures
  - Assertions
  - Parametrization

---

## Unit Tests

**Goal:** Deterministically test individual tools without involving the full Agent.

- Each tool is tested independently
- Tests cover the following scenarios:
  - ✅ **Success**
  - ❌ **Failure**
  - ⚠️ **Error** (invalid input)

### Example: `get_medicine_details_by_name`

A pytest-parametrized test with at least the following inputs for `name`:

| Input        | Description                     |
|--------------|---------------------------------|
| `PainAway`   | Valid input, exists in database |
| `GoAwayPain` | Valid input, not in database    |
| `555`        | Invalid input                   |

- These tests are:
  - Fully deterministic
  - Run on every regression

---

## Integration Tests

**Goal:** Test Ephraim as a complete system interacting with an LLM.

- Integration testing is inherently less deterministic
- Ephraim’s output is analyzed using an additional LLM call:
  - This LLM is referred to as the **Evaluator**
- The Evaluator receives task-specific instructions based on the test type

### Integration Test Categories

- **Accuracy Tests**
- **Rule-Following Tests**
- **Quality Tests**

---

## Accuracy Integration Tests

- Largely deterministic:
  - Predefined input prompt
  - Expected answer known in advance
- The Evaluator:
  - Reads Ephraim’s output
  - Extracts the answer
  - Returns it in a predefined **JSON format**
- The test:
  - Parses the JSON
  - Asserts the extracted answer matches the expected result

### Example

**Input:**  
> *Who manufactures PainAway?*

- The Evaluator strips Ephraim’s response to return only the manufacturer name
- The test compares this result to the expected value

### Coverage

Accuracy tests are run:
- For **every tool**
- In **English and Hebrew**
- For expected error cases 
- Scenarios requiring **multiple tools** in conjunction
  - `What are my prescriptions and what are their side effects?`

---

## Rule-Following Integration Tests

- These tests are also largely deterministic
- The expected outcome is whether Ephraim:
  - Detects a rule violation
  - Refuses the request appropriately

### Evaluator Behavior

- Reads Ephraim’s output
- Returns:
  - `True` → A rule was broken and handled correctly
  - `False` → No rule violation detected

### Test Design

- Inputs are parametrized based on the rule set:
  - No diagnosing
  - No medical advice
  - Etc.
- Assertions verify Ephraim:
  - Identified the violation
  - Responded according to policy

### Coverage

- Tests are run:
  - In **English and Hebrew**
  - With multiple variations of rule-breaking prompts

---

## Quality Integration Tests

**Goal:** Ensure Ephraim meets qualitative standards.

- The Evaluator is given a list of desired qualities, such as:
  - Politeness
  - Likeability
  - Clarity
- Each response is scored on a **0–10 scale** per quality

### Scoring Method

- Ephraim’s output is evaluated:
  - With multiple passes through the Evaluator
  - With slightly varied system instructions
- Final score:
  - Average of all evaluation runs

### Test Criteria

- Tests assert that Ephraim:
  - Meets or exceeds a predefined threshold
  - Across all desired qualities

### Coverage

- Tests are run:
  - In **English and Hebrew**
  - For requests that exercise **every tool**

---

## LLM-Determined Input Tests

**Goal:** Test Ephraim in non-deterministic, evolving scenarios.

- Introduces an additional LLM:
  - **TestCreator**
- TestCreator is instructed to:
  - Generate new test inputs
  - Define expected outputs
  - Output them into a structured file

### Workflow

1. TestCreator generates inputs and expected outputs
2. The generated file is fed into the existing integration tests
3. Ephraim is evaluated on continuously novel cases

### Example

- TestCreator generates multiple variations of an **Accuracy Test**
- Each variation uses slightly different language
- This helps evaluate Ephraim across a broader linguistic and semantic range


---

## CI Execution Plan

Because different test types vary significantly in cost, runtime, and determinism, tests should be executed in tiers within CI.

### On Every Commit / Pull Request
These tests are fast, deterministic, and inexpensive, making them suitable for continuous execution.

- Unit Tests  
  - Fully deterministic
  - No LLM calls
  - Catch regressions in individual tools early

- Accuracy Integration Tests (limited set)  
  - Run with a small, representative subset
  - Ensure core end-to-end functionality still works
  - LLM calls are required but tightly scoped and predictable

- Rule Following Integration Tests  
  - Binary pass/fail behavior
  - Important for safety guarantees
  - Relatively cheap compared to quality tests

These tests should block merges on failure.

### Scheduled / Nightly Runs
These tests are more expensive and/or time-consuming due to multiple LLM calls and non-determinism.

- Full Accuracy Integration Test Suite  
  - Covers all tools, languages, and multi-tool scenarios

- Quality Integration Tests  
  - Require multiple evaluator passes per output
  - Scores are averaged, making them slower and more costly
  - Results are better interpreted as trends rather than single-run failures

- LLM Determined Input Tests  
  - Inputs change over time
  - Intended to broaden coverage rather than provide strict regression guarantees
  - Useful for detecting degradation or unexpected behavior

Failures in these tests should be monitored and investigated but do not necessarily block merges unless persistent.

### Rationale
- Deterministic and safety-critical tests run frequently to prevent regressions
- Expensive and probabilistic tests run less often to control cost and flakiness
- This balance provides fast developer feedback while still evaluating real-world LLM behavior over time

