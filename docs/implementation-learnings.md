# Implementation Learnings

This document captures the major product, architecture, and implementation learnings discovered during planning and early MVP delivery for the room-cleanliness classifier.

It is intentionally explicit so future work does not lose the context behind decisions, test outcomes, and AWS integration details.

## Product Learnings

### Cleanliness must be defined as a product rubric, not a vague model prompt

The biggest product learning is that "cleanliness" is not a default computer-vision concept. The system performs better when the prompt encodes a business rubric instead of asking a model to guess what clean or dirty means.

The MVP rubric that performed best in testing was:

- `clean`: orderly room overall; floor mostly clear; no obvious piles of laundry or trash; a lightly rumpled bed and normal personal items are acceptable
- `borderline`: unsupported scene, ambiguous image, or light clutter that does not clearly justify `dirty`
- `dirty`: obvious piles of clothes, trash, messy surfaces, or significant floor clutter

### Lived-in does not mean dirty

This was a critical product insight from the clean-room test image.

The clean bedroom was initially misclassified because the model treated normal personal items, books, a lightly rumpled bed, and a generally lived-in appearance as evidence against cleanliness. This was incorrect for the product.

The prompt must explicitly tell the model that:

- books, toys, decor, and personal items can still be compatible with `clean`
- a lightly rumpled bed can still be `clean`
- the absence of reject-level clutter matters more than perfect staging

### Unsupported scenes need explicit handling

A hallway is visually tidy, but it is not a room we want to score for housekeeping purposes.

This means the classifier is doing two jobs:

1. Determine whether the image is a supported scene for evaluation
2. If supported, assign a cleanliness score

Without explicit instructions, a model may classify an unsupported but tidy hallway as `clean`, which is product-correct from a visual-tidiness perspective but wrong for the workflow.

For the MVP, the expected behavior is:

- unsupported scene like a hallway -> `borderline` with explanation

## Model Selection Learnings

### Option 2 was the best-performing approach in live testing

Three live options were compared on the same three-image batch:

- dirty room -> expected `dirty`
- hallway -> expected `borderline`
- clean room -> expected `clean`

The options were:

1. Tuned rubric prompt on `writer.palmyra-vision-7b`
2. Tuned rubric prompt on `amazon.nova-lite-v1:0`
3. Two-stage hybrid prompt plus deterministic mapping on `amazon.nova-lite-v1:0`

Live results:

- Option 1: `2/3`
- Option 2: `3/3`
- Option 3: `2/3`

The best-performing current choice is:

- `amazon.nova-lite-v1:0`
- with the tuned single-stage rubric prompt

### Why Option 2 worked best

Option 2 improved two things simultaneously:

- the model changed from `writer.palmyra-vision-7b` to `amazon.nova-lite-v1:0`
- the prompt became much more explicit about supported scenes and the difference between `clean`, `borderline`, and `dirty`

Observed behavior:

- `writer.palmyra-vision-7b` improved after prompt tuning and correctly classified the clean room, but still mislabeled the hallway as `clean`
- `amazon.nova-lite-v1:0` followed the rubric more reliably and correctly classified all three examples

Current recommendation:

- use `amazon.nova-lite-v1:0` as the default MVP model unless later testing disproves it

### Two-stage hybrid logic is promising but currently too strict

The hybrid approach asked the model for:

- scene type
- whether the scene is supported
- severe issues
- moderate issues
- minor issues
- a cleanliness score

The deterministic mapping layer then converted those fields into the final label.

This approach is attractive for explainability, but the first implementation was too harsh on tidy lived-in rooms. The clean bedroom was downgraded to `borderline` because the mapping logic treated minor or moderate issues too aggressively.

Learning:

- a two-stage system may be useful later
- but the policy layer must be tuned carefully or it can become stricter than the model itself

## AWS Bedrock Learnings

### Bedrock was suitable for low-volume MVP experimentation

At the current MVP volume of roughly 5 to 10 images per day, Bedrock multimodal inference is operationally feasible and should remain well under the target monthly budget if model calls are kept compact and intentional.

The actual live dirty-room test with `writer.palmyra-vision-7b` returned:

- `input_tokens`: `1265`
- `output_tokens`: `69`
- `total_tokens`: `1334`
- estimated cost: `0.00023115 USD`

This validated that:

- usage data can be extracted from the Bedrock response
- per-request cost estimates can be logged at the application layer

### Bedrock prompt quality matters more than expected

The prompt change had a real measurable effect on correctness. This is important because it means we do not yet need training data or a custom model to get a much better MVP result.

Before considering custom training, the team should first exhaust:

- prompt rubric tuning
- model selection
- deterministic review policy tuning
- small golden test-set evaluation

### Keep model usage visible in the API

The service now surfaces model version and token usage in the classify response shape. This is useful for:

- budget monitoring
- model-comparison experiments
- debugging behavior changes across model swaps

This should remain part of internal responses during MVP.

## AWS Rekognition Learnings

### Rekognition is useful for image quality checks, not semantic cleanliness scoring

Rekognition worked well for image quality analysis, but it should not be treated as the primary cleanliness classifier.

The most useful role for Rekognition in this system is:

- image quality validation
- retake guidance
- basic supporting signals

Rekognition is not sufficient by itself to define room cleanliness, because cleanliness is a product-specific semantic judgment rather than a native object-detection category.

### Rekognition and Bedrock should be orchestrated by the application, not treated as a direct service-to-service pipeline

