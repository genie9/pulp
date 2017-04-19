#https://github.com/davidmerfield/randomColor
#https://github.com/kevinwuhoo/randomcolor-py
import randomcolor, io, random, sys

args = sys.argv

a = 'red' #args[1]
print a
b = 'blue' #args[2]
print b
c = 'yellow'
m = 'monochrome'

rand_color = randomcolor.RandomColor(13)

c_br = rand_color.generate(hue=c, count=13, luminosity='bright' )
m_br = rand_color.generate(hue=m, count=13) #, luminosity='bright' )
a_drk = rand_color.generate(hue=a, count=13, luminosity='dark' )
a_br = rand_color.generate(hue=a, count=13, luminosity='bright' )
b_drk = rand_color.generate(hue=b, count=13, luminosity='dark' )
a_lgh = rand_color.generate(hue=a, count=13, luminosity='light' )
b_lgh = rand_color.generate(hue=b, count=13, luminosity='light' )
b_br = rand_color.generate(hue=b, count=13, luminosity='bright')

colors = []

for i in range(13) :
    c_i = a_drk[i] +','+ b_drk[i] +','+ c_br[i] +','+ m_br[i] +','+ a_lgh[i] +','+ b_lgh[i] +','+ a_br[i] +','+ b_br[i]
    colors = colors+c_i.split(',')

#colors = a_drk + b_drk + a_br + b_br + a_lgh + b_lgh
#random.shuffle(colors)

print colors

with open('colors.txt','w') as col :
    col.write(','.join(colors))
col.closed
