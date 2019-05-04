import argparse
import binascii
import random
import time

import numpy

from machi import MachiStore

class Timer:
    def __init__(self, stats):
        self.stats = stats
        
    def __enter__(self):
        self.b = time.time()
        
    def __exit__(self, exc_type, exc_value, traceback):
        e = time.time()
        self.stats.append(e-self.b)

class Stats:
    def __init__(self, name):
        self.stats = []
        self.name = name

    def measure(self):
        return Timer(self)
    
    def append(self, duration):
        self.stats.append(duration)
        
    def pp(self):
        if self.stats:
            print(self.name, sum(self.stats) / len(self.stats))
        

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--maxlen', type=int, help="Max len",
                        default=4096)
    parser.add_argument('--dir', type=str, help="Data Directory",
                        default="/tmp")
    parser.add_argument('--interval', type=int, help="interval",
                        default=1)
    args = parser.parse_args()
    assert args.interval > 0
    print(args)
    
    machi = MachiStore(maxlen=args.maxlen, dir=args.dir)
    append_stats = Stats('append time (sec)')
    sample_stats = Stats('sample time (sec)')
    timer = time.time()
    keys = []
    counter = 0
    tenM = 1024 * 1024 * 10
    oneM = 1024 * 1024
    while True:
        length = random.randint(oneM, tenM)
        buf = numpy.random.bytes(length)
        crc = binascii.crc32(buf)
        with append_stats.measure():
            key = machi.append(buf)
            keys.append( (key, crc) )

        if len(keys) > 10:
            with sample_stats.measure():
                test_keys = random.sample(keys, 10)
                for key, crc0 in test_keys:
                    data = machi.get(*key)
                    crc = binascii.crc32(data)
                    assert crc0 == crc

        if len(keys) > 1024 * 1024:
            key = random.sample(keys.keys(), 1)
            machi.trim(*key)
                    
        counter += 1
        t = time.time()
        if t > timer + args.interval:
            print("Counter:", counter)
            append_stats.pp()
            sample_stats.pp()
            timer = t
    

if __name__ == '__main__':
    main()
