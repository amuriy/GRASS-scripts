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
# VERSION: 0.2
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
import re
# import string
# import shutil
import atexit
# import math

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

    ### extract different geometries to different maps
    # points
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

    ### lines
    if iflines > 0:
        # extract lines from input map
        grass.run_command('v.extract', _input = inmap, out = 'v_mc_lines', 
                          _type = 'line', quiet = True, stderr = nuldev)
        
        # delete original categories and make new ones
        in_catdel = 'v_mc_lines' + '_' + 'catdel'
        grass.run_command('v.category', _input = 'v_mc_lines', opt = 'del', 
                          output = in_catdel, quiet = True, stderr = nuldev)
        in_newcats = 'v_mc_lines' + '_' + 'newcats'
        grass.run_command('v.category', _input = in_catdel, opt = 'add', 
                          output = in_newcats, quiet = True, stderr = nuldev)

        ### separate lines from polylines
        # parse the output of v.out.ascii 
        asc = grass.pipe_command('v.out.ascii', _input = in_newcats, _format ='standard', 
                           quiet = True, stderr = nuldev)
        ascs = asc.communicate()[0].strip().split('\n')
        
        vert_list = []
        cat_list = []

        for line in ascs:
            match1 = re.search('^L', line)
            match2 = re.search('^ [0-9] ', line)
            if match1:
                vert_list.append(line.strip().replace("  "," ").replace("   "," "))
            if match2:
                cat_list.append(line.strip().replace("  "," ").replace("   "," "))
                
        lines_list = []
        poly_list = []

        for l in zip(vert_list,cat_list):
            if l[0][2] == '2':
                lines_list.append(l[1][2:])
            else:
                poly_list.append(l[1][2:])
        
        lines_ex = ",".join(lines_list)
        poly_ex = ",".join(poly_list)
        
        # print "Lines are %s" % lines_ex
        # print "Polylines are %s" % poly_ex

        ### explode all lines
        out_split = 'v_mc_lines' + '_' + 'split'
        grass.run_command('v.split', _input = in_newcats, vertices = 2, 
                          out = out_split, quiet = True, stderr = nuldev)
        
        # populate oldcats list
        oldcats_list = []
        c = grass.pipe_command('v.category', _input = out_split, opt = 'print',
                               flags = 'g', quiet = True, stderr = nuldev)
        cc = c.communicate()[0].strip().split('\n')

        for cat in cc:
            oldcats_list.append(cat)

        # make segments with new cats
        out_catdel = out_split + '_' + 'catdel'
        grass.run_command('v.category', _input = out_split, opt = 'del', 
                          output = out_catdel, quiet = True, stderr = nuldev)
        
        out_newcats = out_split + '_' + 'newcats'
        grass.run_command('v.category', _input = out_catdel, opt = 'add', 
                          output = out_newcats, quiet = True, stderr = nuldev)

        # populate newcats list        
        newcats_list = []
        c = grass.pipe_command('v.category', _input = out_newcats, opt = 'print',
                               flags = 'g', quiet = True, stderr = nuldev)
        cc = c.communicate()[0].strip().split('\n')

        for cat in cc:
            newcats_list.append(cat)

        print

        # compute lines' length and populate length list
        len_list = []
        p = grass.pipe_command('v.to.db', _map = out_newcats, opt = 'length', 
                                       flags = 'p', quiet = True)
        pc = p.communicate()[0].strip().split('\n')
        for plen in pc:
            tolist = plen.split('|')[1]
            len_list.append(float(tolist))
            
        # get coordinates of lines' centroids
        p = grass.pipe_command('v.to.db', _map = out_newcats, opt = 'length', 
                               flags = 'p', quiet = True)
        pc = p.communicate()[0].strip().split('\n')
        
        tmp_seg = tmp + '.inf'
        inf_seg = file(tmp_seg, 'a+b')

        for lns in pc:
            lcat = lns.split('|')[0]
            llen = lns.split('|')[1]
            llen2 = float(llen)/2
            line = "P %s %s %s\n" % (lcat, lcat, llen2) 
            inf_seg.write(line)

        inf_seg.close()
    
        # make central points of lines
        out_pts = out_newcats + '_' + 'pts'
        grass.run_command('v.segment', _input = out_newcats, output = out_pts,
                          _file = tmp_seg, quiet = True, stderr = nuldev)

        
        coor = grass.pipe_command('v.to.db', _map = out_pts, opt = 'coor',  
                                  _type = 'point', flags = 'p', quiet = True)
        cc = coor.communicate()[0].strip().split('\n')
        
        # populate coords list
        coords_list = []
        
        for coords in cc:
            tolist = coords.split('|')[1:3]
            tolist_fl = [float(x) for x in tolist]
            coords_list.append(tolist_fl)

        # make full list with new cats, old cats, lengths and coords
        zip_list = zip(oldcats_list, newcats_list, len_list, coords_list)

        mean_xy_list = []

        # extract mean XY for simple lines
        for lns in lines_list:
            ln = [x for x in zip_list if x[0] == lns]
            mean_xy_list.append(ln[0][3])
            
        # compute mean XY for polylines
        for po in poly_list:
            li = [x for x in zip_list if x[0] == po]

            wx_list = []
            wy_list = []
            w_list = []
            
            for xy in li:
                wx = xy[2]*xy[3][0]
                wy = xy[2]*xy[3][1]
                wx_list.append(wx)
                wy_list.append(wy)
                w_list.append(xy[2])
                
            sum_wx = sum(wx_list)
            sum_wy = sum(wy_list)
            sum_w = sum(w_list)
            
            mean_x = sum_wx/sum_w
            mean_y = sum_wy/sum_w
            mean_xy = [mean_x, mean_y]
            mean_xy_list.append(mean_xy)
        
        # compute final mean XY for all lines
        lns_finx = []
        lns_finy = []
        
        pts_count = len(mean_xy_list)
        
        for xy in mean_xy_list:
            lns_finx.append(xy[0])
            lns_finy.append(xy[1])

        finx = sum(lns_finx)/pts_count
        finy = sum(lns_finy)/pts_count

        print finx, finy
            

        


        # fin_lns_list = []


  


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