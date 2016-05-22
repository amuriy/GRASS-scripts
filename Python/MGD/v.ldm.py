#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:       v.ldm
# AUTHOR(S):    Alexander Muriy
#               (Institute of Environmental Geoscience, Moscow, Russia)  
#               e-mail: amuriy AT gmail DOT com 
#
# PURPOSE:      Computes "Linear Directional Mean" of vector lines, optionally displays arrow 
#               on the graphic monitor, saves to vector line and update attribute table
#               with the LDM statistics.
#
# COPYRIGHT:    (C) 2011,2013,2016 Alexander Muriy / GRASS Development Team
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
#%  description: Compute "Linear Directional Mean" of vector lines, displays arrow on the graphic monitor, save to vector line and update attribute table with LDM parameters. 
#%  keywords: vector, statistics, graphics
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
#%  key: type
#%  type: string
#%  required: no
#%  multiple: no
#%  options: orient,direct
#%  description: Type of LDM graphics
#% descriptions: orient; orientation only; direct; orientation and direction
#%  answer: orient
#%End
#%Option
#%  key: ldm
#%  type: string
#%  required: no
#%  key_desc: name
#%  description: Name of output LDM vector map
#%  gisprompt: new,vector,vector
#%End
#%Option
#%  key: width
#%  type: integer
#%  required: no
#%  description: Width of LDM line with arrow
#%  answer: 5
#%End
#%Option
#%  key: color
#%  type: string
#%  required: no
#%  description: Color for LDM line with arrow (standard color name or R:G:B)
#%  answer: black
#%  gisprompt: old_color,color,color
#%End
#%Option G_OPT_F_OUTPUT
#%  key: graph
#%  required: no
#%  description: Output file to save LDM graphics
#%End
#%Flag
#%  key: x
#%  description: Show LDM graphics on the screen
#%End
#%Flag
#%  key: g
#%  description: Print in shell script style
#%End
############################################################################

import sys
import os
import glob
import string
import shutil
import atexit
import math
import subprocess

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
    grass.run_command('g.remove', type_ = 'vect', pat = 'v_ldm_vect*', flags = 'f',
                      quiet = True, stderr = nuldev)
    
def decimal2dms(dec_deg):
    deg = int(dec_deg)
    dec_min = abs(dec_deg - deg) * 60
    min = int(dec_min)
    sec = (dec_min - min) * 60
    dms = str(deg) + ':' + str(min) + ':' + str(sec)
    return dms


# check for v.mc module
def check_progs():
    found_missing = False
    if not grass.find_program('v.mc.py'):
        found_missing = True
        grass.warning(_("'%s' required. Please install '%s' first \n using 'g.extension %s' or check \n PATH and GRASS_ADDON_PATH variables") % ('v.mc.py','v.mc.py','v.mc.py'))
        if found_missing:
            grass.fatal(_("An ERROR occurred running <v.ldm.py>"))


