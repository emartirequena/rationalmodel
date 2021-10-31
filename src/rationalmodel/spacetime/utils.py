from math import sqrt
from functools import reduce
from collections import OrderedDict as odict

def appendEs2Sequences(sequences,es):
    result=[]
    if not sequences:
        for e in es:
            result.append([e])
    else:
        for e in es:
            result+=[seq+[e] for seq in sequences]
    return result

def cartesianproduct(lists):
    """
    given a list of lists,
    returns all the possible combinations taking one element from each list
    The list does not have to be of equal length
    """
    return reduce(appendEs2Sequences,lists,[])

def primefactors(n):
    """lists prime factors, from greatest to smallest"""
    i = 2
    while i<=sqrt(n):
        if n%i==0:
            l = primefactors(int(n/i))
            l.append(i)
            return l
        i+=1
    return [n]      # n is prime

def factorGenerator(n):
    p = primefactors(n)
    factors=odict()
    for p1 in p:
        try:
            factors[p1]+=1
        except KeyError:
            factors[p1]=1
    factors = odict(sorted(factors.items(), key=lambda t:t[0]))
    return factors

def divisors(n):
    factors = factorGenerator(n)
    divisors=[]
    listexponents=[list(map(lambda x:int(k**x),range(0, factors[k]+1))) for k in factors.keys()]
    listfactors=cartesianproduct(listexponents)
    for f in listfactors:
        divisors.append(reduce(lambda x, y: int(x*y), f, 1))
    divisors.sort()
    return divisors


if __name__ == '__main__':
    print(primefactors(952567894321457193))