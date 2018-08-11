
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

def getPeriod(reminders):
    for T in range(1, len(reminders)):
        if reminders[0] == reminders[T]:
            return T
    return len(reminders) 

def getDiff(l):
    L = len(l)
    dif = [0 for i in range(1, L)]
    for i in range(1, L):
        dif[i-1] = l[i] - l[i-1]
    return dif



def lagrangian2d():
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
        
def lagrangian1d(L, nx):
    lagrangian_x = getLagrangian(L, nx)
    print ''.join(map(lambda x:str(x), lagrangian_x))
    
def lagrangianMap2d():
    T=15
    c=0.5
    m = [[0 for _ in range(T)] for _ in range(T)]
    for dx in range(T):
        x = dx - c*T
        nx = c*T - x
        for dy in range(T):
            y = dy - c*T
            ny = c*T - y
            t = int(max(nx, ny))
            if t > 0:
                lagrangian = getLagrangian(t, int(min(nx, ny)))
                st = [0 for _ in range(t)]
                digits = getDigits2d(lagrangian, st)
                reminders = getReminders(digits, 4)
                period = getPeriod(reminders)
                m[dy][dx] += period 
    
    for dx in range(T):
        sl = ''
        for dy in range(T):
            sl += '%2d '%m[dy][dx]
        print sl
            
lagrangianMap2d()