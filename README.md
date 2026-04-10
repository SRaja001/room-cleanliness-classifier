# Dirty Room Image Classifier

This repository contains the planning and design documents for an internal MCP-backed service that analyzes an uploaded room image and classifies its cleanliness.

## MVP Goal

Build an AWS-native service that accepts a single uploaded image, evaluates room cleanliness, and returns:

- a 3-tier classification: `clean`, `borderline`, or `dirty`
- a confidence score
- a `needs_review` flag
- short explainable notes for staff
- image quality feedback when a photo should be retaken

The initial release is planning and documentation only. No runtime application code is included yet.

## Current Phase

The project is in the documentation and architecture phase. The immediate goal is to align product, engineering, and AWS setup decisions before opening implementation PRs.

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

## Planned Workflow

1. Finalize documentation, requirements, and architecture decisions.
2. Confirm AWS service access, IAM roles, and security constraints.
3. Implement the MVP service and internal review workflow.
4. Evaluate early predictions, tune thresholds, and decide whether more automation is safe.

## Working Principles

- Prefer AWS-managed services when they meaningfully reduce complexity.
- Keep monthly cost low, with a target near free-tier usage and a hard ceiling of $50.
- Bias the system to avoid classifying a dirty room as clean.
- Keep predictions explainable and admin-reviewable.