def main():
    check_progs()
    
    inmap = options['input']
    output = options['ldm']
    width = options['width']
    color = options['color']
    graph = options['graph']
    ldm_type = options['type']

    mapset = grass.gisenv()['MAPSET']

    global tmp, nuldev, grass_version
    nuldev = None

    grass_version = grass.version()['version'][0]
    if grass_version != '7':
        grass.fatal(_("Sorry, this script works in GRASS 7.* only"))

    # setup temporary files
    tmp = grass.tempfile()
    
    # check for LatLong location
    if grass.locn_is_latlong() == True:
        grass.fatal("Module works only in locations with cartesian coordinate system")


    # check if input file exists
    if not grass.find_file(inmap, element = 'vector')['file']:
        grass.fatal(_("<%s> does not exist.") % inmap)
        
    # check for lines
    iflines = grass.vector_info_topo(inmap)['lines']
    if iflines == 0:
        grass.fatal(_("Map <%s> has no lines.") % inmap)
    

    # diplay options 
    if flags['x']:
        env = grass.gisenv()
        mon = env.get('MONITOR', None)
        if not mon:
            if not graph:
                grass.fatal(_("Please choose \"graph\" output file with LDM graphics or not use flag \"x\""))

    
    ####### DO IT #######
    # copy input vector map and drop table
    grass.run_command('g.copy', vect = (inmap, 'v_ldm_vect'), quiet = True, stderr = nuldev)
    db = grass.vector_db('v_ldm_vect')
    if db != {}:
        grass.run_command('v.db.droptable', map_ = 'v_ldm_vect', flags = 'f', quiet = True, stderr = nuldev)

    # compute mean center of lines with v.mc.py module
    center_coords = grass.read_command('v.mc.py', input_ = inmap, type_ = 'line',
                                quiet = True, stderr = nuldev).strip()
    mc_x = center_coords.split(' ')[0]
    mc_y = center_coords.split(' ')[1]

    center_coords = str(mc_x) + ',' + str(mc_y)

    ### 
    inmap = 'v_ldm_vect'

    # count lines
    count = grass.vector_info_topo(inmap)['lines']

    # add temp table with azimuths and lengths of lines
    in_cats = inmap + '_cats'    
    grass.run_command('v.category', input_ = inmap, option = 'add', 
                      output = in_cats, quiet = True, stderr = nuldev)
    grass.run_command('v.db.addtable', map_ = in_cats, table = 'tmp_tab', 
                      columns = 'sum_azim double, len double', quiet = True, stderr = nuldev)
    grass.run_command('v.db.connect', map_ = in_cats, table = 'tmp_tab', 
                      flags = 'o', quiet = True, stderr = nuldev)
    grass.run_command('v.to.db', map_ = in_cats, opt = 'azimuth', 
                      columns = 'sum_azim', units = 'radians', quiet = True, stderr = nuldev)
    grass.run_command('v.to.db', map_ = in_cats, opt = 'length',  
                      columns = 'len', units = 'meters', quiet = True, stderr = nuldev)    

    # find end azimuth
    p = grass.pipe_command('v.db.select', map_ = in_cats, columns = 'sum_azim', flags = 'c', quiet = True, stderr = nuldev)
    c = p.communicate()[0].strip().split('\n')

    sin = []
    cos = []
    
    for i in c:
        s1 = math.sin(float(i))
        c1 = math.cos(float(i))
        sin.append(s1)
        cos.append(c1)

    ca_sin = sum(map(float,sin))
    ca_cos = sum(map(float,cos))
    
    atan = math.atan2(ca_sin,ca_cos)
    end_azim = math.degrees(atan)

    # find compass angle    
    if end_azim < 0:
        a2 = -(end_azim)
    if end_azim > 0:
        a2 = end_azim
    if (ca_sin > 0) and (ca_cos > 0):
        comp_angle = a2
    if (ca_sin > 0) and (ca_cos < 0):
        comp_angle = a2
    if (ca_sin < 0) and (ca_cos > 0):
        comp_angle = 360 - a2
    if (ca_sin < 0) and (ca_cos < 0):
        comp_angle = 360 - a2

    # find LDM
    if end_azim < 0:
        a2 = -(end_azim)
    if end_azim > 0:
        a2 = end_azim
    if (ca_sin > 0) and (ca_cos > 0):
        ldm = 90 - a2
    if (ca_sin > 0) and (ca_cos < 0):
        ldm = 450 - a2
    if (ca_sin < 0) and (ca_cos > 0):
        ldm = 90 + a2
    if (ca_sin < 0) and (ca_cos < 0):
        ldm = 90 + a2

    # find circular variance
    sin_pow = math.pow(ca_sin,2) 
    cos_pow = math.pow(ca_cos,2) 

    circ_var = 1-(math.sqrt(sin_pow+cos_pow))/count

    # find start/end points of "mean" line
    end_azim_dms = decimal2dms(end_azim)

    # if end_azim < 0:
    #     end_azim_dms = '-' + (str(end_azim_dms))

    start_azim = 180 - end_azim
    start_azim_dms = decimal2dms(start_azim)
    
    p = grass.pipe_command('v.db.select', map_ = in_cats, columns = 'len',
                           flags = 'c', quiet = True, stderr = nuldev)
    c = p.communicate()[0].strip().split('\n')

    mean_length = sum(map(float,c))/len(c)
    half_length = float(mean_length)/2

    tmp1 = tmp + '.inf'
    inf1 = file(tmp1, 'w')
    print >> inf1, 'N ' + str(end_azim_dms) + ' E ' + str(half_length)
    inf1.close()
    
    end_coords = grass.read_command('m.cogo', input_ = tmp1, output = '-',
                                    coord = center_coords, quiet = True).strip()

    tmp2 = tmp + '.inf2'
    inf2 = file(tmp2, 'w')
    print >> inf2, 'N ' + str(start_azim_dms) + ' W ' + str(half_length)
    inf2.close()

    start_coords = grass.read_command('m.cogo', input_ = tmp2, output = '-',
                                      coord = center_coords, quiet = True).strip()

    # make "arrowhead" symbol
    if flags['x'] or graph:
        tmp3 = tmp + '.arrowhead_1'
        outf3 = file(tmp3, 'w')

        if ldm_type == 'direct':
            t1 = """VERSION 1.0
BOX -0.5 -0.5 0.5 0.5
POLYGON
  RING
  FCOLOR NONE
    LINE
      0 0
      0.3 -1
    END
  END
POLYGON
  RING
  FCOLOR NONE
    LINE
      0 0
      -0.3 -1
    END
  END
END
"""
            outf3.write(t1)
            outf3.close()
    
            gisdbase = grass.gisenv()['GISDBASE']
            location = grass.gisenv()['LOCATION_NAME']
            mapset = grass.gisenv()['MAPSET']
            symbols_dir = os.path.join(gisdbase, location, mapset, 'symbol', 'arrows')
            symbol = os.path.join(symbols_dir, 'arrowhead_1')
    
            if not os.path.exists(symbols_dir):
                try:
                    os.makedirs(symbols_dir)
                except OSError:
                    pass
        
            if not os.path.isfile(symbol):
                shutil.copyfile(tmp3, symbol)
        
    
        # write LDM graph file and optionally display line of LDM with an arrow
    tmp4 = tmp + '.ldm'
    outf4 = file(tmp4, 'w')
    
    arrow_size = int(width) * 1.4
    arrow_azim = 360 - float(end_azim)

    if ldm_type == 'direct':
        t2 = string.Template("""
move $start_coords
width $width
color $color
draw $end_coords

rotation $arrow_azim
width $width
symbol $symbol_s $arrow_size $end_coords $color
""")    
        s2 = t2.substitute(start_coords = start_coords, width = width, color = color,
                       end_coords = end_coords, arrow_azim = arrow_azim,
                       symbol_s = "arrows/arrowhead_1", arrow_size = arrow_size)
    else:
        t2 = string.Template("""
move $start_coords
width $width
color $color
draw $end_coords
""")    
        s2 = t2.substitute(start_coords = start_coords, width = width, color = color,
                       end_coords = end_coords)

    outf4.write(s2)
    outf4.close()

    if graph:
        shutil.copy(tmp4, graph)



    # save LDM line to vector if option "output" set  
    if output:
        tmp5 = tmp + '.line'
        outf5 = file(tmp5, 'w')

        print >> outf5, str(start_coords)
        print >> outf5, str(end_coords)

        outf5.close()

        grass.run_command('v.in.lines', input_ = tmp5, output = output,
                              separator = " ", overwrite = True, quiet = True)

        out_cats = output + '_cats'
        grass.run_command('v.category', input_ = output, option = 'add', 
                          output = out_cats, quiet = True, stderr = nuldev)
        grass.run_command('g.rename', vect = (out_cats,output), 
                          overwrite = True, quiet = True, stderr = nuldev)
        
        if circ_var:
            col = 'comp_angle double,dir_mean double,cir_var double,ave_x double,ave_y double,ave_len double'
        else:
            col = 'comp_angle double,dir_mean double,ave_x double,ave_y double,ave_len double'
                        
        grass.run_command('v.db.addtable', map_ = output, columns = col, quiet = True, stderr = nuldev)

        tmp6 = tmp + '.sql'
        outf6 = file(tmp6, 'w')
                
        t3 = string.Template("""
UPDATE $output SET comp_angle = $comp_angle;
UPDATE $output SET dir_mean = $ldm;
UPDATE $output SET ave_x = $mc_x;
UPDATE $output SET ave_y = $mc_y;
UPDATE $output SET ave_len = $mean_length;
""")
        s3 = t3.substitute(output = output, comp_angle = ("%0.3f" % comp_angle),
                           ldm = ("%0.3f" % ldm), mc_x = ("%0.3f" % float(mc_x)),
                           mc_y = ("%0.3f" % float(mc_y)), mean_length = ("%0.3f" % mean_length))
        outf6.write(s3)

        if circ_var:
            print >> outf6, "UPDATE %s SET cir_var = %0.3f;" % (output, circ_var)

        outf6.close()

        grass.run_command('db.execute', input_ = tmp6, quiet = True, stderr = nuldev)


    # print LDM parameters to stdout (with <-g> flag in shell style):
    print_out = ['Compass Angle', 'Directional Mean', 'Average Center', 'Average Length']
    if circ_var:
        print_out.append('Circular Variance')
        
    print_shell = ['compass_angle', 'directional_mean', 'average_center',
                   'average_length', 'circular_variance']
    if circ_var:
        print_shell.append('circular_variance')
        
    print_vars = ["%0.3f" % comp_angle, "%0.3f" % ldm,
                  "%0.3f" % float(mc_x) + ',' + "%0.3f" % float(mc_y),
                  "%0.3f" % mean_length]
    if circ_var:
        print_vars.append("%0.3f" % circ_var)


    if flags['g']:
        for i,j in zip(print_shell, print_vars):
            print "%s=%s" % (i, j)
    else:
        for i,j in zip(print_out, print_vars):
            print "%s: %s" % (i, j)


    # diplay LDM graphics
    if flags['x']:
        if mon:
            if graph:
                grass.run_command('d.graph', input_ = graph, flags = 'm', quiet = True, stderr = nuldev)
            else:
                grass.run_command('d.graph', input_ = tmp4, flags = 'm', quiet = True, stderr = nuldev)
        elif graph:
            grass.message(_("\n Use this command in wxGUI \"Command console\" or with <d.mon> or with \"command layer\" to display LDM graphics: \n d.graph -m input=%s \n\n" ) % graph)

            
if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
