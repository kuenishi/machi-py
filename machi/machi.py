"""Machi

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

"""
import binascii
import glob
import os
from struct import pack, unpack, calcsize
from typing import Optional

from .rwlock import RWLock


class _MachiGen:
    index_format = "QQQIi"
    index_format_size = calcsize(index_format)

    def __init__(self, dir, gen, creat=True, temp=False):
        self.gen = gen
        self.dir = dir
        self.temp = temp
        self.index = {}
        self.indexname = os.path.join(self.dir, f"{self.gen}.machi")
        self.dataname = os.path.join(self.dir, f"{self.gen}.machd")
        self._ref = 0
        if creat:
            flag = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_TRUNC
            self.indexfile = os.open(self.indexname, flag)
            self.datafile = os.open(self.dataname, flag)
            self._ref = 0

            self.index_pos = 0
            self.pos = 0
        else:
            index_stat = os.stat(self.indexname)
            self.index_pos = index_stat.st_size
            if self.index_pos % self.index_format_size != 0:
                print("Partial write happened previous era")
                remain = self.index_pos % self.index_format_size
                self.index_pos -= remain

            data_stat = os.stat(self.dataname)
            self.pos = data_stat.st_size

            # Renaming original index file to a backup, then copy back
            # to a fresh one. This is because Linux BUG, pwrite(2)
            # says:
            # 
            # "POSIX requires that opening a file with the O_APPEND
            # flag should have no effect on the location at which
            # pwrite() writes data.  However, on Linux, if a file is
            # opened with O_APPEND, pwrite() appends data to the end
            # of the file, regardless of the value of offset."
            bak = '{}.bak'.format(self.indexname)
            os.rename(self.indexname, bak)
            flag = os.O_RDWR | os.O_EXCL | os.O_CREAT | os.O_TRUNC
            self.indexfile = os.open(self.indexname, flag)
            bufsize = 4 * 1024 * 1024
            with open(bak, 'rb') as fp:
                while True:
                    buf = os.read(fp.fileno(), bufsize)
                    if not buf:
                        break
                    os.write(self.indexfile, buf)

            index_pos = 0
            while index_pos < self.index_pos:
                data = os.pread(self.indexfile, self.index_format_size,
                                index_pos)
                g, o, l, c, s = unpack(self.index_format, data)
                assert g == gen
                self.index[o] = l, c, s, index_pos

                if s == 1:
                    self._ref += 1

                index_pos += self.index_format_size

            self.datafile = os.open(self.dataname, os.O_RDONLY)

    def __len__(self):
        return len(self.index) - self._ref

    @property
    def ref(self):
        return self._ref

    def append(self, data):
        self._ref += 1

        pos = self.pos
        r = os.pwrite(self.datafile, data, pos)
        assert len(data) == r
        self.pos += len(data)

        crc = binascii.crc32(data)
        buf = pack(self.index_format, self.gen, pos, len(data), crc, 1)
        # print('append>', self.front, crc, data, self.pos, len(data))
        r = os.pwrite(self.indexfile, buf, self.index_pos)
        assert 32 == r  # calcsize(self.index_format)
        self.index[pos] = (len(data), crc, 1, self.index_pos)
        self.index_pos += r

        return pos, len(data)

    def keys(self):
        for pos in self.index.keys():
            l, c, s, p = self.index[pos]
            if s == 1:
                yield self.gen, pos, l

    def get(self, offset, length):
        if offset not in self.index:
            return None

        length1, crc, st, _ = self.index[offset]
        data = os.pread(self.datafile, length, offset)

        if st == -1:
            # Trimmed
            return None
        elif st != 1:
            raise RuntimeError(
                "Invalid State {} to read {},{} @{}".format(
                    st, offset, length, self.dataname
                )
            )

        if length == length1:
            assert crc == binascii.crc32(data)

        return data

    def trim(self, offset, length):
        if offset not in self.index:
            return None

        length1, crc, st, index_pos = self.index[offset]
        # data = os.pread(self.datafile, length, offset)
        if st == -1:
            # Trimmed
            return None
        # assert length == length1

        buf = pack(self.index_format, self.gen, offset, length1, crc, -1)
        r = os.pwrite(self.indexfile, buf, index_pos)
        # print('append>', self.front, crc, data, self.pos, len(data))

        assert 32 == r  # calcsize(self.index_format)
        self.index[offset] = (length, crc, -1, index_pos)

        self._ref -= 1

    def close(self):
        os.close(self.indexfile)
        os.close(self.datafile)
        if self.temp or self._ref == 0:
            os.remove(self.indexname)
            os.remove(self.dataname)


def _parse_file(path):
    print("Previous era data {} found. Loading...".format(path))
    dir, file = os.path.split(path)
    base, ext = os.path.splitext(file)
    assert ext == ".machi"
    gen = int(base)
    return gen, _MachiGen(dir, gen, creat=False, temp=False)


class MachiStore:
    def __init__(self, dir="/tmp", maxlen=1024 * 1024, temp=False):
        self.dir = dir
        self.temp = temp

        self.back = {}

        # TODO(kuenishi): Load existent files
        if self.temp:
            for file in glob.iglob(os.path.join(dir, "[0-9]*.machi")):
                raise RuntimeError("temp but file exists: " + file)
            for file in glob.iglob(os.path.join(dir, "[0-9]*.machd")):
                raise RuntimeError("temp but file exists: " + file)

        for file in glob.iglob(os.path.join(dir, "[0-9]*.machi")):
            gen, machi_gen = _parse_file(file)
            self.back[gen] = machi_gen

        self.gen = 0
        if self.back:
            self.gen = max(self.back.keys()) + 1

        self.maxlen = maxlen

        self.front = _MachiGen(self.dir, self.gen, temp=self.temp)
        assert self.front is not None

        self.rwlock = RWLock()

    def append(self, data: bytes):  # -> File, offset, length
        with self.rwlock.wrlock():
            result = self.front.append(data)
            gen = self.gen
            if len(self.front) >= self.maxlen:

                if self.front.ref == 0:
                    self.front.close()
                else:
                    self.back[self.gen] = self.front
                    self.gen += 1

                self.front = _MachiGen(self.dir, self.gen, temp=self.temp)

            offset, length = result
            return gen, offset, length

    def keys(self):
        with self.rwlock.rdlock():
            for key in self.front.keys():
                yield key
            for gen in self.back.keys():
                for key in self.back[gen].keys():
                    yield key

    def get(self, gen, offset, length) -> Optional[bytes]:
        with self.rwlock.rdlock():
            if gen == self.gen:
                return self.front.get(offset, length)

            f = self.back.get(gen)

            if f is not None:
                return f.get(offset, length)

            return None

    def trim(self, gen, offset, length):
        with self.rwlock.wrlock():
            if gen == self.gen:
                self.front.trim(offset, length)
                return

            f = self.back.get(gen)

            if f is not None:
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
