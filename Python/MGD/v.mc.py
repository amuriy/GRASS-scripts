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
    grass.run_command('g.mremove', vect = 'v_mc*', flags = 'f',
                      quiet = True, stderr = nuldev)

def main():
    inmap = options['input']
    outmap = options['output']

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
    grass.run_command('v.out.ogr', _input = inmap, dsn = tmp1, 
                      _format = "CSV", _type = ('point','line','boundary','area'), 
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
        
        grass.run_command('v.in.ascii', _input = out, output = outmap,
                          fs = ' ', quiet = True, stderr = nuldev)




    
    # if not outmap:
    #     if flags['c']:
    #         print "%s,%s" % (finx_all, finy_all)
    #     else:
    #         print "Mean center: %s, %s" % (finx_all, finy_all)

    # #### Write output file if needed
    # if outmap:
    #     tmp_out = tmp + '.out'
    #     outf = file(tmp_out, 'w')
    #     print >> outf, str(finx_all) + ',' + str(finy_all)
    #     outf.close()
        
    #     grass.run_command('v.in.ascii', _input = tmp_out, output = outmap,
    #                       fs = ',', quiet = True, stderr = nuldev)
        



if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()















    # # check geometry type
    # geom =  grass.vector_info_topo(inmap)
    # ifpoints = geom.get('points')
    # iflines = geom.get('lines')
    # ifbounds = geom.get('boundaries')
    # ifcent = geom.get('centroids')
    # ifareas = geom.get('areas')

    # if ifpoints == 0 and iflines == 0 and ifbounds == 0 and ifareas == 0:
    #     grass.fatal(_("<%s> map is empty.") % inmap)

    # mean_centers = []

    # # check for categories for input map
    # incats = grass.read_command('v.category', _input = inmap, opt = 'print', 
    #                    quiet = True, stderr = nuldev)
    # if not incats:
    #     grass.fatal(_("<%s> map have no categories of vector features. Please add categories to work with the module.") % inmap)
    
    
    # ### extract different geometries to different maps and compute mean center
    # #### points
    # if ifpoints > 0:
    #     grass.run_command('v.extract', _input = inmap, out = 'v_mc_points', 
    #                       _type = 'point', quiet = True, stderr = nuldev)
        
    #     p = grass.pipe_command('v.to.db', _map = 'v_mc_points', opt = 'coor', 
    #                            flags = 'p', quiet = True, stderr = nuldev)
    #     pc = p.communicate()[0].strip().split('\n')

    #     xlist = []
    #     ylist = []
        
    #     for coor in pc:
    #         pts_x = coor.split('|')[1]
    #         xlist.append(float(pts_x))
    #         pts_y = coor.split('|')[2]
    #         ylist.append(float(pts_y))
            
    #     xmean = sum(xlist)/ifpoints
    #     ymean = sum(ylist)/ifpoints
        
    #     # if not outmap:
    #     #     print "Points' mean center: %s, %s" % (xmean, ymean)
        
    #     points_append = (xmean, ymean)
    #     mean_centers.append(points_append)

        
    # #### polygons
    # if ifareas > 0 and ifcent > 0:
    #     grass.run_command('v.extract', _input = inmap, out = 'v_mc_areas', 
    #                       _type = 'area', quiet = True, stderr = nuldev)
        
    #     # delete original categories of centroids and make new ones
    #     grass.run_command('v.edit', _map = 'v_mc_areas', tool = 'delete',
    #                       cats = '0-999999', _type = 'centroid', 
    #                       quiet = True, stderr = nuldev)
        
    #     newcent = 'v_mc_areas' + '_' + 'newcent'
    #     grass.run_command('v.centroids', _input = 'v_mc_areas', 
    #                       out = newcent, quiet = True, stderr = nuldev)

    #     coor = grass.pipe_command('v.to.db', _map = newcent, opt = 'coor',  
    #                               _type = 'centroid', flags = 'p', quiet = True)
    #     cc = coor.communicate()[0].strip().split('\n')

    #     # populate cats and coords lists of centroids
    #     cent_cats = []
    #     cent_coords = []
        
    #     for coords in cc:
    #         # cent_cats.append(coords.split('|')[0])
    #         tolist = coords.split('|')[1:3]
    #         tolist_fl = [float(x) for x in tolist]
    #         cent_coords.append(tolist_fl)
            

    #     # # populate areas' list of polygons (need for "multipolygons")
    #     # areas_list = []
    #     # areas = grass.pipe_command('v.to.db', _map = newcent, opt = 'area',  
    #     #                            flags = 'p', quiet = True)
    #     # ars = areas.communicate()[0].strip().split('\n')
        
    #     # for ar in ars:
    #     #     areas_list.append(ar.split('|')[1])
            


    #     # compute final mean XY for areas
    #     ar_finx = []
    #     ar_finy = []
        
    #     ar_count = len(cent_coords)
        
    #     for xy in cent_coords:
    #         ar_finx.append(xy[0])
    #         ar_finy.append(xy[1])

    #     finx_areas = sum(ar_finx)/ar_count
    #     finy_areas = sum(ar_finy)/ar_count
        
    #     areas_append = (finx_areas, finy_areas)
    #     mean_centers.append(areas_append)

    #     # if not outmap:
    #     #     print "Areas' mean center: %s, %s" % (finx_areas, finy_areas)


    # #### boundaries
    # if ifbounds > 0:
    #     grass.run_command('v.extract', _input = inmap, out = 'v_mc_bounds', 
    #                       _type = 'boundary', quiet = True, stderr = nuldev)
    
    #     if ifcent > 0 and ifcent == ifareas:
    #         bounds_sel = 'v_mc_bounds' + '_' + 'sel'
    #         grass.run_command('v.select', ainput = 'v_mc_bounds', binput = 'v_mc_areas', 
    #                           out = bounds_sel, flags = 'r', quiet = True, stderr = nuldev)
    #         bounds_lin = bounds_sel + '_' + 'lines'
    #         grass.run_command('v.type', _input = bounds_sel, out = bounds_lin,
    #                           _type = ('boundary', 'line'), quiet = True, stderr = nuldev)

    #     else:
    #         bounds_sel = 'v_mc_bounds'
    #         bounds_lin = bounds_sel + '_' + 'lines'
    #         grass.run_command('v.type', _input = bounds_sel, out = bounds_lin,
    #                           _type = ('boundary', 'line'), quiet = True, stderr = nuldev)

    # #### lines
    # find_lin = grass.find_file('v_mc_bounds_sel_lines', element = 'vector')['file'] or grass.find_file('v_mc_bounds_lines', element = 'vector')['file']
    # if iflines == 0 and find_lin:
    #     inmap = bounds_lin
    #     geom =  grass.vector_info_topo(bounds_lin)
    #     iflines = geom.get('lines')
        
    # if iflines > 0:
    #     # extract lines from input map
    #     grass.run_command('v.extract', _input = inmap, out = 'v_mc_lines', 
    #                       _type = 'line', quiet = True, stderr = nuldev)

    #     # patch with lines from bounds if needed
    #     if grass.find_file('v_mc_bounds_sel_lines', element = 'vector')['file'] or grass.find_file('v_mc_bounds_lines', element = 'vector')['file']:
    #         grass.run_command('v.patch', _input = ('v_mc_lines', bounds_lin), 
    #                           out = 'v_mc_lines_bounds', quiet = True, stderr = nuldev)

    #         v_mc_lines_to = 'v_mc_lines_bounds'
    #     else:
    #         v_mc_lines_to = 'v_mc_lines'

    #     # delete original categories and make new ones
    #     in_catdel = 'v_mc_lines' + '_' + 'catdel'
    #     grass.run_command('v.category', _input = v_mc_lines_to, opt = 'del', 
    #                       output = in_catdel, quiet = True, stderr = nuldev)
    #     in_newcats = 'v_mc_lines' + '_' + 'newcats'
    #     grass.run_command('v.category', _input = in_catdel, opt = 'add', 
    #                       output = in_newcats, quiet = True, stderr = nuldev)

    #     ### separate lines from polylines
    #     # parse the output of v.out.ascii 
    #     asc = grass.pipe_command('v.out.ascii', _input = in_newcats, _format ='standard', 
    #                        quiet = True, stderr = nuldev)
    #     ascs = asc.communicate()[0].strip().split('\n')
        
    #     vert_list = []
    #     cat_list = []

    #     for line in ascs:
    #         match1 = re.search('^L', line)
    #         match2 = re.search('^ [0-9] ', line)
    #         if match1:
    #             vert_list.append(line.strip().replace("  "," ").replace("   "," "))
    #         if match2:
    #             cat_list.append(line.strip().replace("  "," ").replace("   "," "))
                
    #     lines_list = []
    #     poly_list = []

    #     for l in zip(vert_list,cat_list):
    #         if l[0][2] == '2':
    #             lines_list.append(l[1][2:])
    #         else:
    #             poly_list.append(l[1][2:])
        
    #     lines_ex = ",".join(lines_list)
    #     poly_ex = ",".join(poly_list)
        
    #     # print "Lines are %s" % lines_ex
    #     # print "Polylines are %s" % poly_ex

    #     ### explode all lines
    #     out_split = 'v_mc_lines' + '_' + 'split'
    #     grass.run_command('v.split', _input = in_newcats, vertices = 2, 
    #                       out = out_split, quiet = True, stderr = nuldev)
        
    #     # populate oldcats list
    #     oldcats_list = []
    #     c = grass.pipe_command('v.category', _input = out_split, opt = 'print',
    #                            flags = 'g', quiet = True, stderr = nuldev)
    #     cc = c.communicate()[0].strip().split('\n')

    #     for cat in cc:
    #         oldcats_list.append(cat)

    #     # make segments with new cats
    #     out_catdel = out_split + '_' + 'catdel'
    #     grass.run_command('v.category', _input = out_split, opt = 'del', 
    #                       output = out_catdel, quiet = True, stderr = nuldev)
        
    #     out_newcats = out_split + '_' + 'newcats'
    #     grass.run_command('v.category', _input = out_catdel, opt = 'add', 
    #                       output = out_newcats, quiet = True, stderr = nuldev)

    #     # populate newcats list        
    #     newcats_list = []
    #     c = grass.pipe_command('v.category', _input = out_newcats, opt = 'print',
    #                            flags = 'g', quiet = True, stderr = nuldev)
    #     cc = c.communicate()[0].strip().split('\n')

    #     for cat in cc:
    #         newcats_list.append(cat)

    #     # compute lines' length and populate length list
    #     len_list = []
    #     p = grass.pipe_command('v.to.db', _map = out_newcats, opt = 'length', 
    #                                    flags = 'p', quiet = True)
    #     pc = p.communicate()[0].strip().split('\n')
    #     for plen in pc:
    #         tolist = plen.split('|')[1]
    #         len_list.append(float(tolist))
            
    #     # get coordinates of lines' centroids
    #     p = grass.pipe_command('v.to.db', _map = out_newcats, opt = 'length', 
    #                            flags = 'p', quiet = True)
    #     pc = p.communicate()[0].strip().split('\n')
        
    #     tmp_seg = tmp + '.inf'
    #     inf_seg = file(tmp_seg, 'a+b')

    #     for lns in pc:
    #         lcat = lns.split('|')[0]
    #         llen = lns.split('|')[1]
    #         llen2 = float(llen)/2
    #         line = "P %s %s %s\n" % (lcat, lcat, llen2) 
    #         inf_seg.write(line)

    #     inf_seg.close()
    
    #     # make central points of lines
    #     out_pts = out_newcats + '_' + 'pts'
    #     grass.run_command('v.segment', _input = out_newcats, output = out_pts,
    #                       _file = tmp_seg, quiet = True, stderr = nuldev)
        
    #     coor = grass.pipe_command('v.to.db', _map = out_pts, opt = 'coor',  
    #                               _type = 'point', flags = 'p', quiet = True)
    #     cc = coor.communicate()[0].strip().split('\n')
        
    #     # populate coords list
    #     coords_list = []
        
    #     for coords in cc:
    #         tolist = coords.split('|')[1:3]
    #         tolist_fl = [float(x) for x in tolist]
    #         coords_list.append(tolist_fl)

    #     # make full list with new cats, old cats, lengths and coords
    #     zip_list = zip(oldcats_list, newcats_list, len_list, coords_list)

    #     mean_xy_list = []

    #     # extract mean XY for simple lines
    #     for lns in lines_list:
    #         ln = [x for x in zip_list if x[0] == lns]
    #         mean_xy_list.append(ln[0][3])
            
    #     # compute mean XY for polylines
    #     for po in poly_list:
    #         li = [x for x in zip_list if x[0] == po]

    #         wx_list = []
    #         wy_list = []
    #         w_list = []
            
    #         for xy in li:
    #             wx = xy[2]*xy[3][0]
    #             wy = xy[2]*xy[3][1]
    #             wx_list.append(wx)
    #             wy_list.append(wy)
    #             w_list.append(xy[2])
                
    #         sum_wx = sum(wx_list)
    #         sum_wy = sum(wy_list)
    #         sum_w = sum(w_list)
            
    #         mean_x = sum_wx/sum_w
    #         mean_y = sum_wy/sum_w
    #         mean_xy = [mean_x, mean_y]
    #         mean_xy_list.append(mean_xy)
        
    #     # compute final mean XY for all lines
    #     lns_finx = []
    #     lns_finy = []
        
    #     pts_count = len(mean_xy_list)
        
    #     for xy in mean_xy_list:
    #         lns_finx.append(xy[0])
    #         lns_finy.append(xy[1])

    #     finx_lines = sum(lns_finx)/pts_count
    #     finy_lines = sum(lns_finy)/pts_count
        
    #     lines_append = (finx_lines,finy_lines)
    #     mean_centers.append(lines_append)

    #     # if not outmap:
    #     #     print "Lines' mean center: %s, %s" % (finx_lines, finy_lines)
    
        
    # #### compute final mean XY for all geometries
    # all_finx = []
    # all_finy = []
    
    # all_count = len(mean_centers)
    
    # for xy in mean_centers:
    #     all_finx.append(xy[0])
    #     all_finy.append(xy[1])
    
    # finx_all = sum(all_finx)/all_count
    # finy_all = sum(all_finy)/all_count






