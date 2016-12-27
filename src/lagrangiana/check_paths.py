import math
import copy

def splitDigits(digits, base):
    ret = []
    n_dim = int(math.log(base, 2))
    for i in range(n_dim):
        ret.append([])
    for digit in digits:
        num = digit
        for i in range(n_dim):
            rem = num%2
            ret[i].append(rem)
            num = (num-rem)/2
    return ret

def joinDigits(digits):
    res = []
    for i in range(len(digits[0])):
        digit = 0
        for dim in range(len(digits)):
            digit = digit*2 + digits[dim][i]
        res.append(digit)
    return res

def getReminders(num, div, base):
    reminders = []
    rem = num
    while not rem in reminders:
        reminders.append(rem)
        rem = (rem*base)%div
    return reminders

def getNum(digits, base):
    num = 0
    for i in range(len(digits)):
        num = num*base + digits[i]
    return num 

def checkDifferences(reminders, base):
    ordered = sorted(reminders)
    diffs = []
    for i in range(len(ordered)-1):
        diffs.append(ordered[i+1]-ordered[i])
    if len(diffs) == 0:
        return True
    mindiff = min(diffs)
    checked = True
    for i in range(len(diffs)):
        diff = math.log(diffs[i]/float(mindiff), float(base))
        if float(int(diff)) != diff:
            checked = False
            break
    return checked

def generatePathsBinaries(length, ones):
    sequences = []
    sequence = [0 for _ in range(length-ones)] + [1 for _ in range(ones)]
    findPermutations(sequences, sequence, 0)
    return sequences
    
def findPermutations(sequences, sequence, position):
    l = len(sequence)
    if sequence not in sequences:
        sequences.append(sequence)
    if (position == l and sequence[position] == 0) or sequence[position] == 1:
        return
    for p in range(position, l):
        if sequence[p] == 1 and p > position and sequence[p-1] == 0:
            new_sequence = copy.copy(sequence)
            new_sequence[p-1] = 1
            new_sequence[p] = 0
            findPermutations(sequences, new_sequence, p)
            findPermutations(sequences, new_sequence, position)
            break

def checkPaths(length, num_ones):
    base = int(math.pow(2, len(num_ones))) 
    div = int(math.pow(base, length))-1
    paths = []
    for i in range(len(num_ones)-1, -1, -1):
        paths.append(generatePathsBinaries(length, num_ones[i]))
    counters = [0 for i in range(len(num_ones))]
    maxs = [len(paths[i])-1 for i in range(len(num_ones))]
    total = 0
    while True:
        binaries = []
        for dim in range(len(paths)):
            binaries.append(paths[dim][counters[dim]]) 
        digits = joinDigits(binaries)
        num = getNum(digits, base)
        reminders = getReminders(num, div, base)
        if checkDifferences(reminders, base):
            #print total, digits, reminders, num
            total += 1
        
        for dim in range(len(paths)):
            if counters[dim] < maxs[dim]:
                counters[dim] += 1
                break
            else:
                counters[dim] = 0
        if counters == [0 for i in range(len(paths))]:
            break
    return total
    #print 'Terminated: %d'%total

def checkPathsSpace(length):
    totals = [[0 for i in range(length+1)] for i in range(length+1)]
    for ny in range(length+1):
        for nx in range(length+1):
            totals[ny][nx] = checkPaths(length, [nx, ny])
        strings = ''
        for nx in range(length+1):
            strings += ('%02d '%totals[ny][nx])
        print strings
    return totals

checkPathsSpace(5)
  
