#https://github.com/davidmerfield/randomColor
#https://github.com/kevinwuhoo/randomcolor-py
import randomcolor, io, random, sys, math

args = sys.argv

n_colors = int(args[1])
options = len(args)
print "options num %d"%options
colors = []

rand_color = randomcolor.RandomColor()

if options > 2 :
    n_opt = math.ceil(float(n_colors)/(float(options)-2.0)/3.0)
    for i in range(2,options) :
        col = args[i]
        n_opt = int(n_opt)
        colors += rand_color.generate(hue=col, count=n_opt, luminosity='bright') + \
            rand_color.generate(hue=col, count=n_opt, luminosity='dark') + \
            rand_color.generate(hue=col, count=n_opt, luminosity='light')
 
    random.shuffle(colors)
else :
    colors = rand_color.generate(count=n_colors)

print colors
print len(colors)
with open('colors.txt','w') as col :
    col.write(','.join(colors))
col.closed
