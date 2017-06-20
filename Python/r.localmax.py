#!/usr/bin/env python
#
############################################################################
#
# MODULE:       r.localmax
#
# AUTHOR(S):    Alexander Muriy
#               (Institute of Environmental Geoscience, Moscow, Russia)  
#               e-mail: amuriy AT gmail DOT com
#
#               Idea by Jachym Cepicky - Perl version (local_max.pl)
#
# PURPOSE:      Local maxima filter for rasters (optionally saving to points)
#
# COPYRIGHT:    2017, Alexander Muriy / GRASS Development Team
#               
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
############################################################################

#%Module 
#%  description: Local maxima filter for rasters (with optionally saving to points)
#%  keywords: raster, map algebra
#%End
#%Option
#%  key: input
#%  type: string
#%  required: yes
#%  key_desc: name
#%  description: Name of input raster map
#%  gisprompt: old,cell,raster
#%End
#%Option
#%  key: output
#%  type: string
#%  required: yes
#%  key_desc: name
#%  description: Name of output raster map
#%  gisprompt: new,cell,raster
#%End
#%Option
#%  key: points
#%  type: string
#%  required: no
#%  key_desc: name
#%  description: Name of output point map
#%  gisprompt: new,vector,vector
#%End
#%Option
#% key: msize
#% type: integer
#% required: yes
#% description: Matrix size (odd number)
#% answer: 11
#%End
############################################################################

import sys
import os
import atexit

try:
    import grass.script as grass
except:
    try:
        from grass.script import core as grass
    except:
        if not os.environ.has_key("GISBASE"):
            print "You must be in GRASS GIS to run this program."
            sys.exit(1)

def cleanup():
    nuldev = file(os.devnull, 'w')
    grass.run_command('g.remove', type_ = 'rast,vect', pattern = 'R_LOCALMAX*', flags = 'f',
                      quiet = True, stderr = nuldev)

def main():
    inr = options['input']
    outr = options['output']
    outp = options['points']
    msize = options['msize']
    msize = int(msize)
    
    global nuldev
    nuldev = None

    mmax = (msize-1)/2

    mapcalc_str1 = "%s = if(%s == max(" % (outr, inr)
    mapcalc_list = []

    i = 0
    j = 0
    for x in xrange(i, msize):
        for y in xrange(j, msize):
            mapcalc_list.append("%s[%d,%d]" % (inr, -(mmax)+x, -(mmax)+y))
    mapcalc_str2 = ','.join(mapcalc_list)
    mapcalc_str3 = mapcalc_str1 + mapcalc_str2 + ("),%s,null())" % inr)

    grass.mapcalc(mapcalc_str3)
    
    if outp:
        vect1 = 'R_LOCALMAX_vect1'
        grass.run_command('r.to.vect',
                        input_ = outr, output = vect1,
                        type_ = 'point',
                        quiet = True, stderr = nuldev)
        res = grass.raster_info(inr)['nsres']
        vect2 = 'R_LOCALMAX_vect2'
        grass.run_command('v.buffer',
                        input_ = vect1, output = vect2,
                        dist = res*2,
                        quiet = True, stderr = nuldev)
        vect3 = 'R_LOCALMAX_vect3'
        grass.run_command('v.type',
                          input_ = vect2, output = vect3,
                          from_type_ = 'centroid',
                          to_type = 'point',
                          quiet = True, stderr = nuldev)
        vect4 = 'R_LOCALMAX_vect4'
        grass.run_command('v.category',
                          input_ = vect3, opt = 'del', 
                          output = vect4,
                          quiet = True, stderr = nuldev)
        vect5 = 'R_LOCALMAX_vect5'
        grass.run_command('v.category',
                          input_ = vect4, opt = 'add', 
                          output = vect5,
                          quiet = True, stderr = nuldev)
        grass.run_command('v.db.addtable',
                          map_ = vect5, columns = 'dist double',
                          quiet = True, stderr = nuldev)
        vect6 = 'R_LOCALMAX_vect6'
        grass.run_command('v.distance',
                          from_ = vect5, from_type = 'point',
                          to = vect1, to_type = 'point',
                          output = vect6,  upload = 'dist', column = 'dist',
                          quiet = True, stderr = nuldev)
        grass.run_command('v.select',
                          ainput = vect1, binput = vect6,
                          output = outp,
                          quiet = True, stderr = nuldev)

        return 0
        
if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    sys.exit(main())
