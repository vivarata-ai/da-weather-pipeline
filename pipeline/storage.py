"""Storage for pipeline outputs: local files, S3, or GCS.

Load strategy, in the terms of the Virmani decks: this pipeline uses
kill and fill. Each run overwrites the same output files, so a run
is idempotent. Re-running it produces the same result as running it
once, and a single day can be re-run without touching other files
because outputs are written per run, never appended.

Cloud storage is optional. When STORAGE_BACKEND is local, which is
the default, everything is written to the output directory and no
credentials are needed. When it is s3 or gcs, the same files are
also uploaded to the named bucket using the standard credential
chain for that cloud. If the cloud upload fails, the run keeps the
local copy, records a warning, and still succeeds.
"""

import os

from . import config


def _write_local(files, output_dir):
    """Write each file to the local output directory. Returns paths."""
    paths = []
    for relative_path, content in files.items():
        full_path = os.path.join(output_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(full_path, mode) as handle:
            handle.write(content)
        paths.append(full_path)
    return paths


def _upload_to_s3(bucket, files):
    """Upload each file to S3. Returns the object keys written."""
    import boto3

    client = boto3.client("s3")
    keys = []
    for relative_path, content in files.items():
        key = "da-pipeline/%s" % relative_path
        body = content if isinstance(content, bytes) else content.encode("utf-8")
        client.put_object(Bucket=bucket, Key=key, Body=body)
        keys.append("s3://%s/%s" % (bucket, key))
    return keys


def _upload_to_gcs(bucket, files):
    """Upload each file to GCS. Returns the object paths written."""
    from google.cloud import storage

    client = storage.Client()
    bucket_obj = client.bucket(bucket)
    paths = []
    for relative_path, content in files.items():
        name = "da-pipeline/%s" % relative_path
        blob = bucket_obj.blob(name)
        if isinstance(content, bytes):
            blob.upload_from_string(content)
        else:
            blob.upload_from_string(content, content_type="text/plain")
        paths.append("gs://%s/%s" % (bucket, name))
    return paths


def store_outputs(files, output_dir=None):
    """Store output files locally, and to the cloud when configured.

    files maps a relative path to its content. Returns a result dict
    with the backend used, the local paths written, the cloud paths
    written (or an empty list), and any warning.
    """
    output_dir = output_dir or config.OUTPUT_DIR
    settings = config.storage_settings()
    local_paths = _write_local(files, output_dir)
    result = {
        "backend": settings["backend"],
        "local_paths": local_paths,
        "cloud_paths": [],
        "warning": "",
    }
    backend = settings["backend"]
    if backend == "s3":
        if not settings["s3_bucket"]:
            result["warning"] = (
                "STORAGE_BACKEND is s3 but S3_BUCKET is not set, "
                "so files were stored locally only.")
            return result
        try:
            result["cloud_paths"] = _upload_to_s3(
                settings["s3_bucket"], files)
        except Exception as error:
            result["warning"] = (
                "S3 upload failed (%s), files were stored locally only."
                % error)
    elif backend == "gcs":
        if not settings["gcs_bucket"]:
            result["warning"] = (
                "STORAGE_BACKEND is gcs but GCS_BUCKET is not set, "
                "so files were stored locally only.")
            return result
        try:
            result["cloud_paths"] = _upload_to_gcs(
                settings["gcs_bucket"], files)
        except Exception as error:
            result["warning"] = (
                "GCS upload failed (%s), files were stored locally only."
                % error)
    elif backend != "local":
        result["warning"] = (
            "Unknown STORAGE_BACKEND %r, files were stored locally only."
            % backend)
    return result
