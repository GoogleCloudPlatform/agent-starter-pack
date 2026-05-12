# Gsutil to Gcloud Storage Command and Flag Mapping

This document provides a detailed mapping of `gsutil` commands and flags to their `gcloud storage` equivalents, including caveats and key differences. This guide is intended to supplement the main [Transitioning from gsutil to gcloud storage](https://cloud.google.com/storage/docs/gsutil-transition-to-gcloud) document.  
You can also reference to the complete `gcloud storage` documents [here](https://cloud.google.com/sdk/gcloud/reference/storage).

## Command and Flag Mappings

### ls: List buckets and objects


The `gsutil ls` command lists buckets, objects, and prefixes. The equivalent command is `gcloud storage ls`.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -l | -l, --long | Long listing format. |
| -L | -L, --full | Full listing format. |
| -a | -a, --all-versions | Includes non-current object versions. |
| -b | -b, --buckets | Lists only buckets. |
| -r, -R | -r, --recursive | Recursive listing. |
| -e | -e, --etag | Includes ETag in long listing (-l) output |
| -h | --readable-sizes | Displays object sizes in human-readable format. Renamed from -h to avoid conflict with global --help. |
| -d | Not supported | Option to list only directories has no direct translation and does not work as documented in gsutil. |

#### Caveats and Key Differences

*   **Bucket Listing with Wildcards**: When using a wildcard for buckets, `gcloud storage ls` groups results by bucket name; `gsutil` provides a flat list of objects.
*   **-L (Full Listing) Output**: `gcloud storage` uses title case for keys and omits fields with "None" values. `gsutil` simply capitalizes the first word (depending on the term). 
*   **Order of objects**: The order of objects returned may differ between tools.
*   **Time Format**: `gcloud storage` always converts timestamps to UTC. `gsutil` may not be strict about the timezone.
*   **Error Messages**: `gcloud storage` displays error messages at the end of the output.

---

### cat: Concatenate object content


Outputs the contents of objects to stdout. Equivalent to `gcloud storage cat`.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -h | -d, --display-url | Prints a short header for each object. |
| -r | --range | Specifies a byte range to retrieve. |

---

### du: Display object size usage


Displays space in bytes used by objects. Equivalent to `gcloud storage du`.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -0 | --zero-terminator, -0 | Ends each output line with a 0 byte. |
| -a | --all-versions, -a | Includes live and noncurrent object versions. |
| -c | --total, -c | Includes a total size at the end. |
| -e | --exclude-name-pattern, -e | Excludes a pattern. Can be specified multiple times. |
| -h | --readable-sizes, -r | Prints sizes in human-readable format (e.g., 1 KiB, 234 MiB). |
| -s | --summarize, -s | Displays only the total size for each URL argument. |
| -X | --exclude-name-pattern-file, -X | Excludes patterns from a file. |

---

### acl: Get, set, or change ACLs


Replaced by `gcloud storage {buckets|objects} describe` and `gcloud storage {buckets|objects} update`.

**`gsutil acl get` -> `gcloud storage <RESOURCE> describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="multi(acl:format=json)" | Specify `buckets` or `objects`. |

**`gsutil acl set` -> `gcloud storage <RESOURCE> update`**

| gsutil Flag | gcloud storage Flag | Applies To | Notes |
| --- | --- | --- | --- |
| `<file-path>` | --acl-file=<ACL_FILE_PATH> | Buckets/Objects | Specifies a file containing ACL data. |
| `<predefined>` | --predefined-acl=<PREDEFINED_ACL> | Buckets/Objects | Specifies a predefined (canned) ACL. |
| -a | --all-versions, -a | Objects Only | Apply to all object versions. |
| -r, -R | --recursive, -r | Objects Only | Recursively apply. |
| -f | --continue-on-error | Buckets/Objects | Continue on error. |

**`gsutil acl ch` -> `gcloud storage <RESOURCE> update`**

| gsutil Flag | gcloud storage Flag | Applies To | Notes |
| --- | --- | --- | --- |
| -u | --add-acl-grant=GRANT | Buckets/Objects | Adds grant for a user. Format: ENTITY:ROLE |
| -g | --add-acl-grant=GRANT | Buckets/Objects | Adds grant for a group. Format: ENTITY:ROLE |
| -p | --add-acl-grant=GRANT | Buckets/Objects | Adds grant for a project role. Format: ENTITY:ROLE |
| -d | --remove-acl-grant=<ENTITY> | Buckets/Objects | Removes all roles for the entity. |
| -a | --all-versions, -a | Objects Only | Apply to all object versions. |
| -r, -R | --recursive, -r | Objects Only | Recursively apply. |
| -f | --continue-on-error | Buckets/Objects | Continue on error. |

---

### defacl: Get, set, or change default object ACLs


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil defacl get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(defaultObjectAcl)" | Displays the default object ACL. |

**`gsutil defacl set` -> `gcloud storage buckets update`**

| gsutil Argument | gcloud storage Flag | Notes |
| --- | --- | --- |
| `<file-path>` | --default-object-acl-file=<ACL_FILE> | Specifies a file with the default object ACL. |
| `<predefined-acl>` | --predefined-default-object-acl=<ACL> | Specifies a predefined default object ACL. |

**`gsutil defacl ch` -> `gcloud storage buckets update`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -u | --add-default-object-acl-grant=GRANT | Adds grant for a user. Format: ENTITY:ROLE. |
| -g | --add-default-object-acl-grant=GRANT | Adds grant for a group. Format: ENTITY:ROLE. |
| -p | --add-default-object-acl-grant=GRANT | Adds grant for a project role. |
| -d | --remove-default-object-acl-grant=<ENTITY> | Removes all grants for the entity. |
| -f | --continue-on-error | Continues on error. |

---

### autoclass: Configure Autoclass feature


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil autoclass get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(autoclass)" | Displays Autoclass config. |

**`gsutil autoclass set` -> `gcloud storage buckets update`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| set on | --enable-autoclass | Enables Autoclass. |
| set off | --no-enable-autoclass | Disables Autoclass. |

#### Caveats and Key Differences

*   `gcloud storage buckets update` only accepts one bucket URL at a time.

---

### defstorageclass: Get or set the default storage class


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil defstorageclass get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="value(storageClass)" | Displays the default storage class. |

**`gsutil defstorageclass set` -> `gcloud storage buckets update`**

| gsutil Command | gcloud storage Flag | Notes |
| --- | --- | --- |
| set | --default-storage-class=<STORAGE_CLASS> | Sets the default storage class. |

#### Caveats and Key Differences

*   **Storage Class Abbreviations**: `gsutil` allows abbreviations (e.g., `N` for `NEARLINE`). `gcloud storage` requires full names.

---

### compose: Concatenate objects


Equivalent to `gcloud storage objects compose`.

#### Caveats and Key Differences

*   **Preconditions**: In `gcloud storage`, preconditions are set using specific flags like `--if-generation-match`.

---

### cors: Get or set a bucket's CORS configuration


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil cors get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(cors)" | Displays CORS config in YAML. |

**`gsutil cors set` -> `gcloud storage buckets update`**

| gsutil Command | gcloud storage Flag | Notes |
| --- | --- | --- |
| set | --cors-file=<CORS_FILE> | Specifies a local JSON or YAML file for CORS config. Accepts one bucket URL. |
| set [] | --clear-cors | Clears CORS settings. |

---

### hash: Calculate file hashes


Equivalent to `gcloud storage hash`. `gcloud` command uses additive flags instead of subtractive flags in `gsutil`.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -c | --skip-md5 | gsutil: "calculate CRC32c". gcloud: "skip MD5". |
| -m | --skip-crc32c | gsutil: "calculate MD5". gcloud: "skip CRC32c". |
| -h | --hex | Outputs hashes in hex. Default is base64. |
| Default | Default | Calculates both CRC32c and MD5. |

#### Caveats and Key Differences

*   **Hash Selection**: `gsutil` uses additive flags (-c, -m). `gcloud storage` uses subtractive flags (--skip-md5, --skip-crc32c).

---

### hmac: CRUD operations on service account HMAC keys


Mirrored in `gcloud storage hmac`.

**`gsutil hmac create` -> `gcloud storage hmac create`**
**`gsutil hmac delete` -> `gcloud storage hmac delete`**
**`gsutil hmac get` -> `gcloud storage hmac describe`**

**`gsutil hmac list` -> `gcloud storage hmac list`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -a | --all, -a | Show all keys, including recently deleted. |
| -l | --long, -l | Long listing format. |
| -u | --service-account, -u | Filter by service account. |
| -p | --project | Project ID or number. |

**`gsutil hmac update` -> `gcloud storage hmac update`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -s ACTIVE | --activate | Sets key state to ACTIVE. |
| -s INACTIVE | --deactivate | Sets key state to INACTIVE. |
| -e | --etag | Conditional update based on ETag. |
| -p | --project | Project ID or number. |

---

### iam: Get, set, or change bucket/object IAM permissions


For buckets, functionality is in `gcloud storage buckets get-iam-policy`, `set-iam-policy`, `add-iam-policy-binding`, and `remove-iam-policy-binding`. Object-level IAM is generally discouraged in favor of bucket-level policies with conditions.

**`gsutil iam get` -> `gcloud storage buckets get-iam-policy`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | get-iam-policy --format=json | Matches gsutil JSON output. |

**`gsutil iam set` -> `gcloud storage buckets set-iam-policy`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -e <etag> | --etag=<etag>, -e | Conditional set. |
| -f | --continue-on-error, -c | Continue on error. |
| file | POLICY_FILE | Policy file positional argument. Order is reversed: URL first, then file in gcloud. |

**`gsutil iam ch` -> `gcloud storage buckets add-iam-policy-binding / remove-iam-policy-binding`**

| gsutil Flag | gcloud storage Equivalent | Notes |
| --- | --- | --- |
| binding | --member=<MEMBER> --role=<ROLE> on add-iam-policy-binding | Grants role to member. Binding format needs parsing. |
| -d binding | --member=<MEMBER> --role=<ROLE> on remove-iam-policy-binding | Removes role from member. |
| -d entity | --member=<MEMBER> on remove-iam-policy-binding | Removes all roles for the member. |

#### Caveats and Key Differences

*   **`iam ch` Complexity**: Migrating `gsutil iam ch` scripts requires replacing with potentially multiple `gcloud storage buckets add/remove-iam-policy-binding` calls or replicating the read-modify-write loop in your script.
*   **Conditions**: `gsutil iam ch` does not support IAM policies with conditions; `gcloud storage` does.

---

### kms: Configure Cloud KMS encryption


Split between `gcloud storage service-agent` and `gcloud storage buckets update / describe`.

**`gsutil kms authorize` -> `gcloud storage service-agent`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -p | --project | Project ID. |
| -k | --authorize-cmek=<KMS_KEY> | KMS key to authorize. |

**`gsutil kms encryption` -> `gcloud storage buckets describe / update`**

*   **Get**: `describe --format="value(encryption.defaultKmsKeyName)"`
*   **Set**: `update --default-encryption-key=<KMS_KEY>`
*   **Clear**: `update --clear-default-encryption-key`

**`gsutil kms serviceaccount` -> `gcloud storage service-agent`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -p | --project | Project ID. |

---

### label: Get, set, or change bucket labels


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil label get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="gsutiljson(labels)" | Displays labels. |

**`gsutil label set` -> `gcloud storage buckets update`**

| gsutil Argument | gcloud storage Flag | Notes |
| --- | --- | --- |
| `<label-json-file>` | --labels-file=<LABEL_FILE_PATH> | Specifies a JSON file with labels. |

**`gsutil label ch` -> `gcloud storage buckets update`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -l | --update-labels=KEY=VALUE,... | Adds or updates labels. |
| -d | --remove-labels=KEY,... | Removes labels by key. |

---

### lifecycle: Get or set bucket lifecycle configuration


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil lifecycle get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="gsutiljson(lifecycle)" | Displays lifecycle config. |

**`gsutil lifecycle set` -> `gcloud storage buckets update`**

| gsutil Argument | gcloud storage Flag | Notes |
| --- | --- | --- |
| `<config-json-file>` | --lifecycle-file=<LIFECYCLE_FILE> | Specifies a local JSON file with lifecycle config. |

---

### logging: Get or set bucket logging configuration


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil logging get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(logging)" | Displays logging config. |

**`gsutil logging set on` -> `gcloud storage buckets update`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -b | --log-bucket | Specifies the log bucket. |
| -o | --log-object-prefix | Specifies the log object prefix. |

**`gsutil logging set off` -> `gcloud storage buckets update`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| set off | --clear-log-bucket and --clear-log-object-prefix | Clears logging config. |

---

### mb: Make buckets


Equivalent to `gcloud storage buckets create`. Aliases like `makebucket`, `createbucket`, `md`, `mkdir` are not supported in `gcloud storage`.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -p | --project | Project ID. |
| -c, -s | --default-storage-class, -c, -s | Default storage class. |
| -l | --location, -l | Bucket location. |
| -b on | --uniform-bucket-level-access, -b | Enable UBLA. |
| --autoclass | --enable-autoclass | Enable Autoclass. |
| --retention | --retention-period | Retention period. |
| --pap enforced | --public-access-prevention | Enforce public access prevention. |
| -k | --default-encryption-key, -k | Default KMS key. |
| --placement | --placement | Regions for custom dual-region. |
| --rpo | --recovery-point-objective, --rpo | Replication setting for dual/multi-region. |

---

### cp: Copy files and objects


Equivalent to `gcloud storage cp`. Alias `copy` is not supported.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -a | --predefined-acl=<PREDEFINED_ACL>, -a | Predefined ACL for uploaded objects. |
| -A | --all-versions, -A | Copies all source versions. Disables parallelism in gcloud. |
| -c | --continue-on-error, -c | Continue on error. |
| -D | --daisy-chain, -D | Copy between buckets via local machine. |
| -e | --ignore-symlinks | Excludes symbolic links. |
| -I | --read-paths-from-stdin, -I | Read paths from stdin. |
| -j <ext,...> | --gzip-in-flight="<ext,...>", -j | Gzip transport encoding for matching extensions. |
| -J | --gzip-in-flight-all, -J | Gzip transport encoding for all uploads. |
| -L <file> | --manifest-path=<file>, -L | Output manifest log file. |
| -n | --no-clobber, -n | Don't replace existing files. |
| -p | --preserve-acl, -p | Preserve ACLs when copying in the cloud. |
| -P | --preserve-posix, -P | Preserve POSIX attributes. |
| -r, -R | --recursive, -r, -R | Recursive copy. |
| -s <class> | --storage-class=<class>, -s | Storage class of destination. |
| -U | --skip-unsupported, -U | Skip unsupported types (e.g., S3 Glacier). |
| -v | --print-created-message, -v | Print version-specific URL for uploads. |
| -z <ext,...> | --gzip-local="<ext,...>", -z | Compress local files with matching extensions before upload. |
| -Z | --gzip-local-all, -Z | Compress all local files before upload. |
| --stet | (Not supported) | Split-trust encryption tool flag. |

#### Caveats and Key Differences

*   **Parallelism**: `gcloud storage cp` is parallel by default. `gsutil` requires top-level `-m` flag.
*   **Empty Directories**: `gcloud storage cp` copies 0-byte placeholder objects created by Cloud Console, `gsutil cp` skips them.
*   **Error Handling**: `gcloud storage cp` attempts to copy all valid sources even if some are invalid. `gsutil cp` may halt on the first invalid source.
*   **Local Directory Creation**: `gcloud storage cp` creates missing local directories in the destination path during downloads. `gsutil cp` fails if the directory doesn't exist.
*   **Support for Local Copy**: Gcloud Storage is meant as a tool to work with GCS (cloud). So it does not support local copying (where both source and destination are local files/folders). Trying to use the tool this way will cause an error.

---

### mv: Move or rename objects


Equivalent to `gcloud storage mv`. Aliases `move`, `ren`, `rename` are not supported. Most `gsutil cp` flags are available, except not applicable ones like `-r`.

#### Caveats and Key Differences

*   **Non-Atomic**: Like `gsutil mv`, `gcloud storage mv` is a copy followed by a delete.

---

### notification: Configure object change notifications


Pub/Sub notifications are managed via `gcloud storage buckets notifications`. Legacy Object Change Notifications (`watchbucket`, `stopchannel`) are not supported in `gcloud storage`.

**`gsutil notification create` -> `gcloud storage buckets notifications create`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -f | --payload-format=<PAYLOAD_FORMAT>, -f | Payload format (json or none). |
| -p | --object-prefix=<OBJECT_PREFIX>, -p | Filter by object prefix. |
| -t | --topic=<TOPIC>, -t | Cloud Pub/Sub topic. |
| -m | --custom-attributes=KEY=VALUE,..., -m | Custom key:value attributes. |
| -e | --event-types=<EVENT_TYPE>,..., -e | Filter by event type (e.g., OBJECT_FINALIZE). |
| -s | --skip-topic-setup, -s | Skip topic creation/permission setup. |

**`gsutil notification list` -> `gcloud storage buckets notifications list`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -o | (Not supported) | Listing legacy Object Change Notification channels not supported. |

**`gsutil notification delete` -> `gcloud storage buckets notifications delete`**

Deletes a specific notification by name or all notifications on a bucket.

---

### pap: Get or set Public Access Prevention


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil pap get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(iamConfiguration.publicAccessPrevention)" | Displays PAP config. |

**`gsutil pap set` -> `gcloud storage buckets update`**

| gsutil Argument | gcloud storage Flag | Notes |
| --- | --- | --- |
| enforced | --public-access-prevention | Enforces PAP. |
| inherited | --no-public-access-prevention | Sets PAP to inherited. |

---

### rb: Remove buckets


Equivalent to `gcloud storage buckets delete`. Aliases `deletebucket`, `removebucket`, etc., are not supported.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -f | --continue-on-error | Continues despite errors. |

---

### requesterpays: Configure requester pays


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil requesterpays set` -> `gcloud storage buckets update`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| on | --requester-pays | Enables Requester Pays. |
| off | --no-requester-pays | Disables Requester Pays. |

**`gsutil requesterpays get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(requesterPays)" | Displays Requester Pays config. |

---

### retention: Manage retention policies and holds


Split across `gcloud storage buckets` and `gcloud storage objects` commands.

*   **Set/Clear/Get Bucket Retention Policy**: `gcloud storage buckets update --retention-period`, `gcloud storage buckets update --clear-retention-period`, `gcloud storage buckets describe --format="default(retentionPolicy)"`
*   **Lock Bucket Retention Policy**: `gcloud storage buckets update --lock-retention-period`
*   **Default Event-Based Hold**: `gcloud storage buckets update --default-event-based-hold / --no-default-event-based-hold`
*   **Object Event-Based Hold**: `gcloud storage objects update --event-based-hold / --no-event-based-hold`
*   **Object Temporary Hold**: `gcloud storage objects update --temporary-hold / --no-temporary-hold`

---

### rewrite: Rewrite objects in place


Equivalent to `gcloud storage objects update`.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -k | --encryption-key=KEY, --clear-encryption-key | Complex behavior, see Caveats. |
| -s <class> | --storage-class=<class>, -s | Rewrite to specified storage class. |
| -r, -R | --recursive, -r | Recursive rewrite. |
| -f | --continue-on-error | Continue on error. |
| -I | --read-paths-from-stdin, -I | Read paths from stdin. |
| -O | --no-preserve-acl | Use bucket's default object ACL. |

#### Caveats and Key Differences

*   **Encryption Handling**: `gsutil rewrite -k` behavior depends on `boto` config. If `encryption_key` is set in boto, that key is applied. If not set, it's equivalent to `gcloud storage objects update --clear-encryption-key`, potentially removing CSEK/CMEK.
*   **Redundancy Checks**: `gsutil rewrite` skips no-op transformations. `gcloud storage objects update` might not, potentially causing unnecessary operations.

---

### rm: Remove objects


Equivalent to `gcloud storage rm`. Aliases `del`, `delete`, `remove` are not supported.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -f | --continue-on-error | Continue on error. |
| -I | --read-paths-from-stdin, -I | Read paths from stdin. |
| -R, -r | --recursive, -r | Recursive delete. |
| -a | --all-versions, -a | Delete all versions. |

---

### rpo: Get or set a bucket's replication setting


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil rpo get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(rpo)" | Displays RPO setting. |

**`gsutil rpo set` -> `gcloud storage buckets update`**

| gsutil Argument | gcloud storage Flag | Notes |
| --- | --- | --- |
| ASYNC_TURBO or DEFAULT | --recovery-point-objective=RPO, --rpo=RPO | Sets replication setting. |

---

### rsync: Synchronize content


Equivalent to `gcloud storage rsync`.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -a | --predefined-acl=<PREDEFINED_ACL> | Sets predefined ACL on uploads. |
| -c | --checksums-only | Compare checksums only. |
| -C | --continue-on-error | Continue on error. |
| -d | --delete-unmatched-destination-objects | Delete destination files not in source. |
| -e | --ignore-symlinks | Exclude symlinks. |
| -i | --no-clobber | Skip existing destination files. |
| -j <ext,...> | --gzip-in-flight="<ext,...>" | Gzip transport encoding. |
| -J | --gzip-in-flight-all | Gzip all uploads. |
| -n | --dry-run | Dry run. |
| -p | --preserve-acl | Preserve ACLs. |
| -P | --preserve-posix | Preserve POSIX attributes. |
| -r, -R | --recursive, -r, -R | Recursive sync. |
| -u | --skip-if-dest-has-newer-mtime | Skip if destination is newer. |
| -U | --skip-unsupported | Skip unsupported storage classes. |
| -x | --exclude=<PATTERN> | Exclude files matching pattern. |

#### Caveats and Key Differences

*   **Change Detection**: `gsutil rsync` defaults to size and mtime. `gcloud storage rsync` also uses size and mtime, but falls back to checksums if sizes match but mtimes differ or are missing.
*   **Parallelism**: `gcloud storage rsync` is parallel by default. `gsutil rsync` requires top-level `-m`.
*   **Symlink Handling**: `gsutil rsync` follows symlinks by default. `gcloud storage rsync` ignores them by default (use `--no-ignore-symlinks`).

---

### setmeta: Set metadata on objects


Equivalent to `gcloud storage objects update`, but with different flag structure.

| Action | gsutil setmeta Example | gcloud storage objects update Equivalent |
| --- | --- | --- |
| Set Metadata | -h "Content-Type:text/html" | --content-type="text/html" |
|  | -h "Cache-Control:no-cache" | --cache-control="no-cache" |
|  | -h "Content-Language:en" | --content-language="en" |
|  | -h "x-goog-meta-foo:bar" | --update-custom-metadata=foo=bar |
| Remove Metadata | -h "Content-Type" | --clear-content-type |
|  | -h "Cache-Control" | --clear-cache-control |
|  | -h "x-goog-meta-foo" | --remove-custom-metadata=foo |

---

### signurl: Create a signed URL


Equivalent to `gcloud storage sign-url`.

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| `<private-key-file>` | --private-key-file=<PRIVATE_KEY_FILE> | Path to private key file. Positional in gsutil. |
| -u, --use-service-account | (No flag needed) | Default behavior in gcloud if --private-key-file not used. |
| -d | --duration=<DURATION> | URL validity duration. Different format (e.g., 10m). |
| -m | --http-verb=<METHOD> | HTTP method (e.g., GET, PUT). |
| -c | --headers=content-type=<CONTENT_TYPE> | Content-Type header. Part of repeatable --headers flag. |
| -p | --private-key-password=<PASSWORD> | Password for encrypted private key. |
| -r | --region=<REGION> | Resource region. |
| -b | --query-params=userProject=<PROJECT> | Billing project for Requester Pays. |

---

### stat: Display object status


Equivalent to `gcloud storage objects list --stat --fetch-encrypted-object-hashes`.

#### Caveats and Key Differences

*   **Output Formatting**: Output format differs, with known spacing issues. Scripts parsing `gsutil stat` output may need adjustments.

---

### ubla: Configure Uniform bucket-level access


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil ubla get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(iamConfiguration.uniformBucketLevelAccess)" | Displays UBLA config. |

**`gsutil ubla set` -> `gcloud storage buckets update`**

| gsutil Argument | gcloud storage Flag | Notes |
| --- | --- | --- |
| on | --uniform-bucket-level-access | Enables UBLA. |
| off | --no-uniform-bucket-level-access | Disables UBLA. |

---

### versioning: Enable or suspend versioning


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil versioning get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(versioning)" | Displays versioning config. |

**`gsutil versioning set` -> `gcloud storage buckets update`**

| gsutil Argument | gcloud storage Flag | Notes |
| --- | --- | --- |
| on | --versioning | Enables versioning. |
| off | --no-versioning | Disables (suspends) versioning. |

---

### web: Set a website configuration for a bucket


Replaced by `gcloud storage buckets describe` and `gcloud storage buckets update`.

**`gsutil web get` -> `gcloud storage buckets describe`**

| gsutil Command | gcloud storage Command | Notes |
| --- | --- | --- |
| get | describe --format="default(website)" | Displays website config. |

**`gsutil web set` -> `gcloud storage buckets update`**

| gsutil Flag | gcloud storage Flag | Notes |
| --- | --- | --- |
| -m <main_page_suffix> | --web-main-page-suffix=<MAIN_PAGE_SUFFIX> | Main page suffix. |
| -e <error_page> | --web-error-page=<ERROR_PAGE> | Not-found (404) page. |
| (no flags) | --clear-web-main-page-suffix and --clear-web-error-page | Clears website config. |

---

### Other Commands

The following `gsutil` commands do not have direct translations in `gcloud storage` as their functionality is gsutil-specific or handled differently within the gcloud ecosystem:

*   **config**: Manages gsutil-specific configurations. `gcloud` has its own `config` group.
*   **version**: Displays gsutil version. You can use `gcloud -v` instead.
*   **help**: gsutil-specific help. You can use `gcloud help`.
*   **perfdiag**: gsutil-specific performance diagnostics. While not a direct mapping, `gcloud alpha storage diagnose` can be used instead.
*   **test**: Runs gsutil tests.
*   **update**: Updates gsutil. gcloud components are updated via `gcloud components update`.

