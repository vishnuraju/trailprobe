import argparse
from .auth import make_session
from .orchestrator import run_services

def main():
    ap = argparse.ArgumentParser(
        description="TrailProbe — simulate AWS API calls (no AssumeRole, no analysis)."
    )
    ap.add_argument(
        "--aws-services", required=True,
        help="Comma-separated list, e.g., ec2,s3,lambda,bedrock"
    )
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--profile", default=None, help="Local profile to use (optional).")
    ap.add_argument("--rate", type=int, default=5, help="Max calls per second per service.")
    ap.add_argument("--max-ops", type=int, default=30, help="Max operations to attempt per service.")
    ap.add_argument("--include-dryrun", action="store_true", help="Include DryRun-capable mutating APIs.")
    ap.add_argument("--min-dryrun", type=int, default=5, help="Ensure at least this many DryRun ops (if available).")
    ap.add_argument("--aggressive", action="store_true",
                    help="Include representative non-dryrun WRITE ops with bogus IDs to force safe server-side failure (CloudTrail will log).")
    ap.add_argument("--all-ops", action="store_true",
                    help="Attempt EVERY operation for each service (up to --max-ops). Overrides selection heuristics.")
    ap.add_argument("--only-safe", action="store_true", help="Only call read-only ops (List/Get/Describe/Head).")
    ap.add_argument("--verbose", action="store_true", help="Print selected operations before execution.")
    args = ap.parse_args()

    services = [s.strip() for s in args.aws_services.split(",") if s.strip()]
    sess = make_session(region=args.region, profile=args.profile)

    run_services(
        session=sess,
        region=args.region,
        services=services,
        rate_limit_per_sec=args.rate,
        max_ops_per_service=args.max_ops,
        include_dryrun=args.include_dryrun and not args.only_safe,
        aggressive=args.aggressive and not args.only_safe,
        all_ops=args.all_ops,
        min_dryrun=args.min_dryrun,
        verbose=args.verbose,
    )

if __name__ == "__main__":
    main()