from functools import reduce
from copy import copy

def appendEs2Sequences(sequences, es):
    result=[]
    if not sequences:
        for e in es:
            result.append([e])
    else:
        for e in es:
            result+=[seq+[e] for seq in sequences]
    return result

def cartesianproduct(lists) :
    """
    given a list of lists,
    returns all the possible combinations taking one element from each list
    The list does not have to be of equal length
    """
    return reduce(appendEs2Sequences, lists, [])

def primefactors(n: int) -> list[int]:
    """lists prime factors, from greatest to smallest"""
    i:int = 3
    limit:int = n // (4 if n < 100000000 else 4096)
    while i <= limit:
        if n % i == 0:
            lst: list[int] = primefactors(n // i)
            lst.append(i)
            return lst
        i+=2
    return [n]      # n is prime

def factorGenerator(n: int) -> dict:
    p = primefactors(n)
    factors= dict()
    for p1 in p:
        try:
            factors[p1]+=1
        except KeyError:
            factors[p1]=1
    factors = dict(sorted(factors.items(), key=lambda t:t[0]))
    return factors

def divisors(n: int) -> list[int]:
    factors = factorGenerator(n)
    divisors: list[int] = []
    listexponents: list[int] = [list(map(lambda x:int(k**x),range(0, factors[k]+1))) for k in factors.keys()]
    listfactors: list[int] = cartesianproduct(listexponents)
    for f in listfactors:
        divisors.append(reduce(lambda x, y: int(x*y), f, 1))
    divisors.sort()
    return divisors

def getExponentsFromFactors(factors: dict, exponents: list[int]) -> dict:
    out: dict = copy(factors)
    keys: list = list(factors.keys())
    for index in range(0, len(exponents)):
        e: int = exponents[index]
        if e == 1:
            out[keys[index]] = 0
        else:
            r: int = e
            for factor in range(0, factors[keys[index]] + 1):
                r = r // keys[index]
                if r == 1:
                    break
            out[keys[index]] = factor + 1
    return out

def getDivisorsAndFactors(n: int, base: int) -> dict:
    factors = factorGenerator(n)
    divisors: dict = {}
    listexponents: list[list[int]] = [list(map(lambda x:int(k**x),range(0, factors[k]+1))) for k in factors.keys()]
    listfactors: list[list[int]] = cartesianproduct(listexponents)
    for f in listfactors:
        number: int = reduce(lambda x, y: int(x*y), f, 1)
        record: dict = {
            'number': number,
            'period': getPeriod(number, base),
            'factors': getExponentsFromFactors(factors, listfactors[listfactors.index(f)])
        }
        divisors[number] = record
    divisors = {k: v for k, v in sorted(divisors.items(), key=lambda item: item[1]['number'])}
    return divisors

def getPeriod(n: int, base: int) -> int:
    if n == 1:
        return 1
    reminder = 1
    p = 1
    while True:
        reminder = (reminder * base) % n
        if reminder == 1:
            break
        p = p + 1
    return p


if __name__ == '__main__':
    print(getDivisorsAndFactors(4**4-1, 4))