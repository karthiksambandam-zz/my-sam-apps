## Automating EBS snapshot life cycle management
Attached cloud formation template would help get started on managing EBS snapshots using CloudWatch events, lambda and resource tags. This template would help users provide the frequency for snapshot, retention policy for snapshots and tag to be used for filtering the Volumes. The necessary CloudWatch events and Lambda function for creating snapshots and cleaning up snapshots will be created by the template.

With this template, user can retain by version count or age. Lambda function would cleanup snapshots based on user provided policy.
