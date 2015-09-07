from PIL import Image

import progressbar
import ReedSolomon
rs = ReedSolomon.ReedSolomon()

class QRError(Exception):
    pass

class QR:
    def __init__(self, filename, mask=None):
        im = Image.open(filename)
        pix = im.load()
        self.w,self.h = im.size

        WHITE = set([(255,255,255,255), 1])
        BLACK = set([(0,0,0,255), 0])

        self.pixels = [
            [  1 if pix[x,y] in BLACK else 0 if pix[x,y] in WHITE else None for x in range(self.w) ]
            for y in range(self.h)
        ]

        if mask is not None:
            self.apply_mask(mask)

    def apply_mask(self, m):
        flipped = [ [ '`' ] * 25 for _ in range(25) ]

        masks = [
            lambda i,j: (i+j)%2 != 0,
            lambda i,j: i%2 != 0,
            lambda i,j: j%3 != 0,
            lambda i,j: (i+j)%3 != 0,
            lambda i,j: (i/2+j/3)%2 != 0,
            lambda i,j: (i*j)%2+(i*j)%3 != 0,
            lambda i,j: ((i*j)%3+i*j)%2 != 0,
            lambda i,j: ((i*j)%3+i+j)%2 != 0,
        ]

        for i in range(self.h):
            for j in range(self.w):
                if not self._is_pattern(j, i):
                    continue

                flipped[i][j] = ' '
                if not masks[m](i,j):
                    flipped[i][j] = 'X'
                    if self.pixels[i][j] is not None:
                        self.pixels[i][j] ^= 1

        for r in flipped:
            print ''.join(map(str,r))
        print ''

        return self

    #@staticmethod
    #def _normal_down_box(x, y):
    #   return [ (x,y), (x+1,y), (x,y+1), (x+1,y+1), (x,y+2), (x+1,y+2), (x,y+3), (x+1,y=3) ]
    #   #return [ (x+1, y), (x, y), (x+1, y+1), (x, y+1), (x+1, y+2), (x, y+2), (x+1, y+3), (x, y+3) ]

    #@staticmethod
    #def _normal_up_box(x, y):
    #   return [ (x,y+3), (x+1,y=3) (x,y+2), (x+1,y+2), (x,y+1), (x+1,y+1), (x,y), (x+1,y), ]
    #   #return [ (x+1, y+3), (x, y+3), (x+1, y+2), (x, y+2), (x+1, y+1), (x, y+1), (x+1, y), (x, y) ]

    #_bytes = [
    #   _down_box(23, 9),
    #   _down_box(23, 13),
    #   _down_box(23, 17),
    #   _down_box(23, 21),
    #   _up_box(21, 21),
    #   _up_box(21, 17),
    #   _up_box(21, 13),
    #   _up_box(21, 9),
    #]

    @staticmethod
    def _is_pattern(x, y):
        if x >= 17 and y <= 8: # top-right
            return False
        if x <= 8 and y <= 8: # top-left
            return False
        if y == 6 or x == 6: # timing
            return False
        if x <= 8 and y >= 17: # bottom-left
            return False
        if x >= 16 and x <= 20 and y >= 16 and y <= 20: # bottom-right
            return False
        if x <= 1 and y >= 13 and (x,y) != (1,13): # reserved
            return False

        return True

    def _get_pattern_byte(self, x, y):
        if not self._is_pattern(x, y):
            raise QRError()
        return self.pixels[y][x]

    def draw(self):
        for y in range(self.h):
            print ''.join({ 0: ' ', 1: '#', None: '?' }[b] for b in self.pixels[y])

    def get_bits(self):
        y,x = 24, 23
        y_direction = -1

        bits = [ ]

        grabbed = [ [ '_' ] * 25 for _ in range(25) ]
        n = 0

        while x >= 0:
            if x == 5: x -= 1

            try:
                bits.append(self._get_pattern_byte(x+1, y))
                #grabbed[y][x+1] = bits[-1] if bits[-1] is not None else '?'
                grabbed[y][x+1] = n
                n = (n+1)%8
            except QRError: grabbed[y][x+1] = 'X'

            #for r in grabbed:
            #   print ''.join(map(str,r))
            #raw_input()

            try:
                bits.append(self._get_pattern_byte(x, y))
                #grabbed[y][x] = bits[-1] if bits[-1] is not None else '?'
                grabbed[y][x] = n
                n = (n+1)%8
            except QRError: grabbed[y][x] = 'X'

            y += y_direction
            if y < 0:
                y = 0
                y_direction = 1
                x -= 2
            if y > 24:
                y = 24
                y_direction = -1
                x -= 2

            #for r in grabbed:
            #   print ''.join(map(str,r))
            #raw_input()

        all_bits = ''.join([ { 0:'0', 1:'1', None:'?' }[n] for n in bits ])
        all_bytes = [ ]
        for i in range(0, len(all_bits), 8):
            all_bytes.append(all_bits[i:i+8])

        return ''.join(all_bytes)

    def get_bytes(self):
        bits = self.get_bits()
        return [ bits[i:i+8] for i in range(0, len(bits), 8) ]

    def get_values(self):
        return [ (int(b, 2) if '?' not in b else -1) for b in self.get_bytes() ]

    _ASCII = [ '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', ' ', '$', '%', '*', '+', '-', '.', '/', ':', ]

    @staticmethod
    def ascii_decode(what):
        s = [ ]

        while len(what) >= 11:
            k,what = what[:11], what[11:]
            m = int(k, 2)
            try: s.append(QR._ASCII[m / 45])
            except IndexError: s.append('?')
            try: s.append(QR._ASCII[m % 45])
            except IndexError: s.append('?')

        return ''.join(s)

    @staticmethod
    def ascii_encode(what):
        s = ''
        while what:
            k,what = what[:2], what[2:]
            if len(k) == 2:
                s += bin(QR._ASCII.index(k[0])*45 + QR._ASCII.index(k[1]))[2:].rjust(11, '0')
            else:
                s += bin(QR._ASCII.index(k[0]))[2:].rjust(6, '0')
        return s

    @staticmethod
    def iter_byte_possibilities(s, start=0):
        if '?' not in s:
            yield s
            return

        for i in range(start, len(s)):
            if s[i] == '?':
                for a in QR.iter_byte_possibilities(s[:i]+'0'+s[i+1:], start=i+1):
                    yield a
                for a in QR.iter_byte_possibilities(s[:i]+'1'+s[i+1:], start=i+1):
                    yield a
                break

    @staticmethod
    def iter_chain_possibilities(s, start=0, max_unknowns=3):
        ss = list(s)
        for i in range(start, len(ss)):
            if '?' in ss[i] and ss[i].count('?') <= max_unknowns:
                for a in QR.iter_byte_possibilities(ss[i]):
                    for b in QR.iter_chain_possibilities(ss[:i] + [ a ] + ss[i+1:], start=i, max_unknowns=max_unknowns):
                        yield b
                break
        else:
            yield ss

    def tryit(self, max_unknowns, max_correct=28):
        possibilities = list(self.iter_chain_possibilities(self.get_bytes(), max_unknowns=max_unknowns))
        print "%d possibilities" % len(possibilities)

        results = [ ]

        for i in progressbar.ProgressBar()(possibilities):
            ii = [ (int(s, 2) if '?' not in s else -1) for s in i ]
            #ii[-6] = 1
            #print ii.count(-1)
            try:
                jj = rs.RSDecode(ii, max_correct)
                if jj is None:
                    continue
                kk = rs.RSDecode(jj, max_correct)
                if kk is None:
                    continue
            except ZeroDivisionError:
                #if jj is not None:
                #   print jj
                #   print "ZDE"
                continue
            something = ''.join([ bin(x)[2:].rjust(8, '0') for x in kk ])
            results.append(QR.ascii_decode(something[13:57+11*6]))
            #print results[-1]

        return results
