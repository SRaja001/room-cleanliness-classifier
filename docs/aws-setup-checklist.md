# AWS Setup Checklist

## Purpose

This checklist prepares the project for implementation without requiring runtime code yet. It focuses on the AWS resources and security posture needed for the MVP.

## Required Services

- API Gateway
- AWS Lambda
- Amazon S3
- Amazon Bedrock
- Amazon Rekognition
- Amazon DynamoDB
- Amazon CloudWatch
- AWS IAM
- AWS KMS if bucket or table encryption keys need to be customer-managed

## Identity and Authentication

- Use IAM roles for Lambda to access AWS services
- Do not embed AWS API keys in code
- Do not rely on static credentials stored in the repository
- Use Secrets Manager or SSM Parameter Store for any non-AWS application secrets

## S3 Requirements

- Create a private bucket for original image storage
- Block public access at the bucket level
- Enable server-side encryption
- Define object key conventions for traceability
- Decide whether to store thumbnails or processed outputs separately

## Bedrock Requirements

- Confirm Bedrock is enabled in the target AWS region
- Request access to at least one image-capable model
- Confirm the Lambda role can invoke the selected model
- Record the chosen model and region in implementation docs

## Rekognition Requirements

- Confirm the Lambda role can call the specific Rekognition APIs used for quality checks
- Decide whether label detection is needed in addition to quality validation

## DynamoDB Requirements

- Create a table for prediction records
- Store image reference, classification, confidence, review status, and admin comments
- Decide on retention and audit fields before implementation

## Logging and Monitoring

- Enable CloudWatch logs for Lambda
- Track request count, failures, latency, and model call failures
- Add logging around admin overrides so later evaluation is possible

## Security and Privacy

- Keep uploaded images private
- Restrict access to authorized internal users and services only
- Apply least-privilege IAM policies
- Document which roles can read images and review results
- Confirm whether VPC placement is required by internal policy

## Operational Decisions to Confirm

- AWS account and region for deployment
- Bedrock model availability in that region
- Naming conventions for buckets, tables, and functions
- Whether presigned S3 uploads will be used
- Whether customer-managed KMS keys are required

## Day 1 Required vs Later

### Required for MVP

- private S3 bucket
- Lambda execution role
- Bedrock model access
- Rekognition permissions
- DynamoDB table
- CloudWatch logging

### Can Be Added Later

- stricter monitoring and alerting
- VPC isolation
- customer-managed KMS keys
- lifecycle rules and archival policies
- infrastructure as code
