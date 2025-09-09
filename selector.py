from botocore.session import Session as BotoCoreSession

SAFE_PREFIXES = ("List", "Get", "Describe", "Head")

# Representative write-ish ops that safely fail server-side (CloudTrail still logs)
PINNED_AGGRESSIVE = {
    "lambda": ["UpdateFunctionConfiguration", "PublishVersion", "CreateAlias", "DeleteFunction"],
    "s3": ["DeleteObject", "PutBucketTagging"],
    "iam": ["AttachRolePolicy", "AttachUserPolicy", "CreateAccessKey"],
    "events": ["PutRule", "PutTargets", "PutEvents"],
    "logs": ["PutResourcePolicy", "PutRetentionPolicy", "PutSubscriptionFilter"],
    "sqs": ["SetQueueAttributes", "RemovePermission", "TagQueue"],
    "sns": ["SetTopicAttributes", "Subscribe", "Unsubscribe"],
    "ecr": ["BatchDeleteImage", "DeleteRepository"],
    "rds": ["ModifyDBInstance", "StopDBInstance", "StartDBInstance"],
    "eks": ["UpdateClusterConfig"],
    "es": ["UpdateElasticsearchDomainConfig"],           # legacy ES in botocore
    "opensearch": ["UpdateDomainConfig"],
    "kms": ["DisableKey", "EnableKeyRotation", "ScheduleKeyDeletion"],
    "cloudtrail": ["UpdateTrail", "StartLogging", "StopLogging"],
    "glue": ["StartJobRun", "CreateJob", "DeleteJob"],
    "stepfunctions": ["StartExecution", "StopExecution"],
    "bedrock": ["PutModelInvocationLoggingConfiguration"],
}

# DryRun-capable ops to definitely try where available
PINNED_DRYRUN = {
    "ec2": ["StartInstances", "StopInstances", "TerminateInstances", "RebootInstances", "RunInstances", "CreateTags"],
    "autoscaling": ["CreateAutoScalingGroup", "UpdateAutoScalingGroup", "DeleteAutoScalingGroup"],
}

def select_operations_for_service(boto3_session, service_name, max_ops_per_service=30,
                                  include_dryrun=False, aggressive=False, all_ops=False, min_dryrun=5):
    bc = BotoCoreSession()
    try:
        smodel = bc.get_service_model(service_name)
    except Exception:
        return []

    op_names = list(smodel.operation_names)

    # If user asked for literally everything, return full list up to cap
    if all_ops:
        return op_names[:max_ops_per_service]

    # Otherwise, compose: DryRun (ensure some), then Aggressive, then safe reads
    # DryRun-capable (discovered + pinned)
    dryrun_ops = []
    if include_dryrun:
        discovered = []
        for op in op_names:
            op_model = smodel.operation_model(op)
            input_shape = op_model.input_shape
            if input_shape and "DryRun" in input_shape.members:
                discovered.append(op)
        pinned = [op for op in PINNED_DRYRUN.get(service_name, []) if op in op_names]
        dryrun_ops = pinned + [op for op in discovered if op not in pinned]

    aggr_ops = [op for op in PINNED_AGGRESSIVE.get(service_name, []) if op in op_names] if aggressive else []
    safe_ops = [op for op in op_names if op.startswith(SAFE_PREFIXES)]

    out, seen = [], set()

    if include_dryrun:
        for op in dryrun_ops:
            if len(out) >= max_ops_per_service: break
            if op in seen: continue
            seen.add(op); out.append(op)

    if aggressive and len(out) < max_ops_per_service:
        for op in aggr_ops:
            if len(out) >= max_ops_per_service: break
            if op in seen: continue
            seen.add(op); out.append(op)

    if len(out) < max_ops_per_service:
        for op in safe_ops:
            if len(out) >= max_ops_per_service: break
            if op in seen: continue
            seen.add(op); out.append(op)

    return out