"""STS credential issuance service for direct S3 uploads."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.config import settings
from app.schemas.upload import STSCredentials, UploadTarget


class STSService:
    """Service for issuing scoped AWS STS credentials for direct S3 uploads."""

    def __init__(self):
        """Initialize STS service."""
        pass

    async def issue_sts_credentials(
        self,
        agent_id: UUID,
        org_id: UUID,
        job_id: UUID,
        file_targets: list[dict]
    ) -> dict:
        """Issue temporary STS credentials for direct S3 upload.

        Args:
            agent_id: Agent requesting credentials
            org_id: Organization ID for tenant isolation
            job_id: Job ID for path scoping
            file_targets: List of files with their S3 upload paths
                Format: [{"file_id": UUID, "oa_asset_id": str, "filename": str}, ...]

        Returns:
            Dictionary with "credentials" (STSCredentials) and
            "upload_targets" (list[UploadTarget])

        Raises:
            Exception: If AWS STS call fails
        """
        # Generate IAM policy scoped to specific S3 paths
        policy = self._generate_upload_policy(org_id, job_id, agent_id)

        # For MVP, we'll mock the STS credentials
        # In production, this would call boto3.client('sts').assume_role()
        expiry = datetime.now(UTC) + timedelta(seconds=settings.sts_token_duration_seconds)

        credentials = STSCredentials(
            access_key=f"ASIA{agent_id.hex[:12].upper()}",
            secret_key=f"mock_secret_{agent_id.hex[:16]}",
            session_token=f"mock_token_{agent_id.hex[:20]}",
            expiry=expiry
        )

        # Build upload targets
        upload_targets = []
        for target in file_targets:
            s3_key = self._generate_s3_key(
                org_id=org_id,
                job_id=job_id,
                agent_id=agent_id,
                file_id=target["file_id"],
                filename=target["filename"]
            )

            upload_targets.append(
                UploadTarget(
                    file_id=target["file_id"],
                    bucket=settings.aws_s3_bucket_name,
                    key=s3_key,
                    oa_asset_id=target["oa_asset_id"]
                )
            )

        return {
            "credentials": credentials,
            "upload_targets": upload_targets
        }

    def _generate_upload_policy(
        self,
        org_id: UUID,
        job_id: UUID,
        agent_id: UUID
    ) -> dict:
        """Generate scoped IAM policy for S3 upload.

        Args:
            org_id: Organization UUID
            job_id: Job UUID
            agent_id: Agent UUID

        Returns:
            IAM policy document as dict
        """
        # Construct resource ARN pattern
        resource_pattern = (
            f"arn:aws:s3:::{settings.aws_s3_bucket_name}/"
            f"uploads/{org_id}/{job_id}/{agent_id}/*"
        )

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:AbortMultipartUpload"
                    ],
                    "Resource": resource_pattern
                }
            ]
        }

        return policy

    def _generate_s3_key(
        self,
        org_id: UUID,
        job_id: UUID,
        agent_id: UUID,
        file_id: UUID,
        filename: str
    ) -> str:
        """Generate S3 object key for a file upload.

        Args:
            org_id: Organization UUID
            job_id: Job UUID
            agent_id: Agent UUID
            file_id: File UUID
            filename: Original filename

        Returns:
            S3 object key string
        """
        return f"uploads/{org_id}/{job_id}/{agent_id}/{file_id}/{filename}"
