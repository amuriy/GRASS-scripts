#!/usr/bin/env python

############################################################################
#
# MODULE:       i.landsat.trim
# AUTHOR(S):    Alexander Muriy
#               (Institute of Environmental Geoscience, Moscow, Russia)  
#               e-mail: amuriy AT gmail DOT com 
# VERSION: 0.2
#
#               Some code from page http://grass.osgeo.org/wiki/LANDSAT
#
# PURPOSE:      Trims the "fringe" from the borders of Landsat images, for each band
#               separately or with the MASK where coverage exists for all bands. 
#               Optionally saves vector footprints of trimmed rasters and MASK. 
#               Works with Landsat 5, Landsat 7 (SLC-on). 
#
# COPYRIGHT:    (C) 2012 Alexander Muriy / GRASS Development Team
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
#% description: Trims the "fringe" from the borders of Landsat images, for each band separately or with the MASK where coverage exists for all bands. Optionally saves vector footprints of trimmed rasters and MASK. Works with Landsat 5, Landsat 7 (SLC-on).
#% keywords: imagery, landsat, raster, vector
#%End
#%Option
#% key: input
#% type: string
#% required: no
#% multiple: no
#% label: Name of input raster band(s)
#% description: Example: L5170028_02820070521_B10
#% gisprompt: old,cell,raster
#%End
#%Option
#% key: input_base
#% type: string
#% required: no
#% multiple: no
#% label: Base name of input raster bands
#% description: Example: L5170028_02820070521
#%End
#%Option
#% key: input_prefix
#% type: string
#% required: no
#% multiple: no
#% label: Prefix name of input raster bands
#% description: Example: 'B.' for B.1, B.2, ...
#%End
#%Option
#% key: output_prefix
#% type: string
#% required: yes
#% multiple: no
#% label: Prefix for output raster maps 
#% description: Example: 'trim' generates B.1.trim, B.2.trim, ...
#%End
#%Option
#% key: rast_buffer
#% type: integer
#% required: no
#% multiple: no
#% description: Distance for raster buffering (in meters)
#% answer: 300
#%End
#%Option
#% key: gener_thresh
#% type: integer
#% required: no
#% multiple: no
#% description: Threshold for generalizing of vector footprints or coverage MASK (in meters)
#% answer: 3000
#%End
#%Flag
#% key: m
#% description: Trim raster(s) with the MASK where coverage exists for all bands   
#%End
#%Flag
#% key: g
#% description: Trim raster(s) with the generalized footprint from all bands   
#%End
#%Flag
#% key: a
#% description: Process all bands 
#%End
#%Flag
#% key: f
#% description: Save vector footprint(s) of trimmed raster bands or coverage MASK 
#%End


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
    # for rast in tmp_rast:
    grass.run_command('g.region', region = 'I_LANDSAT_TRIM' + '_old_region', quiet = True)

    if grass.find_file('I_LANDSAT_TRIM', element = 'region')['file']:
        grass.run_command('g.remove', rast = MASK, flags = 'f', quiet = True)
        
    grass.run_command('g.mremove',
                      rast = '*' + 'I_LANDSAT_TRIM' + '*',
                      flags = 'f',
                      quiet = True)
    grass.run_command('g.mremove',
                      vect = '*' + 'I_LANDSAT_TRIM' + '*',
                      flags = 'f',
                      quiet = True)
    grass.run_command('g.remove',
                      region = 'I_LANDSAT_TRIM' + '_old_region',
                      flags = 'f',
                      quiet = True)
    

def band_mask():
    tmp = 'I_LANDSAT_TRIM'
    buf = options['rast_buffer']
    thresh = int(buf) / 3
    print thresh
    

    
def main():
    tmp = 'I_LANDSAT_TRIM'
    buf = options['rast_buffer']
    thresh = int(buf) / 3
    print thresh
    



    # tmp = 'I_LANDSAT_TRIM'
    # buf = options['rast_buffer']
    # thresh = int(buf) / 3
    # print thresh
 
if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    sys.exit(main())


            




