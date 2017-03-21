import randomcolor, io, random


rand_color = randomcolor.RandomColor(100)

orange =rand_color.generate(hue='orange', count=17, luminosity='bright' )
blue =rand_color.generate(hue='blue', count=17, luminosity='bright' )
blue_br =rand_color.generate(hue='blue', count=17, luminosity='bright' )
orange_br =rand_color.generate(hue='orange', count=17, luminosity='bright' )
orange_drk =rand_color.generate(hue='orange', count=17, luminosity='dark' )
blue_drk =rand_color.generate(hue='blue', count=17, luminosity='dark' )
blue_lgh =rand_color.generate(hue='blue', count=16, luminosity='light' )
orange_lgh =rand_color.generate(hue='orange', count=16, luminosity='light' )

colors = blue_drk + orange_drk + blue_br + orange_br + blue_lgh + orange_lgh
random.shuffle(colors)

with open('colors.txt','w') as col :
    col.write(','.join(colors))
col.closed
