#!/usr/bin/env python3
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:       v.triangle
# AUTHOR(S):    Alexander Muriy
#               e-mail: amuriy AT gmail DOT com 
#
# PURPOSE:      Front-end for <Triangle> utility
#               (http://www.cs.cmu.edu/~quake/triangle.html) 
#               of J.R. Shewchuk.
#
#               Makes constrained Delaunay triangulations, 
#               conforming Delaunay triangulations and high-quality triangular meshes.
#               In GIS terminology, it produces TIN, optionally with "hard breaklines"
#               and also with the angle or area constraints. Constrained Delaunay
#               triangulation is made by default.
#
# COPYRIGHT:    (C) 2012,2016,2019,2020 Alexander Muriy / GRASS Development Team
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
#%  description: Front-end for <Triangle> utility of J.R. Shewchuk. Make constrained Delaunay triangulations, conforming Delaunay triangulations and high-quality triangular meshes. In GIS terminology, it produces TIN, optionally with "hard breaklines" and also with the angle or area constraints. Constrained Delaunay triangulation is made by default.
#%  keywords: vector, geometry, TIN, triangulation
#%End
#%Option
#%  key: points
#%  type: string
#%  required: yes
#%  multiple: no
#%  key_desc: name
#%  description: Input vector map containing points
#%  gisprompt: old,vector,vector
#%End
#%Option
#%  key: lines
#%  type: string
#%  required: no
#%  multiple: no
#%  key_desc: name
#%  description: Input vector map containing breaklines 
#%  gisprompt: old,vector,vector
#%End
#%Option
#%  key: tin
#%  type: string
#%  required: yes
#%  multiple: no
#%  key_desc: name
#%  description: Name of output vector map (TIN)
#%  gisprompt: new,vector,vector
#%End
#%Option
#%  key: max_area
#%  type: double
#%  required: no
#%  multiple: no
#%  key_desc: name
#%  description: Maximum triangle area (use with "-a" flag)
#%End
#%Option
#%  key: min_angle
#%  type: double
#%  required: no
#%  multiple: no
#%  key_desc: name
#%  description: Minimum mesh angle (use with "-q" flag)
#%End
#%Flag
#%  key: d 
#%  description: Conforming Delaunay triangulation
#%End
#%Flag
#%  key: q
#%  description: Quality mesh generation (all angles are between 20 and 140 degrees)
#%End
#%Flag
#%  key: a
#%  description: Imposes a maximum triangle area constraint
#%End
###########################################################################

import sys
import os
import glob
import atexit
import csv
import itertools
import subprocess 

try:
    import grass.script as grass
except:
    try:
        from grass.script import core as grass
    except:
        if not os.environ.has_key("GISBASE"):
            print("You must be in GRASS GIS to run this program.")
            sys.exit(1)

from grass.lib.gis    import *
from grass.lib.vector import *
from grass.lib.raster import *
            
if not grass.find_program('triangle'):
    if not grass.find_program('triangle.exe'):
        grass.fatal(_("<Triangle> utility required. Follow instructions on the official page (http://www.cs.cmu.edu/~quake/triangle.html) to install it."))

grass_version = grass.version().get('version')[0:2]
if grass_version != '7.':
    grass.fatal(_("Sorry, this script works in GRASS 7.* only. For GRASS 6.4.* use shell script <v.triangle>"))
    
def cleanup():
    nuldev = open(os.devnull, 'w')
    grass.try_remove(tmp)
    for f in glob.glob(tmp + '*'):
        grass.try_remove(f)
    grass.run_command('g.remove', type_ = 'vect', pat = 'V_TRIANGLE_*', flags = 'f',
                      quiet = True, stderr = nuldev)

