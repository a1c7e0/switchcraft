# R4 publication inputs

Temporary staging repository for the public raw-artifact branch consumed by the approved `publish-device-test-package.yml` workflow. It will contain only the validated package parts, manifest, SHA256SUMS, separate source/debug assets, release input record, dependency lock, curl upstream pin, and any required split parts. No source Git objects or unrelated build outputs belong here.

Artifacts are not staged until the clean build, host suite, package checks, and complete byte-level metadata validation have finished. Publish this directory as a new commit without force-updating existing branches, then use the workflow's `artifact_revision` and `release_tag` inputs.
