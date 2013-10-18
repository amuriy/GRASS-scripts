#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:       v.mc
# AUTHOR(S):    Alexander Muriy
#               (Institute of Environmental Geoscience, Moscow, Russia)  
#               e-mail: amuriy AT gmail DOT com 
#
# PURPOSE:      Compute "Mean Center" — the geographic center (or the center of concentration) for a set of vector features.
#
# For line and polygon features, feature centroids are used in distance computations. For multipoints, polylines, or polygons with multiple parts, the centroid is computed using the weighted mean center of all feature parts. The weighting for point features is 1, for line features is length, and for polygon features is area.
#
# VERSION: 0.1
#
# COPYRIGHT:    (C) 2013 Alexander Muriy / GRASS Development Team
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
#%  description: Compute "Mean Center" — the geographic center (or the center of concentration) for a set of vector features.
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
#%  required: yes
#%  multiple: no
#%  key_desc: name
#%  description: Name of output vector map
#%  gisprompt: new,vector,vector
#%End
#%Option
#%  key: weight_field
#%  type: string
#%  required: no
#%  multiple: no
#%  description: The numeric field used to create a weighted mean center
#%End
#%Option
#%  key: case_field
#%  type: string
#%  required: no
#%  multiple: no
#%  description: Field used to group features for separate mean center computations
#%End
#%Option
#%  key: dimension_field
#%  type: string
#%  required: no
#%  multiple: no
#%  description: A numeric field containing attribute values from which an average value will be calculated
#%End
############################################################################

# import sys
import os
import glob
# import string
# import shutil
import atexit
import math

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
    grass.run_command('g.mremove', vect = 'v_mc*', flags = 'f',
                      quiet = True, stderr = nuldev)