There is no special Rekognition-to-Bedrock integration that solves the classification problem automatically.

The correct application pattern for this MVP is:

1. store the image in S3
2. use Rekognition for image-quality and supporting checks
3. use Bedrock for semantic cleanliness reasoning
4. apply product policy in application code
5. persist the result in DynamoDB

This is important because:

- Rekognition and Bedrock solve different problems
- the business logic lives in the service, not in an AWS-native handoff between those two services
- future changes to review thresholds or supported-scene logic should happen in the app layer

### Rekognition integration worked once the image pipeline was stable

The live S3 and Rekognition smoke tests passed after wiring the storage path correctly.

Observed successful behavior:

- image upload to private S3
- Rekognition quality evaluation
- quality feedback surfaced to the app

Example quality output from a real test:

- brightness and sharpness values were returned
- the image passed quality validation

Implementation note:

- the most reliable flow was local image -> application upload path -> private S3 object -> Rekognition read from S3-backed bytes or loaded object data
- keeping a stable storage path reduced ambiguity and made troubleshooting much easier than trying to reason about loosely managed local test inputs

### Rekognition needs a predictable image format path

The workflow was more reliable once images were normalized to supported formats and stored consistently in S3. For ad hoc tests, converting local `.webp` images to a more predictable format such as JPEG simplified the path through AWS services and reduced format ambiguity during testing.

## Integration and Environment Learnings

### Network-restricted local environments can fail even when AWS code is correct

One live comparison run initially failed because the local execution environment could not resolve the S3 endpoint through the sandboxed network path. The code itself was not the problem.

Learning:

- when a cloud integration suddenly fails with DNS or endpoint-resolution errors, check the execution environment before assuming the AWS logic is broken
- a successful rerun outside the restricted sandbox confirmed the implementation path was valid

### The application should keep AWS integrations independently switchable

It was useful to keep separate enablement flags for:

- S3
- Rekognition
- Bedrock
- DynamoDB

This allowed the project to test each AWS slice independently and avoid unnecessary spend while building incrementally.

## S3 Learnings

### Private bucket storage is the right default

The bucket used for MVP testing was created as:

- private
- server-side encrypted with AES256

This matched the requirement that uploaded images be stored privately and created a clean baseline for production hardening later.

### Named test objects are worth keeping

The named test assets were clearer than anonymous upload keys.

Useful pattern:

- `named-tests/dirty-room-bedroom.jpg`
- `named-tests/hallway-not-room.jpg`
- `named-tests/clean-room-bedroom.jpg`

This made evaluation easier and reduced ambiguity about what each image represented.

## DynamoDB Learnings

### On-demand billing is the correct low-cost mode for MVP

The DynamoDB table was created using:

- `PAY_PER_REQUEST`

This is the correct cost choice for low and uneven traffic because there is no reason to provision capacity for an MVP with single-digit daily volume.

### Python floats must be normalized before writing nested payloads

An actual implementation issue occurred when persisting prediction data to DynamoDB.

Problem:

- DynamoDB rejected Python `float` values inside nested payloads

Fix:

- recursively convert numeric payload values into DynamoDB-safe types before writing

This is an important implementation detail for any future schema changes.

### One-table MVP design is sufficient

For the current phase, storing prediction data and admin review information in the same item keyed by `prediction_id` is acceptable and keeps the persistence layer simple.

## Infrastructure and Authentication Learnings

### IAM roles are the right long-term pattern, not embedded API keys

For AWS-native runtime deployment, the preferred pattern is:

- Lambda execution role with IAM permissions

Not:

- hardcoded API keys
- secrets committed in code

Temporary development access was done with local AWS credentials, but the production target should remain role-based access.

### AWS credentials should never be pasted into chat or committed

The correct operational pattern is:

- configure credentials locally via AWS CLI or environment variables
- let boto3 and the AWS SDK load them from the environment
- keep keys out of the repo and out of documentation

This remains a standing rule for all future work.

## Testing Learnings

### Real-image testing was essential

The service needed real-image validation, not just unit tests, because the product quality depends on multimodal judgment.

The live image tests revealed issues that local logic tests would not have caught:

- clean room initially scoring too harshly
- hallway being treated as a clean room by one model
- prompt wording materially affecting results

### A golden evaluation set is necessary

The three-image batch created an initial golden set:

- dirty room
- hallway
- clean room

This should be preserved and expanded over time. Future model or prompt changes should always be checked against a fixed expected-label set before promotion.

### Test each integration phase before moving on

The working delivery pattern for this project has been:

1. implement one AWS slice
2. verify locally with unit tests
3. run a live smoke test
4. then move to the next integration

This approach worked well and should remain the default.

## Current Recommended MVP Stack

Based on the work completed so far, the current recommended MVP stack is:

- FastAPI in Lambda
- private S3 bucket for image storage
- Rekognition for image quality checks
- Bedrock multimodal inference for cleanliness scoring
- DynamoDB for predictions and review persistence
- `amazon.nova-lite-v1:0` as the default model
- conservative review policy with `needs_review=true` during MVP

## Open Follow-Ups

These are the next areas that still need deliberate tuning:

- promote `amazon.nova-lite-v1:0` into the main classify path as the default
- preserve the option-comparison script for repeatable experiments
- expand the golden image set beyond the initial three samples
- refine unsupported-scene handling if the product later wants an explicit `invalid` state
- add budget alerts and stronger cost monitoring if live usage grows
