from math import sqrt

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
    '''lists prime factors, from greatest to smallest'''  
    i = 2
    while i<=sqrt(n):
        if n%i==0:
            l = primefactors(n/i)
            l.append(i)
            return l
        i+=1
    return [n]      # n is prime

def factorGenerator(n):
    p = primefactors(n)
    factors={}
    for p1 in p:
        try:
            factors[p1]+=1
        except KeyError:
            factors[p1]=1
    return factors

def divisores(n):
    factors = factorGenerator(n)
    divisors=[]
    listexponents=[map(lambda x:k**x,range(0,factors[k]+1)) for k in factors.keys()]
    listfactors=cartesianproduct(listexponents)
    for f in listfactors:
        divisors.append(reduce(lambda x, y: x*y, f, 1))
    divisors.sort()
    return divisors

   