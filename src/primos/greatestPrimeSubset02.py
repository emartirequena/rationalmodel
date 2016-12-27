from fractions import gcd
import random
import time
from copy import copy

def createSet(size, init, end):
    if size > (end - init):
        print 'ERROR: size greatest than interval'
        return set()
    random.seed(int(time.time()))
    selected = []
    while len(selected) < size:
        n = random.randint(init, end)
        if n not in selected:
            selected.append(n)
    return selected
        
def gps(elements):
    random.seed(int(time.time()))
    newelements = copy(elements)
    random.shuffle(newelements)
    subset = []
    while len(newelements) > 0:
        elem = newelements.pop()
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

def stat(elements, trials):
    stats = {}
    for i in range(0, trials):
        res = gps(elements)
        if not res in stats:
            stats[res] = 1
        else:
            stats[res] += 1
        if i % 100 == 0:
            print '%7d'%i
    print
    return stats

def writeStats(fname, size, init, end, trials, numsets):
    stats = []
    for i in range(numsets):
        elements = createSet(size, init, end)
        print 'i =', i
        stats.append(stat(elements, trials))

    fp = open(fname, 'wt')
    fp.write('size;%d\n'%size)
    fp.write('trials;%d\n'%trials)
    fp.write(';')
    for i in range(numsets):
        fp.write('%d;'%i)
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


writeStats('gps02_4000_100KTrials.csv', 4000, 1, 40000, 100000, 4)
