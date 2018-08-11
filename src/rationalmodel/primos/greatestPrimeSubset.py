from fractions import gcd
import random
import time

def gps(ini, size):
    random.seed(int(time.time()))
    interval = range(ini, ini+size)
    random.shuffle(interval)
    subset = []
    for elem in interval:
        if len(subset) == 0:
            subset.append(elem)
        else:
            prime = True
            for subelem in subset:
                if gcd(elem, subelem) != 1:
                    prime = False
                    break
            if prime:
                subset.append(elem)
    return len(subset)


def stat(ini, size, trials):
    stats = {}
    for i in range(0, trials):
        res = gps(ini, size)
        if not res in stats:
            stats[res] = 1
        else:
            stats[res] += 1
        if i % 10000 == 0:
            print '%7d'%i
    print
    return stats

def writeStats(fname, size, trials):
    stats = []
    ini = 1
    for i in range(11):
        print 'ini =', ini
        stats.append(stat(ini, size, trials))
        ini *= 10

    fp = open(fname, 'wt')
    fp.write('size;%d\n'%size)
    fp.write('trials;%d\n'%trials)
    fp.write(';')
    ini = 1
    for i in range (11):
        fp.write('%d;'%ini)
        ini *= 10
    fp.write('\n')
    init = 10000000
    end = 0
    for st in stats:
        if min(st) < init:
            init = min(st)
        if max(st) > end:
            end = max(st) 
    for n in range(init, end+1):
        fp.write('%d;'%n)
        for st in stats:
            if n in st:
                fp.write('%d;'%st[n])
            else:
                fp.write(';')
        fp.write('\n')
    fp.close()


writeStats('gps_3MTrials.csv', 200, 3000000)
