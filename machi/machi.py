'''Machi

A file store only with append and trim.

See also: https://github.com/basho/machi

Index files has filename <gen>.machi

Index entry format:

0       8       16      24  28  32bytes
+-------+-------+-------+---+---+
|gen    |offset |length |crc|st |
+-------+-------+-------+---+---+

Indices are appended to index files. Number of max entries per index
file is to be preset.

Data files has filename <gen>.machd

'''
import binascii
import os
from struct import pack, unpack, calcsize
from typing import Optional

from .rwlock import RWLock

class _MachiGen:
    index_format = 'QQQIi'
    
    def __init__(self, dir, gen):
        self.gen = gen
        self.dir = dir
        self.index = {}
        flag = os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_TRUNC
        self.indexname = os.path.join(self.dir, f'{self.gen}.machi')
        self.indexfile = os.open(self.indexname, flag)
        self.dataname = os.path.join(self.dir, f'{self.gen}.machd')
        self.datafile = os.open(self.dataname, flag)
        self.size = 0
        self._ref = 0

        self.index_pos = 0
        self.pos = 0
        
    def __len__(self):
        return self.size
    
    @property
    def ref(self):
        return self._ref

    def append(self, data):
        self.size += 1
        self._ref += 1
        
        pos = self.pos
        r = os.pwrite(self.datafile, data, pos)
        assert len(data) == r
        self.pos += len(data)
        
        crc = binascii.crc32(data)
        buf = pack(self.index_format, self.gen, pos,
                   len(data), crc, 1)
        # print('append>', self.front, crc, data, self.pos, len(data))
        r = os.pwrite(self.indexfile, buf, self.index_pos)
        assert 32 == r # calcsize(self.index_format)
        self.index[pos] = (len(data), crc, 1, self.index_pos)
        self.index_pos += r

        return pos, len(data)
    
    def get(self, offset, length):
        if offset not in self.index:
            return None
        
        length1, crc, st, _ = self.index[offset]
        data = os.pread(self.datafile, length, offset)
        if st == -1:
            # Trimmed
            return None
        elif st != 1:
            raise RuntimeError("Invalid State {} to read {},{} @{}".format(
                st, offset, length, self.dataname))

        if length == length1:
            assert crc == binascii.crc32(data)
            
        return data
    
    def trim(self, offset, length):
        if offset not in self.index:
            return None
        
        length1, crc, st, index_pos = self.index[offset]
        data = os.pread(self.datafile, length, offset)
        if st == -1:
            # Trimmed
            return None
        assert length == length1

        buf = pack(self.index_format, self.gen, offset,
                   len(data), crc, -1)
        r = os.pwrite(self.indexfile, buf, index_pos)
        # print('append>', self.front, crc, data, self.pos, len(data))

        assert 32 == r # calcsize(self.index_format)
        self.index[offset] = (length, crc, -1, index_pos)

        self._ref -= 1
    
    def close(self):
        os.close(self.indexfile)
        os.close(self.datafile)
        os.remove(self.indexname)
        os.remove(self.dataname)


class MachiStore:
    def __init__(self, dir='/tmp', maxlen=1024*1024):
        # TODO(kuenishi): Load existent files
        self.gen = 0
        self.dir = dir
        self.maxlen = maxlen
        
        self.front = _MachiGen(self.dir, self.gen)
        assert self.front is not None
        
        self.back = {}
        
        self.rwlock = RWLock()

    def append(self, data: bytes): # -> File, offset, length
        with self.rwlock.wrlock():
            result = self.front.append(data)
            gen = self.gen
            if len(self.front) >= self.maxlen:
            
                if self.front.ref == 0:
                    self.front.close()
                else:
                    self.back[self.gen] = self.front
                    self.gen += 1

                self.front = _MachiGen(self.dir, self.gen)
        
            offset, length = result
            return gen, offset, length
    
    def get(self, gen, offset, length) -> Optional[bytes]:
        with self.rwlock.rdlock():
            if gen == self.gen:
                return self.front.get(offset, length)
        
            f = self.back.get(gen)
            # print(f)
            # print(self.back)
            if f:
                return f.get(offset, length)
        
            return None

    def trim(self, gen, offset, length):
        with self.rwlock.wrlock():
            if gen == self.gen:
                self.front.trim(offset, length)
                return
        
            f = self.back.get(gen)

            if f:
                f.trim(offset, length)
                if f.ref == 0:
                    f.close()
                    self.back.pop(gen)
        
            return None

    def close(self):
        with self.rwlock.wrlock():
            self.front.close()
            for store in self.back.values():
                store.close()
