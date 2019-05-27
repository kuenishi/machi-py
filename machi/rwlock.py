import threading


class LockContext:
    def __init__(self, locked_lock):
        self.locked_lock = locked_lock

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.locked_lock.unlock()


class RWLock:
    """Reader-writer lock

    TODO(kuenishi): Add unit tests

    """

    def __init__(self, reentrant=True):
        self.cv = threading.Condition()
        self.writer = None
        self.reader = set()
        self.reentrant = reentrant

    def rdlock(self):
        with self.cv:
            self.cv.wait_for(lambda: self.writer is None)
            thread_id = threading.get_ident()
            if not self.reentrant and thread_id in self.reader:
                raise RuntimeError("The lock is not reentrant")
            self.reader.add(threading.get_ident())
            return LockContext(self)

    def wrlock(self):
        with self.cv:
            thread_id = threading.get_ident()
            self.cv.wait_for(
                lambda: self.writer is None
                and self.writer != thread_id
                and len(self.reader) == 0
            )
            self.writer = thread_id
            return LockContext(self)

    def unlock(self):
        with self.cv:
            thread_id = threading.get_ident()
            if self.writer == thread_id:
                self.writer = None
            elif self.reentrant and thread_id in self.reader:
                self.reader.remove(thread_id)
            self.cv.notify_all()


class DummyLock:
    """Dummy class for multithread-unsafe fast cache class
    """

    def __init__(self):
        pass

    def rdlock(self):
        return LockContext(self)

    def wrlock(self):
        return LockContext(self)

    def unlock(self):
        pass
