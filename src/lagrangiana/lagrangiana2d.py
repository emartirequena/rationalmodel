
def shiftList(l, d):
    n = d % len(l)
    return l[n:] + l[:n]    

def getLagrangian(T, n):
    k = float(n)/float(T)
    lagrangian = [0 for i in range(T)]
    e = 0.5
    for i in range(T):
        d = int(e+k)
        lagrangian[i] = d
        e = e + k - d
    return lagrangian

def getDigits2d(lagrangian_x, lagrangian_y):
    L = len(lagrangian_x)
    digits = [0 for i in range(L)]
    for i in range(L):
        digits[i] = lagrangian_y[i]*2 + lagrangian_x[i]
    return digits

def getDigits3d(lagrangian_x, lagrangian_y, lagrangian_z):
    L = len(lagrangian_x)
    digits = [0 for i in range(L)]
    for i in range(L):
        digits[i] = (lagrangian_y[i]*2 + lagrangian_x[i])*2 + lagrangian_z[i]
    return digits

def getReminders(digits, base):
    L = len(digits)
    N = pow(base, L)-1
    reminder = 0
    for i in range(L):
        reminder = reminder*base + digits[i]
    reminders = [0 for i in range(L)]
    reminders[0] = reminder
    for i in range(1, L):
        reminders[i] = (reminders[i-1]*base)%N
    return reminders

def getDiff(l):
    L = len(l)
    dif = [0 for i in range(1, L)]
    for i in range(1, L):
        dif[i-1] = l[i] - l[i-1]
    return dif

L = 7
nx = 1
ny = 2
base = 4
lagrangian_x = getLagrangian(L, nx)
lagrangian_y = getLagrangian(L, ny)
for dx in range(L):
    slx = shiftList(lagrangian_x, dx)
    for dy in range(L):
        sly = shiftList(lagrangian_y, dy)
        digits = getDigits2d(slx, sly)
        print digits
        reminders = getReminders(digits, base)
        print reminders
        reminders.sort()
        dif = getDiff(reminders)
        res = [0 for i in range(len(dif))]
        for i in range(len(dif)):
            res[i] = dif[i]/float(min(dif))
        print res
        
