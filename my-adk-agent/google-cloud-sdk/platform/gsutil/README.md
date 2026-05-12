IMPORTANT: gsutil is not the recommended CLI for Cloud Storage. Use [gcloud storage commands](https://docs.cloud.google.com/storage/docs/discover-object-storage-gcloud) in the Google Cloud CLI instead.

* The gsutil tool is a legacy Cloud Storage CLI and minimally maintained.
* The gsutil tool does not support working with newer Cloud Storage features, such as [soft delete](https://docs.cloud.google.com/storage/docs/soft-delete) and [managed folders](https://docs.cloud.google.com/storage/docs/managed-folders).
* gcloud storage commands require less manual optimization in order to achieve the fastest upload and download rates.

# gsutil

gsutil is a Python application that lets you access Google Cloud Storage from
the command line. You can use gsutil to do a wide range of bucket and object
management tasks, including:

* Creating and deleting buckets.
* Uploading, downloading, and deleting objects.
* Listing buckets and objects.
* Moving, copying, and renaming objects.
* Editing object and bucket ACLs.

## Installation

For installation instructions, please see:

https://cloud.google.com/storage/docs/gsutil_install

## Testing / Development

The gsutil source code is available at https://github.com/GoogleCloudPlatform/gsutil

See https://cloud.google.com/storage/docs/gsutil/addlhelp/ContributingCodetogsutil
for best practices on how to contribute code changes to the gsutil repository.

## Help and Support

Run the "gsutil help" command for a list of the built-in gsutil help topics.

You can also browse the help pages online at:

https://cloud.google.com/storage/docs/gsutil

For community support, visit:

https://cloud.google.com/storage/docs/resources-support#community

