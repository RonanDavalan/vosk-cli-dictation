# Instance unique : verrou exclusif du noyau, propriétaire lisible sans le prendre.

import os
import subprocess
import sys
import textwrap

import pytest

from src import instance_lock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HOLDER = (
    textwrap.dedent("""
    import sys, time
    sys.path.insert(0, %r)
    from src import instance_lock
    print("held" if instance_lock.acquire() else "refused", flush=True)
    time.sleep(60)
""")
    % ROOT
)


@pytest.fixture(autouse=True)
def runtime_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(instance_lock, "_held_fd", None)
    return tmp_path


def start_holder():
    child = subprocess.Popen(
        [sys.executable, "-c", HOLDER], stdout=subprocess.PIPE, text=True
    )
    assert child.stdout.readline().strip() == "held"
    return child


def test_second_acquire_is_refused_while_first_lives():
    child = start_holder()
    try:
        assert instance_lock.acquire() is False
        assert instance_lock.owner_pid() == child.pid
    finally:
        child.kill()
        child.wait()


def test_lock_is_released_by_kernel_after_sigkill():
    child = start_holder()
    child.kill()
    child.wait()
    assert instance_lock.acquire() is True
    assert instance_lock.owner_pid() == os.getpid()
    os.close(instance_lock._held_fd)


def test_owner_pid_none_without_file(runtime_dir):
    assert instance_lock.owner_pid() is None


def test_owner_pid_none_for_dead_pid(runtime_dir):
    dead = subprocess.Popen(["true"])
    dead.wait()
    open(instance_lock.lock_path(), "w").write("%d 1\n" % dead.pid)
    assert instance_lock.owner_pid() is None


def test_owner_pid_none_when_birth_differs(runtime_dir):
    me = os.getpid()
    open(instance_lock.lock_path(), "w").write(
        "%d %d\n" % (me, instance_lock._birth_ticks(me) + 1)
    )
    assert instance_lock.owner_pid() is None


def test_owner_pid_does_not_take_the_lock():
    child = start_holder()
    try:
        instance_lock.owner_pid()
        child.kill()
        child.wait()
        assert instance_lock.acquire() is True
        os.close(instance_lock._held_fd)
    finally:
        if child.poll() is None:
            child.kill()
