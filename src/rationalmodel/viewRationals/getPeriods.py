import os
from utils import getPeriod, divisors

root = 'C:\\users\\emart\\onedrive\\documentos\\enrique\\rationalmodel'
max_num = 400

def main():
    bases = [4, 8]

    fname = os.path.join(root, 'periods.txt')

    with open(fname, 'wt') as fp:
        for base in bases:
            for num in range(1, max_num, 2):
                period = getPeriod(num, base)
                special = base**(period // 2) + 1
                if special >= 18446744073709551617:
                    continue
                print(num, period, special)
                specials = divisors(special)
                if num in specials:
                    fp.write(f'{base}: {num:4d}, {period:2d}\n')
                    fp.flush()


if __name__ == '__main__':
    main()
