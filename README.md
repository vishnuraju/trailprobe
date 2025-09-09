# TrailProbe (AWS API Event Simulator)

***Objective ***
Generate AWS API calls so you can verify (manually) that CloudTrail records them.  


## Options
  -h, --help            show this help message and exit
  --aws-services AWS_SERVICES
                        Comma-separated list, e.g., ec2,s3,lambda,bedrock
  --region REGION
  --profile PROFILE     Local profile to use (optional).
  --rate RATE           Max calls per second per service.
  --max-ops MAX_OPS     Max operations to attempt per service.
  --include-dryrun      Include DryRun-capable mutating APIs.
  --min-dryrun MIN_DRYRUN
                        Ensure at least this many DryRun ops (if available).
  --aggressive          Include representative non-dryrun WRITE ops with bogus IDs to force safe server-side failure (CloudTrail will log).
  --all-ops             Attempt EVERY operation for each service (up to --max-ops). Overrides selection heuristics.
  --only-safe           Only call read-only ops (List/Get/Describe/Head).
  --verbose             Print selected operations before execution.

## Usage
```bash
# Basic run
python -m trailprobe --aws-services ec2,s3,lambda --region ap-south-1

# With profile and verbose logging
python -m trailprobe --aws-services ec2,s3 \
  --profile my-sso --region us-east-1 --verbose

# Aggressive mode: DryRun + safe-failing writes
python -m trailprobe --aws-services ec2,iam,cloudtrail \
  --region us-east-1 --include-dryrun --aggressive --verbose

# All operations for EC2 service
python -m trailprobe --aws-services ec2 --region us-east-1 --all-ops --max-ops 9999