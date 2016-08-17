#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:       v.triangle
# AUTHOR(S):    Alexander Muriy
#               (Institute of Environmental Geoscience, Moscow, Russia)  
#               e-mail: amuriy AT gmail DOT com 
#
# PURPOSE:      Front-end for <Triangle> utility
#               (http://www.cs.cmu.edu/~quake/triangle.html) 
#               of J.R. Shewchuk.
#
#               Makes exact Delaunay triangulations, constrained Delaunay triangulations, 
#               conforming Delaunay triangulations and high-quality triangular meshes. 
#               In GIS terminology, it produces 2D TIN, optionally with "breaklines".
#
# COPYRIGHT:    (C) 2012,2016 Alexander Muriy / GRASS Development Team
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
#%  description: Front-end for <Triangle> utility of J.R. Shewchuk. Make exact Delaunay triangulations, constrained Delaunay triangulations, conforming Delaunay triangulations and high-quality triangular meshes. In GIS terminology, it produces 2D TIN, optionally with "breaklines".
#%  keywords: vector, geometry, triangulation
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
#%Option
#%  key: steiner_points
#%  type: integer
#%  required: no
#%  multiple: no
#%  key_desc: name
#%  description: Specifies the maximum number of Steiner points that may be inserted into the mesh (use with "-s" flag)
#%End
#%Option
#%  key: save
#%  type: string
#%  required: no
#%  multiple: no
#%  key_desc: name
#%  description: Path to save <Triangle> working files (*.node,*.poly,*.edge,*.ele). By default uses current location directory
#%End
#%Flag
#%  key: c
#%  description: Conforming constrained Delaunay triangulation without angle or area constraints
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
#%Flag
#%  key: l
#%  description: Uses only vertical cuts in the divide-and-conquer algorithm
#%End
#%Flag
#%  key: y
#%  description: Prohibits the insertion of Steiner points on the mesh boundary 
#%End
#%Flag
#%  key: s
#%  description: Specifies the maximum number of added Steiner points
#%End
#%Flag
#%  key: i
#%  description: Uses the incremental algorithm for Delaunay triangulation, rather than the divide-and-conquer algorithm
#%End
#%Flag
#%  key: f
#%  description: Uses Steven Fortune's sweepline algorithm for Delaunay triangulation, rather than the divide-and-conquer algorithm
#%End
###########################################################################


import sys
import os
import glob
import atexit
# import pandas as pd
import csv
import itertools

from subprocess import Popen, PIPE

try:
    import grass.script as grass
except:
    try:
        from grass.script import core as grass
    except:
        if not os.environ.has_key("GISBASE"):
            print "You must be in GRASS GIS to run this program."
            sys.exit(1)

# try:
#     import triangle
# except:
#     print "You have to install <triangle> Python module to run this script."
#     sys.exit(1)


grass_version = grass.version().get('version')[0:2]
if grass_version != '7.':
    grass.fatal(_("Sorry, this script works in GRASS 7.* only. For GRASS 6.4.* use shell script <v.triangle>"))


def cleanup():
    nuldev = file(os.devnull, 'w')
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
    steiner_points = options['steiner_points']
    
    global tmp, nuldev, grass_version
    nuldev = None

    # setup temporary files
    tmp = grass.tempfile()

    # check for LatLong location
    if grass.locn_is_latlong() == True:
        grass.fatal("Module works only in locations with cartesian coordinate system")

    # check if input file exists
    if not grass.find_file(in_pts, element = 'vector')['file']:
        grass.fatal(_("<%s> does not exist.") % inmap)

    ############################################################
    ## check for Triangle options
    
        
    ############################################################
    ## prepare vectors to Triangle input

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

    tmp_node = tmp + '_node'
    
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
        for line1, line2, line3 in itertools.izip_longest(f1, f2, f3, fillvalue = ""):
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
                
    # with open(tmp_poly, 'r') as f:
    #     print f.read().strip()

    ## let's triangulate
    t = triangle.get_data(tmp_poly)
    print t
    # tri = triangle.triangulate(t, 'pc')
    
        
if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
    
