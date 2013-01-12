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
#               Jachym Cepicky (jachym.cepicky AT centrum.cz) - original Perl version
#
# PURPOSE:      Local maxima filter for rasters
#
# COPYRIGHT:    2012 Alexander Muriy / GRASS Development Team
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
#%  description: Local maxima filter for rasters 
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
#% key: size
#% type: integer
#% required: no
#% multiple: no
#% description: Matrix size
#% answer: 3
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







if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    sys.exit(main())        