def main():
    inmap = options['input']
    output = options['output']

    # mapset = grass.gisenv()['MAPSET']

    global tmp, nuldev, grass_version
    nuldev = None

    # grass_version = grass.version()['version'][0]

    # setup temporary files
    tmp = grass.tempfile()

    # check if input file exists
    if not grass.find_file(inmap, element = 'vector')['file']:
        grass.fatal(_("<%s> does not exist.") % inmap)
        
    # check geometry type
    geom =  grass.vector_info_topo(inmap)
    ifpoints = geom.get('points')
    iflines = geom.get('lines')
    ifbounds = geom.get('boundaries')
    ifareas = geom.get('areas')

    if ifpoints == 0 and iflines == 0 and ifbounds == 0 and ifareas == 0:
        grass.fatal(_("<%s> map is empty.") % inmap)

    # extract different geometries to different maps
    ## points
    if ifpoints > 0:
        grass.run_command('v.extract', _input = inmap, out = 'v_mc_points', 
                          _type = 'point', quiet = True, stderr = nuldev)
        
        p = grass.pipe_command('v.to.db', _map = 'v_mc_points', opt = 'coor', 
                               flags = 'p', quiet = True, stderr = nuldev)
        pc = p.communicate()[0].strip().split('\n')

        xlist = []
        ylist = []
        
        for coor in pc:
            pts_x = coor.split('|')[1]
            xlist.append(float(pts_x))
            pts_y = coor.split('|')[2]
            ylist.append(float(pts_y))
            
        xmean = sum(xlist)/ifpoints
        ymean = sum(ylist)/ifpoints
        
        print "Points mean center: %s, %s" % (xmean, ymean)

    ## lines
    if iflines > 0:
        # extract lines from input map
        grass.run_command('v.extract', _input = inmap, out = 'v_mc_lines', 
                          _type = 'line', quiet = True, stderr = nuldev)
        
        c = grass.pipe_command('v.category', _input = 'v_mc_lines', opt = 'print',
                               flags = 'g', quiet = True, stderr = nuldev)
        cc = c.communicate()[0].strip().split('\n')
        
        lns_xlist = []
        lns_ylist = []

        for cat in cc:
            out_cat = 'v_mc_lines' + '_' + cat
            # extract each poly(line) to separate map
            grass.run_command('v.extract', _input = 'v_mc_lines', _list = cat, 
                              out = out_cat, quiet = True)
            
            # split poly(lines) to simple lines
            out_split = out_cat + '_' + 'split'
            grass.run_command('v.split', _input = out_cat, vertices = 2, 
                              out = out_split, quiet = True, stderr = nuldev)
            
            # delete old categories and assign new categories to lines
            out_catdel = out_split + '_' + 'catdel'
            grass.run_command('v.category', _input = out_split, opt = 'del', 
                              output = out_catdel, quiet = True, stderr = nuldev)
            out_newcats = out_split + '_' + 'newcats'
            grass.run_command('v.category', _input = out_catdel, opt = 'add', 
                              output = out_newcats, quiet = True, stderr = nuldev)
            

            p = grass.read_command('v.to.db', _map = out_newcats, opt = 'length', 
                                       flags = 'p', quiet = True).strip()
            llen = p.split('|')[1]
            print type(float(llen))
            llen2 = float(llen)/2+1
            
            out_pts = out_newcats + '_' + 'pts'
            grass.run_command('v.to.points', _input = out_newcats, output = out_pts,
                              dmax = llen2, quiet = True)
            coor = grass.pipe_command('v.to.db', _map = out_pts, opt = 'coor', layer = 2,
                                      _type = 'point', flags = 'p', quiet = True)
            cc = coor.communicate()[0].strip().split('\n')

            for coords in cc:
                coor_cat = coords.split('|')[0]
                if coor_cat == '2':
                    lns_x = coords.split('|')[1]
                    lns_y = coords.split('|')[2]
                    
                    lns_xlist.append(float(lns_x))
                    lns_ylist.append(float(lns_y))
                    



            cat_geom =  grass.vector_info_topo(out_split)['lines']


            

            if cat_geom == 1:
                print "cat %s is line" % cat
                
                # p = grass.read_command('v.to.db', _map = out_split, opt = 'length', 
                #                        flags = 'p', quiet = True).strip()
                # llen = p.split('|')[1]
                # llen2 = (float(llen)/2)+1
                
                # out_pts = out_split + '_' + 'pts'
                # grass.run_command('v.to.points', _input = out_split, output = out_pts,
                #                   dmax = llen2, quiet = True)
                # coor = grass.pipe_command('v.to.db', _map = out_pts, opt = 'coor', layer = 2,
                #                           _type = 'point', flags = 'p', quiet = True)
                # cc = coor.communicate()[0].strip().split('\n')

                # for coords in cc:
                #     coor_cat = coords.split('|')[0]
                #     if coor_cat == '2':
                #         lns_x = coords.split('|')[1]
                #         lns_y = coords.split('|')[2]
                        
                #         lns_xlist.append(float(lns_x))
                #         lns_ylist.append(float(lns_y))
                
            else:
                print "cat %s is polyline with %s lines" % (cat, cat_geom)

                out_catdel = out_split + '_' + 'catdel'
                grass.run_command('v.category', _input = out_split, opt = 'del', 
                                  output = out_catdel, quiet = True, stderr = nuldev)
                out_newcats = out_split + '_' + 'newcats'
                grass.run_command('v.category', _input = out_catdel, opt = 'add', 
                                  output = out_newcats, quiet = True, stderr = nuldev)

                p = grass.pipe_command('v.to.db', _map = out_newcats, opt = 'length', 
                                       flags = 'p', quiet = True)
                pc = p.communicate()[0].strip().split('\n')
                
                plens = []
                
                for xy in pc:
                    xy_cat = xy.split('|')[0]
                    xy_coors = xy.split('|')[1]
                    
                    plens.append(xy_coors)
                
                # print plens
                
                
                



                
            
        # print lns_xlist
        # print lns_ylist



        
        # out_split = 'v_mc_lines' + '_' + 'split'
        # grass.run_command('v.split', _input = 'v_mc_lines', vertices = 2, 
        #                   out = out_split, quiet = True, stderr = nuldev)
        # out_catdel = 'v_mc_lines' + '_' + 'catdel'
        # grass.run_command('v.category', _input = out_split, opt = 'del', 
        #                   output = out_catdel, quiet = True, stderr = nuldev)
        # out_newcats = 'v_mc_lines' + '_' + 'newcats'
        # grass.run_command('v.category', _input = out_catdel, opt = 'add', 
        #                   output = out_newcats, quiet = True, stderr = nuldev)

        # c = grass.pipe_command('v.category', _input = out_newcats, opt = 'print',
        #                        flags = 'g', quiet = True, stderr = nuldev)
        # cc = c.communicate()[0].strip().split('\n')

        # for cat in cc:
        #     print cat
        #     out_cat = out_newcats + '_' + cat
        #     grass.run_command('v.extract', _input = out_newcats, _list = cat, 
        #                       out = out_cat, quiet = True)


            
        #     p = grass.read_command('v.to.db', _map = out_cat, opt = 'length', 
        #                        flags = 'p', quiet = True).strip()
        #     llen = p.split('|')[1]
        #     llen2 = (float(llen)/2)+1
            
        #     out_pts = out_cat + '_' + 'pts'
        #     print out_pts
        #     grass.run_command('v.to.points', _input = out_cat, output = out_pts,
        #                       dmax = llen2, quiet = True)
            
        #     grass.run_command('d.vect', _map = out_cat, width = 2)
        #     grass.run_command('d.vect', _map = out_pts, color = 'red', size = 8)


            
        
        



    ## boundaries
    if ifbounds > 0:
        grass.run_command('v.extract', _input = inmap, out = 'v_mc_bounds', 
                          _type = 'boundary', quiet = True, stderr = nuldev)

    ## areas
    if ifareas > 0:
        grass.run_command('v.extract', _input = inmap, out = 'v_mc_areas', 
                          _type = 'area', quiet = True, stderr = nuldev)


    
    # mlist = grass.pipe_command('g.mlist', _type = 'vect', pattern = 'v_mc_*')
    # mlist2 = mlist.communicate()[0].strip().split('\n')
    # for vect in mlist2:
    #     if '_points' in vect:
    #         print vect


        # if '_lines' in vect:
        #     print vect
            
            
            

        

    
    
    
        

    


    # ####### DO IT #######
    # # copy input vector map and drop table
    # grass.run_command('g.copy', vect = (inmap, 'v_ldm_vect'), quiet = True, stderr = nuldev)
    # db = grass.vector_db('v_ldm_vect', quiet = True, stderr = nuldev) 
    # if db != {}:
    #     grass.run_command('v.db.droptable', _map = 'v_ldm_vect', flags = 'f', quiet = True, stderr = nuldev)

    # inmap = 'v_mc'


if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
