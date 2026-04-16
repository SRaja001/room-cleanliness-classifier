# Optimization Playbook

This document captures the optimization steps for the room-cleanliness classifier so future tuning work is deliberate, testable, and easy to revisit.

The goal is not just to improve accuracy. The goal is to improve:

- classification quality
- explainability
- review efficiency
- cost control
- product confidence

## Current Baseline

Current MVP baseline:

- primary classifier: `amazon.nova-lite-v1:0`
- image quality checks: Amazon Rekognition
- storage: private S3
- persistence: DynamoDB
- review workflow: admin review and summary reporting
- review posture: conservative, with `needs_review=true` still acceptable for MVP

The classifier currently performs well on the first named test set:

- dirty room -> `dirty`
- hallway / unsupported scene -> `borderline`
- clean room -> `clean`

## Optimization Goals

Optimization should focus on five areas:

1. Accuracy
2. Review load
3. Explainability
4. Cost
5. Robustness on edge cases

## Optimization Order

Use this order unless there is a clear reason to do otherwise.

### 1. Expand the golden test set

Before changing prompts or policies, build a better evaluation set.

Add examples for:

- clearly clean bedrooms
- clearly dirty bedrooms
- borderline rooms
- unsupported scenes such as hallways or non-room spaces
- low-quality images
- difficult lived-in but acceptable rooms
- rooms with unusual decor that should still classify correctly

For every image, store:

- image label or filename
- expected classification
- notes on why the label is correct
- whether the image is supported or unsupported

Why this matters:

- prompt tuning without a stable benchmark leads to guesswork
- future model swaps become much easier to evaluate
- product stakeholders can align on disagreements explicitly

### 2. Tune the prompt rubric before changing architecture

Prompt quality has already shown a large impact on results.

Tune:

- what counts as `clean`
- what counts as `dirty`
- how to treat lived-in rooms
- how to treat unsupported scenes
- how to phrase visible reasons

Prompt tuning rules:

- keep outputs structured
- keep the rubric concrete
- avoid subjective wording like "messy" without examples
- explicitly say what should not count against a room

Why this is worth pursuing:

- cheapest improvement path
- lowest engineering overhead
- easiest to compare with the current baseline

### 3. Tune product policy separately from model behavior

The model and the review policy should be optimized separately.

Questions to revisit:

- when should `clean` still require review?
- when should poor quality force `retake`?
- should unsupported scenes remain `borderline` externally?
- when should confidence thresholds be tightened or relaxed?

Why this matters:

- a strong model can still produce poor product behavior if the policy is too harsh
- this was already observed in the first two-stage hybrid attempt

### 4. Measure review overrides

Add reporting that makes it easy to inspect:

- model classification vs final admin classification
- top sources of disagreement
- unsupported-scene error rate
- clean-room false downgrades
- dirty-room false clears

Why this matters:

- admin overrides become labeled product evidence
- this is the cleanest path toward deciding whether more automation is safe

### 5. Optimize cost after the evaluation path is stable

Current cost is low enough that accuracy and product confidence matter more than tiny token savings.

Still, cost should be monitored in a structured way.

Track:

- estimated model cost per request
- daily request volume
- average tokens per request
- model used per request

Cost optimization moves to consider later:

- shorten prompts where accuracy is unaffected
- reduce unnecessary repeat calls
- send fewer fields when they do not improve outcomes
- keep Rekognition and Bedrock calls independent and intentional

### 6. Only revisit hybrid logic after the golden set grows

The first two-stage hybrid attempt was more explainable but too strict on clean lived-in rooms.

Revisit hybrid logic only after:

- more labeled examples exist
- disagreement patterns are clearer
- the one-stage Nova Lite baseline is no longer good enough

Potential future hybrid inputs:

- supported scene
- severe issues
- moderate issues
- cleanliness score
- internal invalid-scene status

## Optimization Checklist

Use this checklist before promoting tuning changes:

- update the golden test set if needed
- run the named-image evaluation script
- compare before/after accuracy
- compare before/after review load
- compare before/after estimated cost
- document what changed and why
- keep one clear rollback point

## Metrics To Watch

Product-facing metrics:

- dirty rooms incorrectly marked clean
- clean rooms incorrectly downgraded
- unsupported scenes incorrectly treated as valid rooms
- review rate
- override rate

Engineering-facing metrics:

- median and p95 response time
- Bedrock token usage
- estimated cost per image
- Rekognition retake rate
- schema or parsing failures

## Recommended Next Optimization Slice

The highest-value optimization slice from here is:

1. expand the golden image set
2. add a repeatable evaluation harness
3. report pass/fail per image and overall disagreement rate

This should happen before any major architectural change.
