#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:       v.mc
# AUTHOR(S):    Alexander Muriy
#               (Institute of Environmental Geoscience, Moscow, Russia)  
#               e-mail: amuriy AT gmail DOT com 
#
# PURPOSE:      Compute "Mean Center" - the geographic center (or the center of concentration) for a set of vector features.
#
# TODO: 
# - Calculate also the mean center for a 3rd dimension if vector map is 3D
# - Work with fields
#
# COPYRIGHT:    (C) 2013,2016 Alexander Muriy / GRASS Development Team
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
#%  description: Compute "Mean Center" - the geographic center (or the center of concentration) for a set of vector features.
#%  keywords: display, graphics, vector, symbology
#%End
#%Option
#%  key: input
#%  type: string
#%  required: yes
#%  multiple: no
#%  key_desc: name
#%  description: Name of input vector map
#%  gisprompt: old,vector,vector
#%End
#%Option
#%  key: output
#%  type: string
#%  required: no
#%  multiple: no
#%  key_desc: name
#%  description: Name of output vector map
#%  gisprompt: new,vector,vector
#%End
#%Option
#%  key: type
#%  type: string
#%  multiple: yes
#%  options: point,line,boundary,centroid,area,auto
#%  answer: auto
#%  required: no
#%  description: Geometry type (default is auto)
#%End
############################################################################

import sys
import os
import glob
import atexit

from osgeo import ogr
from shapely.wkt import loads
from shapely import geometry

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
    inmap = options['input']
    nuldev = file(os.devnull, 'w')
    grass.try_remove(tmp)
    for f in glob.glob(tmp + '*'):
        grass.try_remove(f)
    grass.run_command('g.remove', type_ = 'vect', pat = 'v_mc*', flags = 'f',
                      quiet = True, stderr = nuldev)

def main():
    inmap = options['input']
    outmap = options['output']
    gtype = options['type']

    global tmp, nuldev, grass_version
    nuldev = None

    # setup temporary files
    tmp = grass.tempfile()

    # check for LatLong location
    if grass.locn_is_latlong() == True:
        grass.fatal("Module works only in locations with cartesian coordinate system")

    # check if input file exists
    if not grass.find_file(inmap, element = 'vector')['file']:
        grass.fatal(_("<%s> does not exist.") % inmap)
        

    ## export geometry to CSV
    tmp1 = tmp + '.csv'
    if gtype:
        grass.run_command('v.out.ogr', input_ = inmap, output = tmp1, 
                      format_ = "CSV", type_ = '%s' % gtype, 
                          lco = "GEOMETRY=AS_WKT", quiet = True, stderr = nuldev)
    else:
        grass.run_command('v.out.ogr', input_ = inmap, output = tmp1, 
                      format_ = "CSV", type_ = ('point','centroid','line','boundary','area'), 
                      lco = "GEOMETRY=AS_WKT", quiet = True, stderr = nuldev)
    
    # open CSV with OGR
    input = ogr.Open(tmp1, 0)
    lyr = input.GetLayer(0)

    xlist = []
    ylist = []

    # export geometries as WKT
    for f in lyr:
        geom = f.GetGeometryRef()
        load = loads(geom.ExportToWkt())
        # compute centroid for each feature
        cent = str(load.centroid.wkt).replace('POINT ','').replace('(','').replace(')','')
        x = cent.split(' ')[0]
        y = cent.split(' ')[1]
        xlist.append(float(x))
        ylist.append(float(y))
        
    xy_list = zip(xlist,ylist)

    # compute centroid for centroids    
    mpoint = geometry.MultiPoint(xy_list)
    mcent = str(mpoint.centroid.wkt.replace('POINT ','').replace('(','').replace(')',''))


    # output
    if not outmap:
        print mcent
    else:
        out = tmp + '.out'
        outf = file(out, 'w')
        print >> outf, mcent
        outf.close()
        
        grass.run_command('v.in.ascii', input_ = out, output = outmap,
                          sep = ' ', quiet = True, stderr = nuldev)


if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
        
