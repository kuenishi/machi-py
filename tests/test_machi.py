import random

from machi import MachiStore

def test_smoke():
    machi = MachiStore(maxlen=37)
    try:
        
        key = machi.append(b'1')
        data = machi.get(*key)
        assert b'1' == data
        
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
            
        for i in random.sample(range(repeat), repeat):
            key = keys[i]
            machi.trim(*key)

        for i in random.sample(range(repeat), repeat):
            key = keys[i]
            data = machi.get(*key)
            assert None == data
        
    finally:
        machi.close()
