import os
from functools import reduce
from copy import copy
import subprocess
from PIL import Image
from PyQt5 import QtGui
from math import sqrt

def lerp(t, ta, a, tb, b):
    return a + (b-a)*(t-ta)/(tb-ta)


def check_ffmpeg(ffmpeg_path: str) -> bool:
    return os.path.exists(ffmpeg_path)


def pil2pixmap(img):
    if img.mode == "RGB":
        r, g, b = img.split()
        img = Image.merge("RGB", (b, g, r))
    elif  img.mode == "RGBA":
        r, g, b, a = img.split()
        img = Image.merge("RGBA", (b, g, r, a))
    elif img.mode == "L":
        img = img.convert("RGBA")
    img2 = img.convert("RGBA")
    data = img2.tobytes("raw", "RGBA")
    qimg = QtGui.QImage(data, img.size[0], img.size[1], QtGui.QImage.Format_ARGB32)
    pixmap = QtGui.QPixmap.fromImage(qimg)
    return pixmap


def make_video(
        ffmpeg_path: str, 
        in_sequence_path: str, 
        out_video_path: str, 
        video_codec: str='prores', 
        video_format: str='mov', 
        frame_rate: int=1, 
        bit_rate: int=4000, 
        image_resx: int=1920, 
        image_resy: int=1080
):
    if not check_ffmpeg(ffmpeg_path):
        return False
    options = [
        ffmpeg_path,
        '-y',
        '-r', f'{frame_rate}',
        '-i', in_sequence_path,
        '-c', video_codec,
        '-f', video_format,
        '-b:v', f'{bit_rate}',
        '-s', f'{image_resx}x{image_resy}',
        out_video_path,
    ]
    print(*options)
    subprocess.run(options)
    return True


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
    # limit:int = n // (4 if n < 100000000 else 4096)
    limit:int = int(sqrt(float(n)))
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