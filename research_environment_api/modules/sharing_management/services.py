from research_environment_api.modules.app import app
from research_environment_api.modules.sharing_management import entities, enums, models

from google.cloud.storage import Bucket as GCPBucket


def create_shared_bucket(shared_bucket_creation: entities.SharedBucketCreation):
    storage_client = app.config.google_cloud_storage_client
    bucket = storage_client.bucket(shared_bucket_creation.bucket_name)
    bucket.storage_class = shared_bucket_creation.storage_class

    bucket.labels["cloud_identity_username"] = shared_bucket_creation.username

    storage_client.create_bucket(
        bucket,
        location=shared_bucket_creation.region.value.upper(),
        project=shared_bucket_creation.workspace_project_id,
    )
    _add_iam_permissions(
        bucket, shared_bucket_creation.user_email, enums.IamSharingRole.ADMIN
    )


def delete_shared_bucket(shared_bucket_deletion: entities.SharedBucketDeletion):
    storage_client = app.config.google_cloud_storage_client
    bucket = storage_client.bucket(shared_bucket_deletion.bucket_name)
    with app.database_session() as session:
        with session.begin():
            sharing_metadata = (
                session.query(models.SharingData)
                .filter_by(bucket_name=shared_bucket_deletion.bucket_name)
                .one()
            )

            bucket.delete()

            sharing_metadata.state = enums.SharingState.REVOKED


def _add_iam_permissions(
    bucket: GCPBucket, user_email: str, role: enums.IamSharingRole
):
    policy = bucket.get_iam_policy(requested_policy_version=3)
    user_binding = _get_storage_user_binding_role(policy, role)
    if user_binding:
        return
    policy.bindings.append({"role": role.value, "members": {f"user:{user_email}"}})
    bucket.set_iam_policy(policy)


def _get_storage_user_binding_role(policy, role: str):
    return next(
        filter(
            lambda binding: binding["role"] == role,
            policy.bindings,
        ),
        None,
    )
