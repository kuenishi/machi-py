import pytest
from machi.rwlock import RWLock


def test_rwlock():
    lock = RWLock(reentrant=False)

    with pytest.raises(RuntimeError):
        lock.rdlock()
        lock.rdlock()

    lock = RWLock(reentrant=True)

    lock.rdlock()
    lock.rdlock()
    lock.unlock()
