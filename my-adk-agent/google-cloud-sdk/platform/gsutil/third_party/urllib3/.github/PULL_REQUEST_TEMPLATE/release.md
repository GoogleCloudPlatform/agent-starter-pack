* [ ]  See if all tests, including downstream, pass
* [ ]  Get the release pull request approved by a [CODEOWNER](https://github.com/urllib3/urllib3/blob/main/.github/CODEOWNERS)
* [ ]  Squash merge the release pull request with message "`Release <VERSION>`"
* [ ]  Tag with X.Y.Z, push tag on urllib3/urllib3 (not on your fork, update `<REMOTE>` accordingly)
  * Notice that the `<VERSION>` shouldn't have a `v` prefix (Use `1.26.6` instead of `v.1.26.6`)
  * ```
    # Ensure the release commit is the latest in the main branch.
    git checkout main
    git pull origin main
    git tag -s -a '<VERSION>' -m 'Release: <VERSION>'
    git push <REMOTE> --tags
    ```
* [ ]  Execute the `publish` GitHub workflow. This requires a review from a maintainer.
* [ ]  Ensure that all expected artifacts are added to the new GitHub release. Should
       be one `.whl`, one `.tar.gz`, and one `multiple.intoto.jsonl`. Update the GitHub
       release to have the content of the release's changelog.
* [ ]  Announce on:
  * [ ]  Twitter
  * [ ]  Discord
  * [ ]  OpenCollective
* [ ]  Update Tidelift metadata
* [ ]  If this was a 1.26.x release, add changelog to the `main` branch
