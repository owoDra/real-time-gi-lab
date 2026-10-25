"""032 effective CPU limits and durable child-launch evidence, CPU only."""
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

ADDRESS = 4*1024**3


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def state():
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    return dict(cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                address=list(resource.getrlimit(resource.RLIMIT_AS)),
                core=list(resource.getrlimit(resource.RLIMIT_CORE)),
                sigxcpu_default=signal.getsignal(signal.SIGXCPU) == signal.SIG_DFL,
                sigxcpu_unblocked=signal.SIGXCPU not in blocked)


def limits():
    hard = resource.getrlimit(resource.RLIMIT_CPU)[1]
    if hard != resource.RLIM_INFINITY and hard < 1200:
        raise ValueError('032 inherited CPU hard limit cannot support registered native1200')
    if os.environ.get('OPENBLAS_NUM_THREADS') != '1' or os.environ.get('OMP_NUM_THREADS') != '1':
        raise ValueError('032 requires one BLAS/OMP worker')
    signal.signal(signal.SIGXCPU, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGXCPU})
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS, ADDRESS))
    resource.setrlimit(resource.RLIMIT_CPU, (360, 1200))
    observed = state()
    if observed != dict(cpu=[360, 1200], address=[ADDRESS, ADDRESS], core=[0, 0], sigxcpu_default=True, sigxcpu_unblocked=True):
        raise ValueError('032 effective parent CPU/AS/signal guard differs')
    return observed


def guarded(command, out, name, cpu=1200, wall=1800):
    out = Path(out); started = time.monotonic(); parent = state()
    write(out/(name+'.command.json'), dict(command=list(map(str, command)), cpu_limit=cpu, wall_limit=wall,
                                           address_limit=ADDRESS, parent_effective=parent))
    def child_limits():
        try:
            signal.signal(signal.SIGXCPU, signal.SIG_DFL)
            signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGXCPU})
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_AS, (ADDRESS, ADDRESS))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
            observed = state()
            if observed != dict(cpu=[cpu, cpu], address=[ADDRESS, ADDRESS], core=[0, 0], sigxcpu_default=True, sigxcpu_unblocked=True):
                raise ValueError('032 effective child guard mismatch')
            write(out/(name+'.child-limits.json'), observed)
        except Exception as e:
            write(out/(name+'.child-limit-error.json'), dict(error=type(e).__name__+': '+str(e), inherited_parent=parent))
            raise
    process = None; result = None
    with (out/(name+'.stdout')).open('xb') as stdout, (out/(name+'.stderr')).open('xb') as stderr:
        try:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=child_limits)
            write(out/(name+'.pid.json'), dict(pid=process.pid))
            try:
                code = process.wait(timeout=wall)
                result = dict(pid=process.pid, returncode=code, timed_out=False, reaped=True)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
                result = dict(pid=process.pid, returncode=process.returncode, timed_out=True, reaped=True)
        except Exception as e:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
            write(out/(name+'.process.json'), dict(launch_or_monitor_error=type(e).__name__+': '+str(e),
                                                   pid=process.pid if process else None, reaped=process is not None))
            raise
    result['diagnostic_cpu_wall_seconds'] = time.monotonic()-started
    write(out/(name+'.process.json'), result)
    if result['timed_out'] or result['returncode'] != 0:
        raise ValueError('032 process failure/timeout; preserve and stop: '+name)
    return dict(command=list(map(str, command)), **result)
