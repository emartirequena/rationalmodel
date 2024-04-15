import time


last_duration = 0.0

def timing(f):
    def wrap(*args, **kwargs):
        global last_duration
        time1 = time.time()
        ret = f(*args, **kwargs)
        time2 = time.time()
        last_duration = time2-time1
        print(f'------- {f.__name__:s}() took {last_duration:.2f} secs')
        return ret
    return wrap

def get_last_duration():
    return last_duration
