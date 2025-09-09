import botocore
import random
import string
import time
from .recorder import Recorder
from botocore.session import Session as BotoCoreSession

def _rand(n=8):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def _dummy_for_shape(shape, name_hint=None, service_name=None):
    # Simple, non-intrusive dummies based on type/name hints
    t = shape.type_name if hasattr(shape, 'type_name') else shape.type
    nh = (name_hint or "").lower()
    # enums: choose a valid one to avoid client-side ParamValidation
    if hasattr(shape, 'enum') and shape.enum:
        return shape.enum[0]
    if t == "string":
        if "arn" in nh:
            return f"arn:aws:service:region:111122223333:resource/{_rand()}"
        if nh.endswith("id") or nh.endswith("name") or nh.endswith("key") or nh.endswith("bucket") or nh.endswith("stream"):
            return f"nonexistent-{_rand()}"
        # Heuristics for common IDs for better server-side errors (still non-intrusive)
        if nh in ('imageid',) or nh.endswith('imageid'):
            return 'ami-0' + '0'*8
        if nh in ('instanceid',) or nh.endswith('instanceid'):
            return 'i-0' + '0'*8
        if nh.endswith('subnetid'):
            return 'subnet-0' + '0'*8
        if nh.endswith('vpcid'):
            return 'vpc-0' + '0'*8
        if nh.endswith('securitygroupid'):
            return 'sg-0' + '0'*8
        if nh.endswith('allocationid'):
            return 'eipalloc-0' + '0'*8
        if nh.endswith('internetgatewayid'):
            return 'igw-0' + '0'*8
        if nh.endswith('transitgatewayattachmentid'):
            return 'tgw-attach-0' + '0'*8
        return "noop"
    if t == "integer" or t == "long":
        return 1
    if t == "boolean":
        return False
    if t == "float" or t == "double":
        return 0.0
    if t == "list":
        # list of one dummy of member type
        mem = shape.member if hasattr(shape, "member") else None
        return [] if mem is None else [_dummy_for_shape(mem, name_hint, service_name)]
    if t == "map":
        k = shape.key if hasattr(shape, "key") else None
        v = shape.value if hasattr(shape, "value") else None
        return {} if (k is None or v is None) else { _dummy_for_shape(k, name_hint, service_name): _dummy_for_shape(v, name_hint, service_name) }
    if t == "structure":
        out = {}
        for mname, mshape in (shape.members or {}).items():
            # Only populate required fields at call time; here we just craft placeholders
            out[mname] = _dummy_for_shape(mshape, mname, service_name)
        return out
    # default
    return None

def _build_params_for_operation(service_name, op_model):
    input_shape = op_model.input_shape
    if not input_shape:
        return {}

    params = {}
    required = list(getattr(input_shape, "required_members", []) or [])
    # Prefer to set DryRun when available to avoid effects
    if "DryRun" in input_shape.members:
        params["DryRun"] = True

    # Only populate required fields; keep it minimal
    for mname in required:
        mshape = input_shape.members[mname]
        params[mname] = _dummy_for_shape(mshape, mname, service_name)

    return params

def execute_operation(client, service_name, op_name, recorder: Recorder):
    # Fetch botocore model for parameter shapes
    bc = BotoCoreSession()
    smodel = bc.get_service_model(service_name)
    op_model = smodel.operation_model(op_name)

    # Build minimal params
    params = _build_params_for_operation(service_name, op_model)

    # Make the call; do not interpret success/failure beyond logging
    from botocore import xform_name
    py_method = xform_name(op_model.name)
    try:
        method = getattr(client, py_method)
    except AttributeError:
        recorder.write({"service": service_name, "op": op_name, "status": "no_method", "py_method": py_method})
        return

    try:
        resp = method(**params)
        req_id = (resp or {}).get("ResponseMetadata", {}).get("RequestId")
        recorder.write({"service": service_name, "op": op_name, "status": "invoked", "request_id": req_id})
    except botocore.exceptions.ClientError as e:
        # Expected for many ops with dummy params or lacking perms
        err = e.response.get("Error", {})
        req_id = e.response.get("ResponseMetadata", {}).get("RequestId")
        recorder.write({"service": service_name, "op": op_name, "status": "client_error", "code": err.get("Code"), "msg": err.get("Message"), "request_id": req_id})
    except Exception as e:
        recorder.write({"service": service_name, "op": op_name, "status": "exception", "error": str(e)})
