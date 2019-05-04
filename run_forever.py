import argparse
import random
import time

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
        print(self.name, sum(self.stats) / len(self.stats))
        

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--maxlen', type=int, help="Max len",
                        default=65536)
    parser.add_argument('--dir', type=str, help="Data Directory",
                        default="/tmp")
    args = parser.parse_args()
    
    print(args)
    
    machi = MachiStore(maxlen=args.maxlen, dir=args.dir)
    append_stats = Stats('append time (sec)')
    sample_stats = Stats('sample time (sec)')
    timer = time.time()
    keys = []
    while True:
        i = random.randint(0, 345678)
        with append_stats.measure():
            key = machi.append(str(i).encode())
            keys.append( (key, i) )

        if len(keys) > 10:
            with sample_stats.measure():
                test_keys = random.sample(keys, 10)
                for key, i in test_keys:
                    data = machi.get(*key)
                    assert data == str(i).encode()
                    
        t = time.time()
        if t > timer + 1:
            append_stats.pp()
            sample_stats.pp()
            timer = t
    

if __name__ == '__main__':
    main()
