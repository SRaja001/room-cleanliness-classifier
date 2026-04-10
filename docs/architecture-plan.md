# Architecture Plan

## Recommendation

Use a hybrid AWS-managed architecture:

- Amazon Bedrock for primary vision-based cleanliness classification
- Amazon Rekognition for image quality checks and supporting signals
- Deterministic policy rules in Lambda to keep behavior conservative and explainable

This approach best balances low cost, low operational complexity, and acceptable accuracy for an MVP with no training data.

## Why This Approach

The product needs a semantic judgment of cleanliness, not just object detection. Rekognition alone can help with labels and image quality, but it does not natively understand the business rubric for `clean`, `borderline`, and `dirty`. A multimodal model in Bedrock can reason over the scene using a defined rubric, while Rekognition and rules provide objective quality checks and safer review thresholds.

## AWS Services

- API Gateway for the upload and test API
- AWS Lambda for the application runtime
- FastAPI as the application framework
- Amazon S3 for private image storage
- Amazon Bedrock for primary vision inference
- Amazon Rekognition for quality analysis and optional supporting labels
- Amazon DynamoDB for predictions, review state, and comments
- Amazon CloudWatch for logs, metrics, and alerting

## End-to-End Flow

1. Client uploads one image to the service.
2. The service stores the original image in a private S3 bucket.
3. Rekognition checks image quality and can optionally return supporting labels.
4. Bedrock evaluates the image against the cleanliness rubric and returns structured output.
5. Lambda applies deterministic policies, including conservative handling of low confidence and poor image quality.
6. The final result and metadata are stored in DynamoDB.
7. An admin reviews the result and can add comments or override the final decision.

## Option Comparison

### Managed Vision Rules Only

Use Rekognition and a Lambda-based rule engine only.

- Lowest cost
- Lowest complexity
- Lowest expected accuracy for cleanliness as a business concept
- Best only as a baseline, not as the main recommendation

### Multimodal Model Only

Use Bedrock vision inference without Rekognition.

- Low complexity
- Better semantic reasoning than rules only
- Weaker guardrails around image quality and deterministic review behavior

### Hybrid Managed Approach

Use Bedrock for classification and Rekognition plus policy rules for guardrails.

- Moderate complexity
- Strongest MVP fit
- Maintains explainability while staying AWS-native

### Custom ML

Use Rekognition Custom Labels or SageMaker with a trained classifier.

- Highest complexity
- Requires labeled training data that does not exist yet
- Not appropriate for the first release

## Draft Service Contract

### Primary Operation

`classify_room_cleanliness`

### Request

- image upload or S3 object reference
- optional metadata such as room type or source
- optional `image_role`, defaulting to `after`

### Response

- `classification`
- `confidence`
- `needs_review`
- `recommended_action`
- `visible_reasons`
- `image_quality`
- internal provider metadata for tracing if needed

## Key Technical Principles

- Use IAM roles instead of embedded API keys for AWS service access
- Keep S3 private by default
- Treat poor image quality as a first-class product outcome
- Favor false review escalation over false cleanliness approval
