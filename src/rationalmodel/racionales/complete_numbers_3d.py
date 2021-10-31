from math import pow
import utils

even = set()
odd = set()
def factorize(T):
    global even, odd
    n = int(pow(8, T))-1
    factors = utils.factorGenerator(n)
    divisors = utils.divisors(n)
    if not T%2:
        even.update(divisors)
    else:
        odd.update(divisors)
    print '%2d %28d %9d  '%(T, n, len(divisors)),
    for f in factors:
        if factors[f] == 1:
            print f,
        else:
            print '%d^%d'%(f, factors[f]),
    print
print '%2s %28s %9s   %s'%('T', 'complete numbers', 'divisors', 'factors')
print '-'*2, '-'*28, '-'*9, ' ', '-'*42

for T in range(1, 31, 1):
    factorize(T)

print ' '
print 'divisors with T odd %d, T even %d, proportion odd/even %5.2f%%'%(
    len(odd), len(even), float(len(odd))/float(len(even))*100.0
)
