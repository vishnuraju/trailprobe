import time, sys, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from .recorder import Recorder
from .selector import select_operations_for_service
from .runner import execute_operation

class RateLimiter:
    # Simple token bucket: up to rate tokens per second per service
    def __init__(self, rate_per_sec: int):
        self.rate = max(1, rate_per_sec)
        self.allowance = self.rate
        self.last_check = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self):
        while True:
            with self.lock:
                now = time.monotonic()
                self.allowance += (now - self.last_check) * self.rate
                self.last_check = now
                if self.allowance > self.rate:
                    self.allowance = self.rate
                if self.allowance >= 1:
                    self.allowance -= 1
                    return
            # not enough tokens yet
            time.sleep(0.02)

def _run_ops_for_service(client, svc, ops, rec: Recorder, rate_limiter: RateLimiter, verbose: bool):
    # worker function
    def _do(op_name: str):
        thread_name = threading.current_thread().name
        print(f"[{thread_name}] {svc}:{op_name} executing")
        #print(f"  {op_name} executed")
        rate_limiter.acquire()
        try:
            execute_operation(client, svc, op_name, rec)
        except Exception as e:
            rec.write({"service": svc, "op": op_name, "status": "exception", "error": str(e)})

    return _do

def run_one_service(session, region, svc, *, rate_limit_per_sec, max_ops_per_service,
                    include_dryrun, aggressive, all_ops, min_dryrun, verbose, threads):
    rec = Recorder()
    print(f"Starting simulating events for {svc.upper()}")
    try:
        client = session.client(svc, region_name=region)
    except Exception as e:
        rec.write({"service": svc, "op": "-", "status": "client_error", "error": str(e)})
        return

    ops = select_operations_for_service(
        session, svc,
        max_ops_per_service=max_ops_per_service,
        include_dryrun=include_dryrun,
        aggressive=aggressive,
        all_ops=all_ops,
        min_dryrun=min_dryrun
    )
    if verbose:
        sys.stderr.write(f"[trailprobe] {svc}: {len(ops)} ops selected\n")
        for o in ops:
            sys.stderr.write(f"  - {o}\n")
        sys.stderr.flush()

    limiter = RateLimiter(rate_limit_per_sec)
    work = _run_ops_for_service(client, svc, ops, rec, limiter, verbose)

    if threads <= 1:
        for op in ops:
            work(op)
    else:
        with ThreadPoolExecutor(max_workers=threads, thread_name_prefix=f"{svc}-w") as ex:
            futures = [ex.submit(work, op) for op in ops]
            for _ in as_completed(futures):
                pass  # results already logged

def run_services(session, region, services, rate_limit_per_sec=5, max_ops_per_service=30,
                 include_dryrun=False, aggressive=False, all_ops=False,
                 min_dryrun=5, verbose=False, threads=1, parallel_services=False):
    if parallel_services and len(services) > 1:
        with ThreadPoolExecutor(max_workers=min(len(services), 8), thread_name_prefix="svc") as ex:
            futs = []
            for svc in services:
                futs.append(ex.submit(
                    run_one_service, session, region, svc,
                    rate_limit_per_sec=rate_limit_per_sec,
                    max_ops_per_service=max_ops_per_service,
                    include_dryrun=include_dryrun,
                    aggressive=aggressive,
                    all_ops=all_ops,
                    min_dryrun=min_dryrun,
                    verbose=verbose,
                    threads=threads
                ))
            for _ in as_completed(futs):
                pass
    else:
        for svc in services:
            run_one_service(session, region, svc,
                            rate_limit_per_sec=rate_limit_per_sec,
                            max_ops_per_service=max_ops_per_service,
                            include_dryrun=include_dryrun,
                            aggressive=aggressive,
                            all_ops=all_ops,
                            min_dryrun=min_dryrun,
                            verbose=verbose,
                            threads=threads)