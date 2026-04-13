# Implementation Roadmap

## Summary

The project should move in phases, starting with rubric definition and managed-service integration before any consideration of custom ML.

## Phase 0: Definition and Evaluation Setup

- Finalize the cleanliness rubric for `clean`, `borderline`, and `dirty`
- Create an internal 10-image evaluation set
- Define the expected result for each test image
- Confirm what counts as poor image quality and what retake guidance should say

## Phase 1: Managed MVP

- Build the Lambda-hosted FastAPI service
- Add private S3 image storage
- Add Bedrock-based classification with structured responses
- Add Rekognition-based image quality checks
- Add deterministic policy rules for confidence and review handling
- Persist predictions, metadata, and review status
- Provide an admin review path for every MVP result

## Phase 2: Threshold Tuning

- Review the first batch of admin-reviewed results
- Identify any cases where a dirty room was scored too leniently
- Tighten review thresholds and prompt instructions
- Improve staff-facing explanations and retake messaging

## Phase 3: Expansion

- Add explicit support for before or after image role metadata
- Add finer-grained issue notes such as clutter, trash, or surface mess
- Reassess whether some high-confidence cases can bypass admin review
- Reevaluate custom-model options only after enough labeled outcomes exist

## MVP Boundaries

Include:

- one image per request
- 3-tier cleanliness score
- confidence and review flag
- explainable notes
- private S3 storage
- admin review for all predictions

Defer:

- automated production approvals
- multi-image or true before-and-after comparison
- custom-trained classifiers
- full UI workflows beyond what is needed for internal review

## Acceptance Criteria

- The system can process at least 10 test images
- Every response contains the expected structured fields
- No dirty test image is classified as clean
- Poor-quality images receive actionable retake guidance
- The estimated monthly cost stays under the target budget

## Trigger for Custom ML Reconsideration

Only revisit Rekognition Custom Labels or SageMaker when:

- the managed hybrid approach fails to meet accuracy expectations
- enough reviewed images exist to form a trustworthy labeled dataset
- the team is ready to own training, evaluation, and retraining workflows
