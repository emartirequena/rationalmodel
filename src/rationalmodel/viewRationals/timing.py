import time


last_duration = 0.0
init_time = 0

def timing(f):
    def wrap(*args, **kwargs):
        global last_duration
        global init_time
        init_time = time.time()
        ret = f(*args, **kwargs)
        end_time = time.time()
        last_duration = end_time - init_time
        print(f'------- {f.__name__:s}() took {last_duration:.2f} secs')
        return ret
    return wrap

def get_duration():
    global init_time
    end_time = time.time()
    return end_time - init_time

def get_last_duration():
    return last_duration
