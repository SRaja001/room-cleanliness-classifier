from dataclasses import dataclass

from app.core.config import AppConfig
from app.services.bedrock import BedrockVisionClient
from app.services.classifier import ClassifierService
from app.services.policy import ReviewPolicy
from app.services.rekognition import RekognitionClient
from app.services.reviews import ReviewService
from app.services.repository import (
    DynamoDbPredictionRepository,
    InMemoryPredictionRepository,
)
from app.services.storage import ImageStorageClient


@dataclass(frozen=True)
class ApplicationServices:
    classifier_service: ClassifierService
    review_service: ReviewService


def create_application_services(*, config: AppConfig) -> ApplicationServices:
    s3_client = None
    rekognition_client = None
    bedrock_client = None
    dynamodb_resource = None

    if config.aws_integration_enabled:
        try:
            import boto3  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "AWS integration is enabled, but boto3 is not installed."
            ) from exc

        session = boto3.Session(region_name=config.aws_region)
        if config.s3_enabled:
            s3_client = session.client("s3")
        if config.rekognition_enabled:
            rekognition_client = session.client("rekognition")
        if config.bedrock_enabled:
            bedrock_client = session.client("bedrock-runtime")
        if config.dynamodb_enabled:
            dynamodb_resource = session.resource("dynamodb")

    storage_client = ImageStorageClient(config=config, s3_client=s3_client)
    if config.dynamodb_enabled:
        if dynamodb_resource is None:
            raise RuntimeError(
                "DynamoDB integration is enabled, but AWS integration is not available."
            )
        repository = DynamoDbPredictionRepository(
            table=dynamodb_resource.Table(config.dynamodb_table_name)
        )
    else:
        repository = InMemoryPredictionRepository()
    classifier_service = ClassifierService(
        rekognition_client=RekognitionClient(
            config=config,
            rekognition_client=rekognition_client,
        ),
        bedrock_client=BedrockVisionClient(
            config=config,
            bedrock_client=bedrock_client,
            storage_client=storage_client,
        ),
        review_policy=ReviewPolicy(config=config),
        storage_client=storage_client,
        repository=repository,
        config=config,
    )
    return ApplicationServices(
        classifier_service=classifier_service,
        review_service=ReviewService(repository=repository),
    )
