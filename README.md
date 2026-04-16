# Dirty Room Image Classifier

This repository contains the MVP implementation and planning documents for an internal AWS-backed service that analyzes an uploaded room image and classifies its cleanliness.

## MVP Goal

Build an AWS-native service that accepts a single uploaded image, evaluates room cleanliness, and returns:

- a 3-tier classification: `clean`, `borderline`, or `dirty`
- a confidence score
- a `needs_review` flag
- short explainable notes for staff
- image quality feedback when a photo should be retaken

The initial release is planning and documentation only. No runtime application code is included yet.

## Current Phase

The project is in an internal staging and validation phase. The current goal is to make the service easy for product stakeholders to test with real images before any production rollout.

## Intended Stack

- AWS Lambda
- Python + FastAPI
- Amazon S3
- Amazon Bedrock
- Amazon Rekognition
- Amazon DynamoDB
- Amazon CloudWatch

## Documentation

- [Product Requirements](docs/product-requirements.md)
- [Architecture Plan](docs/architecture-plan.md)
- [Implementation Roadmap](docs/implementation-roadmap.md)
- [AWS Setup Checklist](docs/aws-setup-checklist.md)
- [Implementation Learnings](docs/implementation-learnings.md)
- [Optimization Playbook](docs/optimization-playbook.md)
- [Staging Live Testing Plan](docs/staging-live-testing-plan.md)

## Planned Workflow

1. Keep the classifier, review workflow, and reporting path stable in staging.
2. Expand the golden test set and improve prompt/policy accuracy.
3. Expose a real staging endpoint and lightweight interfaces for image upload and result review.
4. Run structured product testing before deciding what belongs in a production rollout.

## Working Principles

- Prefer AWS-managed services when they meaningfully reduce complexity.
- Keep monthly cost low, with a target near free-tier usage and a hard ceiling of $50.
- Bias the system to avoid classifying a dirty room as clean.
- Keep predictions explainable and admin-reviewable.