def main():
    in_pts = options['points']
    in_lines = options['lines']
    out_tin = options['tin']
    max_area = options['max_area']
    min_angle = options['min_angle']
    
    global tmp, nuldev, grass_version
    nuldev = None

    # setup temporary files
    tmp = grass.tempfile()

    # check for LatLong location
    if grass.locn_is_latlong() == True:
        grass.fatal("Module works only in locations with cartesian coordinate system")
        
    # check if input maps are existed
    if in_pts:
        if not grass.find_file(in_pts, element = 'vector')['file']:
            grass.fatal(_("<%s> does not exist.") % in_pts)
    if in_lines:
        if not grass.find_file(in_lines, element = 'vector')['file']:
            grass.fatal(_("<%s> does not exist.") % in_lines)

    ############################################################
    ## check for Triangle options
    if max_area and not flags['a']:
        grass.fatal(_("\n Use <max_area> option with <\"-a\" flag>"))
    if min_angle and not flags['q']:
        grass.fatal(_("\n Use <min_angle> option with <\"-q\" flag>"))
    # if in_lines:
    if flags['a']:
        if max_area:
            flag_a = "-a%s" % max_area
        else:
            grass.fatal(_("\n To use flag <\"-a\"> choose <max_area> option"))
    else:
        flag_a = ""
    if flags['d']:
        flag_d = "-D"
    else:
        flag_d = ""
    if flags['q']:
        flag_q = "-q -Y"
        if min_angle:
            flag_q = "-q%s" % min_angle
    else:
        flag_q = ""
        
    ############################################################
    ## prepare vectors to Triangle input
    grass.message(_("Prepare vectors to Triangle input..."))
    
    tmp_pts_cut = tmp + '_pts_cut'
    grass.run_command('v.out.ascii', input_ = in_pts, output = tmp_pts_cut,
                      sep = ' ', quiet = True, stderr = nuldev)

    tmp_pts_cut2 = tmp_pts_cut + '2'
    with open(tmp_pts_cut,'r') as fin:
        with open (tmp_pts_cut2,'w') as fout:
            writer = csv.writer(fout, delimiter=' ')            
            for row in csv.reader(fin, delimiter=' '):
                writer.writerow(row[0:3])

    if in_lines:
        grass.run_command('v.split', input_ = in_lines, output = 'V_TRIANGLE_CUT_SEGM',
                          vertices = '2', quiet = True, stderr = nuldev)
        grass.run_command('v.category', input_ = 'V_TRIANGLE_CUT_SEGM', output = 'V_TRIANGLE_CUT_SEGM_NOCATS',
                          option = 'del', quiet = True, stderr = nuldev)
        grass.run_command('v.category', input_ = 'V_TRIANGLE_CUT_SEGM_NOCATS', output = 'V_TRIANGLE_CUT_SEGM_NEWCATS',
                          option = 'add', quiet = True, stderr = nuldev)
        grass.run_command('v.to.points', input_ = 'V_TRIANGLE_CUT_SEGM_NEWCATS', output = 'V_TRIANGLE_CUT_PTS',
                          use = 'vertex', flags = 't', quiet = True, stderr = nuldev)

        tmp_lines_cut = tmp + '_lines_cut'
        grass.run_command('v.out.ascii', input_ = 'V_TRIANGLE_CUT_PTS', output = tmp_lines_cut,
                          format_ = 'point', sep = ' ', quiet = True, stderr = nuldev)

    ## make *.node file
    tmp_pts_cut_0 = tmp_pts_cut + '_0'    
    with open(tmp_pts_cut2,'r') as fin:
        with open (tmp_pts_cut_0,'w') as fout:
            writer = csv.writer(fout, delimiter=' ')            
            for row in csv.reader(fin, delimiter=' '):
                row.append('0')
                writer.writerow(row)

    tmp_cut = tmp + '_cut'
    with open(tmp_cut, 'w') as outfile:
        if in_lines:
            filenames = [tmp_lines_cut, tmp_pts_cut_0]
        else:
            filenames = [tmp_pts_cut_0]

        for fname in filenames:
            with open(fname) as infile:
                for num, line in enumerate(infile, 1):
                    outfile.write('%s ' '%s' % (num, line))

    num_lines = sum(1 for line in open(tmp_cut))
    
    tmp_header = tmp + '_header'
    with open(tmp_header,'w') as fout:
        fout.write("%s 2 1 1" % num_lines)
        fout.write('\n')

    tmp_node = tmp + '.node'    
    filenames = [tmp_header, tmp_cut]
    with open(tmp_node, 'w') as outfile:
        for fname in filenames:
            with open(fname) as infile:
                for line in infile:
                    outfile.write(line)

                    
    ## make *.poly file
    tmp_poly = tmp + '.poly'
    if in_lines:
        with open(tmp_poly, 'w') as fout:
            fout.write('0 2 1 1')
            fout.write('\n')
    
        vert_num = sum(1 for line in open(tmp_lines_cut))
        segm_num = (vert_num / 2)

        with open(tmp_poly, 'a') as fout:
            fout.write('%s 1' % segm_num)
            fout.write('\n')
            
        tmp_num = tmp + '_num'
        with open(tmp_num, 'w') as outfile:
            with open(tmp_lines_cut) as infile:
                for num, line in enumerate(infile, 1):
                    outfile.write('%s ' '%s' % (num, line))
                    
        tmp_num1 = tmp + '_num1'
        tmp_num2 = tmp + '_num2'
        tmp_num3 = tmp + '_num3'
        tmp_num4 = tmp + '_num4'
        tmp_num5 = tmp + '_num5'
        
        with open(tmp_num1, 'w') as outfile1:
            with open(tmp_num2, 'w') as outfile2:
                with open(tmp_num) as infile:
                    reader = csv.reader(infile, delimiter=' ')
                    for row in reader:
                        content = list(row[i] for i in [0])
                        content = [int(i) for i in content]
                        content2 = str(content).replace('[','').replace(']','')
                        if int(content2) % 2:
                            outfile1.write('%s' % content2)
                            outfile1.write('\n')
                        else:
                            outfile2.write('%s' % content2)
                            outfile2.write('\n')
        numlist = []
        with open(tmp_num) as infile:
            reader = csv.reader(infile, delimiter=' ')
            for row in reader:
                content = list(row[i] for i in [4])
                content = [int(i) for i in content]
                numlist.append(content)

        numlist2 = [item for sublist in numlist for item in sublist]
        numlist3 = list(set(numlist2))

        with open(tmp_num3, 'w') as outfile:
            for item in numlist3:
                outfile.write("%s\n" % item)

        with open(tmp_num4, 'w') as outfile, open(tmp_num1) as f1, open(tmp_num2) as f2, open(tmp_num3) as f3:
            for line1, line2, line3 in itertools.zip_longest(f1, f2, f3, fillvalue = ""):
                outfile.write("{} {} {}\n".format(line1.rstrip(), line2.rstrip(), line3.rstrip()))

        with open(tmp_num5, 'w') as outfile:
            with open(tmp_num4) as infile:
                for num, line in enumerate(infile, 1):
                    outfile.write('%s ' '%s' % (num, line))

        with open(tmp_poly, 'a') as outfile:
            with open(tmp_num5) as infile:
                for line in infile:
                    outfile.write(line)
            outfile.write('0')

            
    ## let's triangulate
    grass.message(_("Triangulate..."))
    if in_lines:
        subprocess.call(['triangle', '-Q', '-c', '-p', flag_a, flag_d, flag_q, tmp_poly], shell = False)
    else:
        subprocess.call(['triangle', '-Q', '-c', flag_a, flag_d, flag_q, tmp_node], shell = False)

    ## back from Triangle to GRASS
    grass.message(_("Back from Triangle to GRASS..."))
    out_node = tmp + '.1.node'
    out_node = out_node.replace('0.','')

    out_ele = tmp + '.1.ele'
    out_ele = out_ele.replace('0.','')

    out_node2 = out_node + '2'
    out_node3 = out_node + '3'
    out_node4 = out_node + '4'
    out_ele2 = out_ele + '2'
    out_ele3 = out_ele + '3'
    
    with open(out_node, 'r') as f:
        data = f.read().splitlines(True)
        with open(out_node2, 'w') as fout:
            fout.writelines(data[1:])

    with open(out_node2, 'r') as f:
        data = f.read().splitlines(True)
        with open(out_node3, 'w') as fout:
            fout.writelines(data[:-1])

    with open(out_node4, 'w') as fout:
        with open(out_node3) as fin:
            for line in fin:
                line2 = " ".join(line.split())
                fout.write(line2 + '\n')

    with open(out_ele, 'r') as f:
        data = f.read().splitlines(True)
        with open(out_ele2, 'w') as fout:
            fout.writelines(data[1:])

    with open(out_ele2, 'r') as f:
        data = f.read().splitlines(True)
        with open(out_ele3, 'w') as fout:
            fout.writelines(data[:-1])        

    out_ele4 = out_ele + '4'
    with open(out_ele4, 'w') as fout:
        with open(out_ele3) as fin:
            for line in fin:
                line2 = " ".join(line.split())
                fout.write(line2 + '\n')
    
    out_ele5 = out_ele + '5'
    with open(out_ele4,'r') as fin:
        with open (out_ele5,'w') as fout:
            writer = csv.writer(fout, delimiter='\n')
            for row in csv.reader(fin, delimiter=' '):
                row2 = row[1:4]
                ap = ''.join(row[1:2])
                row2.append(ap)
                writer.writerow(row2)

    out_ele6 = out_ele + '6'
    with open(out_ele5, 'r') as f1, open(out_node4, 'r') as f2, open(out_ele6, 'w') as fout:
        list1 = f1.read().splitlines()
        list2 = f2.read().splitlines()
        for line1 in list1:
            for line2 in list2:                
                if line2.startswith(str(line1)):
                    fout.write(line2 + '\n')
                    break

    out_ele7 = out_ele + '7'
    with open(out_ele6,'r') as fin:
        with open (out_ele7,'w') as fout:
            writer = csv.writer(fout, delimiter=' ')
            for row in csv.reader(fin, delimiter=' '):
                row = row[1:4]
                writer.writerow(row)

    out_ele8 = out_ele + '8'
    with open(out_ele8, 'w') as fout, open(out_ele7, 'r') as fin:
        fout.write('B 4\n')
        for line in fin:
            fout.write(line)

    out_ele9 = out_ele + '9'
    with open(out_ele9, 'w') as fout:
        with open(out_ele8, 'r') as fin:
            for lineno, line in enumerate(fin):
                if lineno % 4 == 0:
                    fout.write(line.rstrip() + '\nB 4\n')
                else:
                    fout.write(line.rstrip() + '\n')

    out_ele10 = out_ele + '10'
    with open(out_ele10, 'w') as fout, open(out_ele9, 'r') as fin:
        lines = fin.readlines()
        lines = lines[:-1]    
        lines = lines[1:]
        for line in lines:
            fout.write(line)

            
    ## import "raw" TIN into GRASS
    grass.run_command('v.in.ascii', flags = 'zn', input_ = out_ele10, output = 'V_TRIANGLE_TIN_RAW',
                      format_ = 'standard', sep = ' ', quiet = True, stderr = nuldev)

    ## cleanup and make areas
    grass.run_command('v.clean', input_ = 'V_TRIANGLE_TIN_RAW', output = 'V_TRIANGLE_TIN_CLEAN',
                      tool = ('bpol','rmdupl'), quiet = True, stderr = nuldev)
    grass.run_command('v.centroids', input_ = 'V_TRIANGLE_TIN_CLEAN', output = out_tin,
                      quiet = True, stderr = nuldev)

    ## compute 3D centroids of areas
    grass.message(_("Compute 3D centroids of areas..."))
    ## initialize GRASS Ctypes library
    G_gisinit('')    
    # define map structure 
    map_info = pointer(Map_info())    
    # set vector topology to level 2 
    Vect_set_open_level(2)
    
    # check if vector map exists
    mapset = G_find_vector2(out_tin, "")
    if not mapset:
        grass.fatal("Vector map <%s> not found" % out_tin)
        
    # open the vector map
    Vect_open_old(map_info, out_tin, mapset)
    Vect_maptype_info(map_info, out_tin, mapset)
    
    # output ascii
    asc = grass.read_command("v.out.ascii", input_ = out_tin,
                             format_ = "standard", type_ = 'centroid')
    result = asc.split("\n")
    
    out_xyz = tmp + '.xyz'
    with open(out_xyz, 'w') as fout:
        for line in result:            
            if re.findall(r'^.[0-9]+\.',line):                
                line2 = ' '.join(line.split())
                x = line2.split(' ')[0]
                y = line2.split(' ')[1]
                dx = c_double(float(x))
                dy = c_double(float(y))
                z = c_double()
                
                Vect_tin_get_z(map_info, dx, dy, byref (z), None, None)
                fout.write(str(dx.value) + ',' + str(dy.value) + ',' + str(z.value) + '\n')
                
    Vect_close(map_info)
    
    grass.run_command('v.in.ascii', flags = 'zn', input_ = out_xyz, output = 'V_TRIANGLE_TIN_CENT',
                      format_ = 'point', sep = ',', z = 3, quiet = True, stderr = nuldev)
    grass.run_command('v.type', input_ = 'V_TRIANGLE_TIN_CENT', output = 'V_TRIANGLE_TIN_CENT2',
                      from_type = 'point', to_type = 'centroid', quiet = True, stderr = nuldev)
    grass.run_command('v.edit', map_ = out_tin, tool = 'delete', type_ = 'centroid', 
                      ids = '0-99999999', quiet = True, stderr = nuldev)
    grass.run_command('v.edit', map_ = out_tin, bgmap = 'V_TRIANGLE_TIN_CENT2', tool = 'copy', 
                      type_ = 'centroid', ids = '0-99999999', quiet = True, stderr = nuldev)

    return 0
            

    
            
if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
    
