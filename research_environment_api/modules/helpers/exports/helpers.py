import csv
from typing import List

from research_environment_api.modules.app import app


def create_csv(rows: List, filename: str, columns: List):
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)


def upload_to_gcs(source_file_name: str, destination_path: str):
    bucket = app.config.google_cloud_storage_client.bucket(
        app.config.monitoring_csv_exports_root_bucket
    )
    destination_blob_name = f"{destination_path}/{source_file_name}"
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
