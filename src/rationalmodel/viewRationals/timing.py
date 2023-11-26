import time

def timing(f):
    def wrap(*args, **kwargs):
        time1 = time.time()
        ret = f(*args, **kwargs)
        time2 = time.time()
        print(f'------- {f.__name__:s}() took {(time2-time1):.2f} secs')
        return ret
    return wrap


