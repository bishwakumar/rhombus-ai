# S3 connection failure (3 Oct 2026)

**Error shown by Rhombus (every attempt, 5+ retries):**

> AWS denied Rhombus AI access to the whole bucket. Folder / path is blank. The required whole-bucket read-only policy is missing or does not match this bucket. Apply the generated policy, or update the CloudFormation stack so SourceBucket matches the connection form and SourcePrefix is empty, then retry.

**Setup:** bucket `rhombus-ai`, region `ap-southeast-2`, folder/path blank, SSE-S3 encryption (bucket default and object confirmed), Block Public Access on, file `v0_baseline.csv` (21.7 KB).

**Checked:**
- The bucket policy contained the exact statements generated in the Rhombus form (`s3:GetBucketLocation` and `s3:ListBucket` on `arn:aws:s3:::rhombus-ai`, `s3:GetObject` on `arn:aws:s3:::rhombus-ai/*`) for both Rhombus principals:
  - `arn:aws:iam::730335216038:role/rhombusai-production-eks-cluster-app-secrets`
  - `arn:aws:iam::730335216038:role/rhombo-native-s3-managed-compute--GlueExecutionRole-8hk4bLprqo3U`
- The CloudFormation stack was also deployed with `SourceBucket = rhombus-ai` and an empty `SourcePrefix`; a direct stack update reported "The submitted information didn't contain changes". Its statements were present in the bucket policy as well.
- Encryption, region, bucket name and object presence all confirmed.

**Outcome:** a support request was sent with the details above. The source was switched to a GCS bucket so testing could continue.
