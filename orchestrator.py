import time, sys
from .recorder import Recorder
from .selector import select_operations_for_service
from .runner import execute_operation

def run_services(session, region, services, rate_limit_per_sec=5, max_ops_per_service=30,
                 include_dryrun=False, aggressive=False, all_ops=False, min_dryrun=5, verbose=False):
    rec = Recorder()
    delay = 1.0 / max(rate_limit_per_sec, 1)

    for svc in services:
        print(f"Starting simulating events for {svc.upper()}")
        try:
            client = session.client(svc, region_name=region)
        except Exception as e:
            rec.write({"service": svc, "op": "-", "status": "client_error", "error": str(e)})
            continue

        ops = select_operations_for_service(
            session, svc,
            max_ops_per_service=max_ops_per_service,
            include_dryrun=include_dryrun,
            aggressive=aggressive,
            all_ops=all_ops,
            min_dryrun=min_dryrun
        )
        if verbose:
            sys.stderr.write(f"[trailblazer3] {svc}: {len(ops)} ops selected\n")
            for o in ops:
                sys.stderr.write(f"  - {o}\n")
            sys.stderr.flush()

        for op_name in ops:
            print(f"  {op_name} executed")
            try:
                execute_operation(client, svc, op_name, rec)
            except Exception as e:
                rec.write({"service": svc, "op": op_name, "status": "exception", "error": str(e)})
            time.sleep(delay)