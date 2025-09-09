import boto3
import os

def make_session(region=None, profile=None):
    """Create a boto3 Session using local creds/SSO/IMDS. No AssumeRole."""
    if profile:
        return boto3.Session(profile_name=profile, region_name=region)
    prof = os.getenv("AWS_PROFILE")
    if prof:
        return boto3.Session(profile_name=prof, region_name=region)
    return boto3.Session(region_name=region)
