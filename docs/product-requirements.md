# Product Requirements

## Overview

The MVP is an internal service that classifies the cleanliness of a room from a single uploaded image. The service is intended to support operational review, not full automation on day one.

## Product Goal

Determine whether an uploaded room image should be treated as:

- `clean`
- `borderline`
- `dirty`

Each result must also include:

- a confidence score
- a `needs_review` flag
- short notes explaining the visible reasons for the classification
- image quality feedback when the image should be retaken

## Business Context

The long-term goal is to support approval and rejection decisions with staff-facing notes and the stored image. The MVP will remain admin-gated so that predictions can be reviewed before they are used operationally.

## Users

- Internal admins reviewing room cleanliness predictions
- Internal operators testing model behavior during MVP validation

## Input Assumptions

- One image per request
- The initial MVP treats the image as an `after` image
- Images are submitted through an API
- Traffic is low volume, around 5 to 10 images per day
- Images may vary in lighting, blur, and framing, so quality checks are required

## Cleanliness Rubric

### Clean

The room appears orderly and ready to approve. There are no clearly visible signs of trash, clutter, major stains, dishes, or other obvious cleanliness issues.

### Borderline

The room is mostly acceptable but contains visible ambiguity or minor issues that make automatic confidence unsafe. Examples include limited clutter, unclear surfaces, partial room visibility, or mixed signals caused by image quality.

### Dirty

The room shows clear visible cleanliness problems such as clutter, trash, messy surfaces, unmade sleeping areas, or other obvious issues that should prevent approval without human intervention.

## Review Policy

- Every MVP result is reviewed by an admin
- The system should be conservative when returning `clean`
- Any uncertain or poor-quality result should set `needs_review=true`
- The system should never optimize for speed at the expense of missing a dirty room

## Success Criteria

The initial acceptance bar for MVP validation is:

- run at least 10 test images through the service
- produce a classification for each image
- do not mark any dirty rooms as clean

## Non-Functional Requirements

- Near-real-time response for internal testing
- Explainable outputs for product and engineering review
- Monthly operating cost should stay below $50
- Images must be stored in a private S3 bucket

## Out of Scope for MVP

- True before-and-after comparison
- Multi-image submissions
- Custom-trained ML models
- End-user capture workflow
- Automatic production approval without admin confirmation

## Draft Output Contract

The MVP response should include:

- `classification`
- `confidence`
- `needs_review`
- `recommended_action`
- `visible_reasons`
- `image_quality`

## Open Follow-Up Items

- Define a tighter approval rubric once real test images are collected
- Decide how much structured metadata should accompany an image
- Decide when admin review can be reduced for high-confidence cases
