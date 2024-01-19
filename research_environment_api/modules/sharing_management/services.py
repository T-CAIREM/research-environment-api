from research_environment_api.modules.app import app
from research_environment_api.modules.sharing_management import entities, enums, models

from typing import Iterable


from google.cloud.storage import Bucket as GCPBucket


def list_accessible_buckets_in_project(
    gcp_project_id: str, username: str, caller_email: str
) -> Iterable[entities.SharedBucket]:
    storage_client = app.config.google_cloud_storage_client
    buckets = storage_client.list_buckets(project=gcp_project_id)
    return [
        entities.SharedBucket.from_storage_instance(bucket, username)
        for bucket in buckets
        if _user_has_access_to_bucket(
            bucket.get_iam_policy(requested_policy_version=3).bindings, caller_email
        )
    ]


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


def share_bucket_to(share_bucket: entities.ShareBucket):
    storage_client = app.config.google_cloud_storage_client
    bucket = storage_client.bucket(share_bucket.bucket_name)
    with app.database_session() as session:
        with session.begin():
            sharing_metadata = (
                session.query(models.SharingData)
                .filter_by(
                    bucket_name=share_bucket.bucket_name,
                    accessor_email=share_bucket.accessor_email,
                )
                .first()
            )
            if sharing_metadata:
                sharing_metadata.state = enums.SharingState.SHARED
            else:
                sharing_metadata = models.SharingData(
                    sharer_email=share_bucket.sharer_email,
                    accessor_email=share_bucket.accessor_email,
                    bucket_name=share_bucket.bucket_name,
                    project_id=share_bucket.project_id,
                    state=enums.SharingState.SHARED,
                )

                session.add(sharing_metadata)
            _add_iam_permissions(
                bucket, share_bucket.accessor_email, enums.IamSharingRole.USER
            )


def revoke_access_to_shared_bucket(
    revoke_shared_bucket_access: entities.RevokeSharedBucketAccess,
):
    storage_client = app.config.google_cloud_storage_client
    bucket = storage_client.bucket(revoke_shared_bucket_access.bucket_name)
    with app.database_session() as session:
        with session.begin():
            sharing_metadata = (
                session.query(models.SharingData)
                .filter_by(
                    bucket_name=revoke_shared_bucket_access.bucket_name,
                    accessor_email=revoke_shared_bucket_access.accessor_email,
                    state=enums.SharingState.SHARED,
                )
                .first()
            )

            _remove_iam_permissions(
                bucket,
                revoke_shared_bucket_access.accessor_email,
                enums.IamSharingRole.USER,
            )
            sharing_metadata.state = enums.SharingState.REVOKED


def generate_signed_url(generate_signed_url_entity: entities.GenerateSignedUrl):
    storage_client = app.config.google_cloud_storage_client
    bucket = storage_client.bucket(generate_signed_url_entity.bucket_name)
    blob = bucket.blob(generate_signed_url_entity.filename.strip("/"))
    signed_url = blob.generate_signed_url(
        api_access_endpoint="https://storage.googleapis.com",
        expiration=int(app.config.gcp_signed_url_expiration_time),
        method="PUT",
        headers={"X-Upload-Content-Length": str(generate_signed_url_entity.size)},
        version="v4",
    )

    return signed_url


def get_shared_bucket_content(
    get_shared_bucket_content_entity: entities.GetSharedBucketContent,
) -> Iterable[entities.SharedBucketObject]:
    storage_client = app.config.google_cloud_storage_client
    bucket_blobs = storage_client.list_blobs(
        get_shared_bucket_content_entity.bucket_name,
        prefix=get_shared_bucket_content_entity.subdir,
        delimiter="/",
    )

    files = [
        entities.SharedBucketObject(
            type=entities.BucketObjectType(entities.BucketObjectType.FILE),
            name=blob.name.split("/")[-1],
            size=_readable_size(blob.size),
            modification_time=blob.updated.strftime("%Y-%m-%d"),
            full_path=blob.name,
        )
        for blob in bucket_blobs
        if blob.size != 0
    ]

    directories = [
        entities.SharedBucketObject(
            type=entities.BucketObjectType(entities.BucketObjectType.DIRECTORY),
            name=prefix.split("/")[-2],
            full_path=prefix,
        )
        for prefix in bucket_blobs.prefixes
    ]
    return files + directories


def create_shared_bucket_directory(
    create_shared_bucket_directory_entity: entities.CreateSharedBucketDirectory,
):
    storage_client = app.config.google_cloud_storage_client
    blob = storage_client.bucket(
        create_shared_bucket_directory_entity.bucket_name
    ).blob(create_shared_bucket_directory_entity.directory_path)
    blob.upload_from_string("")


def delete_shared_bucket_content(
    delete_shared_bucket_content_entity: entities.DeleteSharedBucketContent,
):
    storage_client = app.config.google_cloud_storage_client
    if delete_shared_bucket_content_entity.full_path.endswith("/"):
        blobs = storage_client.list_blobs(
            delete_shared_bucket_content_entity.bucket_name,
            prefix=delete_shared_bucket_content_entity.full_path,
        )
        storage_client.bucket(
            delete_shared_bucket_content_entity.bucket_name
        ).delete_blobs(list(blobs))
    else:
        storage_client.bucket(
            delete_shared_bucket_content_entity.bucket_name
        ).delete_blob(delete_shared_bucket_content_entity.full_path)


def _readable_size(num, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024:
            readsize = "{0:g}".format(num)

            if "." not in readsize:
                return readsize + " " + unit + suffix
            else:
                return "{:3.1f} {:s}{:s}".format(num, unit, suffix)

        num /= 1024.0
    return "{:.1f}{:s}{:s}".format(num, "Y", suffix)


def _add_iam_permissions(
    bucket: GCPBucket, user_email: str, role: enums.IamSharingRole
):
    policy = bucket.get_iam_policy(requested_policy_version=3)
    user_binding = _get_storage_user_binding_role(policy, role)
    if not user_binding:
        policy.bindings.append({"role": role.value, "members": {f"user:{user_email}"}})
        bucket.set_iam_policy(policy)
        return

    user_member = f"user:{user_email}"
    if user_member not in user_binding["members"]:
        user_binding["members"].add(user_member)
        bucket.set_iam_policy(policy)
        return


def _remove_iam_permissions(
    bucket: GCPBucket, user_email: str, role: enums.IamSharingRole
):
    policy = bucket.get_iam_policy(requested_policy_version=3)

    user_binding = _get_storage_user_binding_role(policy, role)
    if not user_binding:
        return

    user_member = f"user:{user_email}"
    if user_member not in user_binding["members"]:
        return
    user_binding["members"].discard(user_member)
    bucket.set_iam_policy(policy)


def _get_storage_user_binding_role(policy, role: str):
    return next(
        filter(
            lambda binding: binding["role"] == role,
            policy.bindings,
        ),
        None,
    )


def _user_has_access_to_bucket(bindings: list, email: str) -> bool:
    return any(f"user:{email}" in binding["members"] for binding in bindings)
