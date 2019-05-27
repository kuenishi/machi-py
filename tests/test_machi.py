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
            # print(key)

        for i in random.sample(range(repeat), repeat):
            key = keys[i]
            # print(key)
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
