# Staging Live Testing Plan

This document describes how to get the room-cleanliness classifier ready for staging-style live testing with product stakeholders.

The purpose of this environment is:

- allow real users to upload images
- show predictions and explanations through a real endpoint
- allow reviewers to inspect results and provide feedback
- support product iteration before any production rollout

This is not a production plan. It is a practical internal testing plan.

## Staging Goal

Create a lightweight staging environment where product people can:

1. upload a room image
2. submit it to the classifier through a real HTTP endpoint
3. see the classification, confidence, reasons, and quality feedback
4. review recent predictions
5. leave feedback on whether the result looks right

## What Staging Needs

The staging environment should include four visible surfaces:

1. Upload interface
2. Results view
3. Review queue
4. Summary/reporting view

## Recommended Staging Architecture

Use the existing backend service and wrap it in a lightweight internal-facing web interface.

Recommended components:

- FastAPI app as the core API
- AWS Lambda for runtime
- API Gateway for HTTP exposure
- private S3 for uploaded images
- DynamoDB for predictions and reviews
- optional simple frontend, served either:
  - from a second lightweight app
  - or from static files plus API calls

## Staging Interfaces

### 1. Upload Interface

The upload interface should be intentionally minimal.

Required fields:

- image file
- optional room type
- optional source tag

Required behavior:

- show upload status
- show response after classification
- display quality feedback if the image should be retaken

Nice-to-have:

- drag and drop upload
- preview before submission
- display the uploaded image alongside the result

### 2. Results View

The results screen should show:

- uploaded image
- classification
- confidence
- recommended action
- visible reasons
- image quality result
- model version
- estimated cost

The results view should be explainable to non-engineers.

### 3. Review Queue

The review queue should start simple and internal.

Minimum features:

- list recent predictions
- filter to `pending_only=true`
- open a prediction detail view
- submit an admin review

Useful additions:

- filter by classification
- filter by source
- filter by room type

### 4. Summary / Reporting View

The summary view should show:

- total predictions
- reviewed predictions
- pending review count
- classification breakdown
- final review breakdown
- estimated model-cost total

This is mainly for product and ops visibility during testing.

## Recommended Implementation Order

### Phase 1. Expose a staging API endpoint

Use the existing FastAPI app behind API Gateway and Lambda.

Tasks:

- package the service for Lambda
- define staging environment variables
- configure IAM role for S3, Rekognition, Bedrock, and DynamoDB
- verify the existing endpoints through a deployed URL

Success criteria:

- internal users can hit a live endpoint
- classify and review endpoints work in staging

### Phase 2. Build a simple internal upload page

Build a lightweight internal-only interface that calls the staging API.

Tasks:

- add image upload UI
- call `/classify`
- render the response
- display image and output together

Recommended implementation style:

- keep it simple
- avoid investing in a complex design system yet
- optimize for ease of testing, not polish

### Phase 3. Build a review page

Tasks:

- list predictions
- filter pending predictions
- open prediction detail
- submit admin review comments

This is where product stakeholders and reviewers can start participating.

### Phase 4. Add summary visibility

Tasks:

- show summary metrics from `/reports/summary`
- optionally show recent disagreements or review outcomes

## API Endpoints To Support Staging

Already available:

- `POST /classify`
- `POST /predictions/{prediction_id}/review`
- `GET /predictions/{prediction_id}`
- `GET /predictions`
- `GET /reports/summary`

Most likely next additions for staging:

- direct file-upload route if we want the browser to send files more naturally
- pre-signed S3 upload support if browser uploads should bypass the app server

## Recommended Near-Term UI Scope

For the first staging interface, keep scope small.

Include:

- one upload page
- one result page
- one review queue page
- one prediction detail page

Do not include yet:

- end-user authentication complexity beyond internal access control
- polished production branding
- advanced workflow automation
- mobile-native apps

## Security And Access For Staging

Staging should still be private.

Minimum constraints:

- private S3 bucket
- internal-only API access if possible
- no public bucket objects
- no secrets in client code
- environment-based AWS credentials only

If needed, basic auth or internal access controls are acceptable for staging.

## Suggested Product Testing Workflow

Use this workflow with product stakeholders:

1. upload an image
2. inspect the classifier result
3. record whether the result feels correct
4. if needed, submit an admin review
5. review summary metrics after multiple tests

Capture specifically:

- false `clean`
- false `dirty`
- unsupported-scene handling
- quality-feedback usefulness
- explanation quality

## Acceptance Criteria For Staging

The staging environment is ready when:

- a product stakeholder can upload a real image without engineering help
- the system shows classification and reasons clearly
- recent predictions can be reviewed through a simple queue
- feedback can be submitted through the UI
- the backend summary updates correctly

## Recommended Next Build Slice

The next implementation slice should be:

1. deploy the FastAPI app behind a real staging endpoint
2. create a minimal upload-and-results UI
3. wire the review queue to the existing endpoints

That gets product people involved quickly without overbuilding.
