import random
import tempfile

from machi import MachiStore


def test_smoke():
    testdir = tempfile.TemporaryDirectory()
    machi = MachiStore(maxlen=37, temp=True)
    try:

        key = machi.append(b"1")
        data = machi.get(*key)
        assert b"1" == data

        machi.trim(*key)
        data = machi.get(*key)
        assert data is None
        keys = {}
        repeat = 683
        for i in random.sample(range(repeat), repeat):
            key = machi.append(str(i).encode())
            keys[i] = key

        for i in random.sample(range(repeat), repeat):
            key = keys[i]
            data = machi.get(*key)
            assert str(i).encode() == data

        for key in machi.keys():
            assert isinstance(key, tuple)

        for i in random.sample(range(repeat), repeat):
            key = keys[i]
            machi.trim(*key)

        for i in random.sample(range(repeat), repeat):
            key = keys[i]
            data = machi.get(*key)
            assert data is None

    finally:
        machi.close()
        testdir.cleanup()


def test_persistence():
    with tempfile.TemporaryDirectory() as testdir:
        machi = MachiStore(maxlen=29, temp=False, dir=testdir)
        try:
            for key in machi.keys():
                assert isinstance(key, tuple)
            key = machi.append(b"1")
            assert b"1" == machi.get(*key)
        finally:
            machi.close()

        machi = MachiStore(maxlen=29, temp=False, dir=testdir)
        try:
            for key in machi.keys():
                assert isinstance(key, tuple)
            keys = list(machi.keys())
            assert 1 == len(keys)
            key = keys[0]
            assert b"1" == machi.get(*key)
        finally:
            machi.close()

import os
def test_file_deletion():
    with tempfile.TemporaryDirectory() as testdir:
        keys = []
        with MachiStore(maxlen=29, temp=False, dir=testdir) as machi:
            key = machi.append(b"1")
            keys.append(key)
            assert b"1" == machi.get(*key)

        with MachiStore(maxlen=29, temp=False, dir=testdir) as machi:
            for key in keys:
                machi.trim(*key)
            assert 0 == len(list(machi.keys()))

        with MachiStore(maxlen=29, temp=False, dir=testdir) as machi:
            assert 0 == len(list(machi.keys()))


def test_file_deletion2():
    with tempfile.TemporaryDirectory() as testdir:
        keys = []
        with MachiStore(maxlen=29, temp=False, dir=testdir) as machi:
            key = machi.append(b"1")
            keys.append(key)
            assert b"1" == machi.get(*key)

        with open(os.path.join(testdir, '1.machi'), 'wb') as fp:
            pass
        with open(os.path.join(testdir, '1.machd'), 'wb') as fp:
            pass

        for f in os.scandir(testdir):
            print(f.name, f.stat().st_size)

        with MachiStore(maxlen=29, temp=False, dir=testdir) as machi:
            for i in range(30):
                key = machi.append(str(i).encode())
                keys.append(key)
                assert str(i).encode() == machi.get(*key)

            assert 8 == len(os.listdir(testdir))

            for key in keys:
                machi.trim(*key)
            assert 0 == len(list(machi.keys()))

        with MachiStore(maxlen=29, temp=False, dir=testdir) as machi:
            assert 0 == len(list(machi.keys()))
