from pathlib import Path


def test_dynamodb_scripts_exist() -> None:
    assert Path("scripts/create_dynamodb_table.py").exists()
    assert Path("scripts/live_dynamodb_smoke_test.py").exists()
    assert Path("scripts/create_s3_bucket.py").exists()
    assert Path("scripts/live_s3_rekognition_smoke_test.py").exists()
    assert Path("scripts/live_local_image_s3_rekognition_test.py").exists()
    assert Path("scripts/live_local_image_classify_test.py").exists()
