#!/usr/bin/env python3
############################################################################
#
# MODULE:       v.mbg
#
# AUTHOR(S):    Alexander Muriy
#               (amuriy AT gmail DOT com)
#
# PURPOSE:      Creates a vector map containing polygons which represent a specified
#               minimum bounding geometry enclosing each input feature or each group
#               of input features
#
# COPYRIGHT:    (C) 2019-2020 by the GRASS Development Team
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################
#
# REQUIREMENTS:
#      - NumPy module
#  
#%module
#% description: Creates a vector map containing polygons which represent "Minimum Bounding Geometry".
#% keyword: vector
#% keyword: geometry
#%end

#%option G_OPT_V_INPUT
#%  key: input
#%  description: Input vector map 
#%end

#%option G_OPT_V_OUTPUT
#%  key: output
#%  description: Output vector map (minimum bounding geometry)
#%end

#%option
#% key: geom_type
#% type: string
#% description: Type of output minimum bounding geometry
#% required: yes
#% multiple: no
#% options: convex_hull, envelope, rectangle_area, circle, ellipse
#% answer: rectangle_area
#%end

#%option
#% key: group
#% type: string
#% description: Group input features
#% required: no
#% multiple: no
#% options: none, all, list
#% answer: none
#%end

#%option
#% key: field
#% type: string
#% description: Attribute field to group input features
#% required: no
#% multiple: no
#%end

#%option
#% key: export
#% type: string
#% description: Path to GeoPackage (.gpkg) file to export "minimum bounding geometry" polygons (into the separate layers due to GRASS topological issues with overlapping)
#% required: no
#% multiple: no
#%end

##################
# IMPORT MODULES #
##################

import os
import sys
import atexit
import random
import string

import math
import numpy as np

import grass.script as grass
from grass.pygrass.modules.shortcuts import vector as v
from grass.pygrass.modules.shortcuts import general as g
from grass.pygrass.vector import VectorTopo
from grass.pygrass.vector import Vector
from grass.pygrass.vector.geometry import Point
from grass.exceptions import CalledModuleError

from minboundingrect import minBoundingRect
from minboundingcircle import get_bounding_ball as minBoundingCircle
from minboundingellipse  import getMinVolEllipse as minBoundingEllipse


####################
#### FUNCTIONS #####
####################

def cleanup():
    nuldev = open(os.devnull, 'w')
    grass.run_command('g.remove', flags = 'f', type = ['raster','vector'],
                      stderr = nuldev, pattern = prefix + '*', quiet = True)
    grass.run_command('g.remove', flags = 'f', type = 'region', name = 'TMP_REGION_V_MBG',
                      stderr = nuldev, quiet = True)

    
def random_name():
    rand = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(8)])
    return rand


def vector_to_nparray(in_vect):
    data = VectorTopo(in_vect)
    data.open('r')    
    coords = []
    coor_list = []
    for i in range(len(data)):
        coor = data.read(i+1).coords()
        coor2 = " ".join(str(x) for x in coor)
        coor3 = [float(s) for s in coor2.split(' ')]
        coords.append(coor3)        
    coords_arr = np.array(coords)
    return coords_arr


def nparray_to_vector(in_array, out_vect):
    if in_array.ndim == 2: 
        points = np.rec.fromarrays([in_array.T[0], in_array.T[1]])
    elif in_array.ndim == 1:
        points = [in_array]        
    new = VectorTopo(out_vect)
    new.open("w", overwrite = True)
    for pnt in points:
        new.write(Point(*pnt))
    new.close()
    new.build() 


def get_db_info(inmap):
    vect = Vector(inmap)
    vect.open()
    link = vect.dblinks[0]
    table = link.table()
    cols = table.columns.items()
    vect.close()
    return cols

    
def hull_make(in_vect, hull):
    try:
        v.hull(input = in_vect, output = hull, flags = 'f', quiet = True, stderr = nuldev)
    except CalledModuleError:
        grass.fatal(_('Cannot extract data with <group> option and compute convex hull... Make sure that there is no points in the input map with <group=none> option or check attributes values for special characters in the input vector map.'.format(in_vect)))

    
def hull_get_coords(hull):
    vert = hull + '_vert' 
    v.to_points(input = hull, output = vert, use = 'vertex', layer = '-1',
                flags = 't', quiet = True, stderr = nuldev)
    hull_coords = vector_to_nparray(vert)
    return hull_coords


def mbg_make(in_vect, hull_coords, out_vect):
    if geom_type in 'rectangle_area':
        (rot_angle, area, width, height, center_point, corner_points) = minBoundingRect(hull_coords)
        rot_angle_deg = rot_angle*(180/math.pi)
        rand = random_name()
        cpoints_map = prefix + rand
        nparray_to_vector(corner_points, cpoints_map)
        hull_make(cpoints_map, out_vect)
    elif geom_type in 'convex_hull':
        hull_make(in_vect, out_vect)
    elif geom_type in 'envelope':
        g.region(vector = in_vect, quiet = True)
        v.in_region(output = out_vect, type = 'area', quiet = True,
                    overwrite = True, stderr = nuldev)
    elif geom_type in 'circle':
        try:
            ccenter, rad = minBoundingCircle(hull_coords)
        except np.linalg.linalg.LinAlgError:
            grass.fatal(_("Cannot compute minimum bounding circle for vector map <{}>".format(in_vect)))
        lon = ccenter[0]
        lat = ccenter[1]
        rand = random_name()
        ccenter_map = prefix + rand
        new = VectorTopo(ccenter_map)
        new.open('w', overwrite=True)
        point0 = Point(float(lon), float(lat))
        new.write(point0)
        new.close()
        v.buffer(input = ccenter_map, output = out_vect, distance = math.sqrt(rad), 
                 tolerance=0.001, quiet = True, overwrite = True, stderr = nuldev)    
    elif geom_type in 'ellipse':
        (ell_center, ell_radius, ell_rotation_init) = minBoundingEllipse(hull_coords, .01)
        
        distance = ell_radius[1]
        minordistance = ell_radius[0]
        rot_00 = float(math.degrees(ell_rotation_init[0][0]))
        rot_01 = float(math.degrees(ell_rotation_init[0][1]))

        if rot_01 < 0 and rot_00 < 0:
            ell_rotation = rot_00
        elif (rot_01 > 0 and rot_00 < 0) and (abs(rot_01) > abs(rot_00)):
            ell_rotation = -(rot_00) 
        elif (rot_01 > 0 and rot_00 < 0) and (abs(rot_01) < abs(rot_00)):
            ell_rotation = -(90 + rot_01) 
        elif rot_01 < 0 and rot_00 > 0:
            ell_rotation = rot_00
        elif rot_01 > 0 and rot_00 > 0:
            ell_rotation = -(rot_00)
        
        lon = ell_center[0]
        lat = ell_center[1]
        rand = random_name()        
        ecenter_map = prefix + rand
        new = VectorTopo(ecenter_map)
        new.open('w', overwrite=True)
        point0 = Point(float(lon), float(lat))
        new.write(point0)
        new.close()         
        v.buffer(input = ecenter_map, output = out_vect, distance = distance, 
                 minordistance = minordistance, angle = ell_rotation, tolerance=0.001,
                 quiet = True, overwrite = True, stderr = nuldev)


def mbg_postprocess(in_vect, geom_todel, out_vect):
    rand = random_name()    
    tmp_gpkg = os.path.join(os.path.dirname(tmpfile), rand+'.gpkg')    
    v.out_ogr(input__ = in_vect, output = tmp_gpkg, type__ = 'area',
              flags = 'c', format_ = 'GPKG',
              quiet = True, stderr = nuldev)
    rand = random_name()
    mbg_ogr = prefix + rand
    v.import_(input_ = tmp_gpkg, output = mbg_ogr)
    v.edit(map_ = mbg_ogr, tool = 'delete', type_ = geom_todel,
           cats = '0-999999', layer = 2, quiet = True, stderr = nuldev)
    v.edit(map_ = in_vect, tool = 'delete', type_ = 'centroid',
           cats = '0-999999', quiet = True, stderr = nuldev)
    v.edit(map_ = in_vect, tool = 'copy', bgmap_ = mbg_ogr, type_ = 'centroid',
           cats = '0-999999', quiet = True, stderr = nuldev)
    rand = random_name()
    mbg_clean = prefix + rand
    v.clean(input_ = in_vect, output = mbg_clean, tool = 'rmdac',
            quiet = True, stderr = nuldev, overwrite = True)
    v.centroids(input_ = mbg_clean, output = out_vect, overwrite = True,
                    quiet = True, stderr = nuldev)
    
############
### MAIN ###
############

def main():
    global nuldev, tmpfile, prefix, geom_type, inmap, in_vect
    nuldev = open(os.devnull, 'w')
    tmpfile = grass.tempfile()
    prefix = 'v_mbg_tmp_%d_' % os.getpid()
    
    inmap = options['input']
    outmap = options['output']
    geom_type = options['geom_type']
    group = options['group']
    field = options['field']
    export = options['export']

    # check if the map is in the current mapset
    mapset = grass.find_file(inmap, element='vector')['mapset']
    if not mapset or mapset != grass.gisenv()['MAPSET']:
        grass.fatal(_("Vector map <{}> not found in the current mapset").format(inmap))

    # check for table existance for input map
    try:
        columns = grass.vector_columns(inmap).keys()
    except CalledModuleError as e:
        v.db_addtable(inmap, quiet = True, stderr = nuldev)

    # check for GPKG driver in OGR (for <export> option)
    if export:
        formats = grass.read_command('v.out.ogr', flags = 'l', quiet = True, stderr = nuldev)
        if ' GPKG (rw+): GeoPackage' not in formats.splitlines():
            grass.fatal(_("Option <export> needs GPKG (GeoPackage) driver for module <v.out.ogr>, but it was not found. Exit."))
    # check for GPKG extension (need for GDAL & Co)
    if export and '.gpkg' not in export:
        export = export + '.gpkg'
    
    # save initial region for later
    g.region(save = 'TMP_REGION_V_MBG')
    
    ## main ##
    db_info = get_db_info(inmap)

    print(db_info)

    attr_dict = {}
    
    # check for <group> option
    if group == 'none':
        # test input feature type
        vect_info = grass.vector_info_topo(inmap)
        if vect_info['points'] > 0:
            grass.fatal(_("Points found in input vector map <{}>. Cannot use option <group=none> with the points.").format(inmap))
        # get cat's list
        group_sel = v.db_select(flags = 'c', map = inmap, columns = 'cat', stdout_= grass.PIPE)
        group_list = group_sel.outputs.stdout.splitlines()
        rand = random_name()
        outmap_edit = prefix + rand
        v.edit(map = outmap_edit, tool = 'create', quiet = True, stderr = nuldev)
        extr_mbg_list = []

        if export:
            v.out_ogr(input_ = outmap_edit, output = export, output_layer = 'tmp',
                      flags = 'n', format_ = 'GPKG', quiet = True, stderr = nuldev)
        
        
        
        # extract features
        for index, value in enumerate(group_list):
            extr = prefix + '_extr_' + str(index)
            try:
                v.extract(input = inmap, where = 'cat == "{}"'.format(value),
                          output = extr, quiet = True, stderr = nuldev)
            except CalledModuleError:
                grass.fatal(_('Cannot extract data with <group> option and compute convex hull... Make sure that there is no points in the input map with <group=none> option or check attributes values for special characters in the input vector map with <group=list> option'.format(inmap)))
                
            
            
            attr_val = grass.vector_db_select(extr)['values']
            attr_dict.update(attr_val)
            
            
            
            extr_hull = prefix + '_extr_' + str(index) + '_hull'
            hull_make(extr, extr_hull) 
            
            hull_coords = hull_get_coords(extr_hull)
            extr_mbg = prefix + '_mbg_' + str(index)
            extr_mbg_list.append(extr_mbg)

            mbg_make(extr_hull, hull_coords, extr_mbg)

            if export:
                lyr_name = 'mbg_' + str(index)
                v.out_ogr(input = extr_mbg, output = export, type_ = 'area',
                          output_layer = lyr_name,
                          flags = 'u', format_ = 'GPKG')
            
            rand = random_name()
            bound_cats = prefix + rand            
            v.category(input_ = extr_mbg, output = bound_cats, option = 'add',
                       type_ = 'boundary',
                       quiet = True, stderr = nuldev)        
            v.edit(map_ = outmap_edit, tool = 'copy', bgmap = bound_cats,
                   type_ = 'boundary', cats = 1)
            
            
            
            
            g.rename(vector = (outmap_edit, outmap), overwrite = True)

        # v.db_select(map_ = outmap)
        
        # vect = VectorTopo(outmap)
        # vect.open('w', tab_cols=cols)
        
        
        print(attr_dict)

        
    elif group == 'all':
        rand = random_name()
        all_hull = prefix + rand
        hull_make(inmap, all_hull)
        hull_coords = hull_get_coords(all_hull)
        mbg_make(all_hull, hull_coords, outmap)

        if export:
            v.out_ogr(input_ = outmap, output = export, type_ = 'area',
                      output_layer = 'mbg', format_ = 'GPKG',
                      quiet = True, stderr = nuldev)
        
    elif group == 'list':
        if not field:
            grass.fatal(_("Attribute <field> must be selected with <group=list> option for group input features"))
        
        # check for field existance for input map
        if field not in columns:
            grass.fatal(_("Field <{}> not found in attribute table of input vector map <{}>".format(field, inmap)))
                        
        group_sel = v.db_select(flags = 'c', map = inmap, columns = field,
                                group = field, stdout_= grass.PIPE)
        group_list = group_sel.outputs.stdout.splitlines()
        rand = random_name()
        outmap_edit = prefix + rand
        v.edit(map = outmap_edit, tool = 'create', quiet = True, stderr = nuldev)
        
        if export:
            v.out_ogr(input_ = outmap_edit, output = export, output_layer = 'tmp',
                      flags = 'n', format_ = 'GPKG', quiet = True, stderr = nuldev)
        
        for index, value in enumerate(group_list):
            extr = prefix + '_extr_' + str(index)
            try:
                v.extract(input = inmap, where = '{} == "{}"'.format(field, value),
                          output = extr, quiet = True, stderr = nuldev)
            except CalledModuleError:
                grass.fatal(_('Cannot extract data with <group> option and compute convex hull... Make sure that there is no points in the input map with <group=none> option or check attributes values for special characters in the input vector map with <group=list> option'.format(inmap)))

            extr_hull = prefix + '_extr_' + str(index) + '_hull'
            hull_make(extr, extr_hull)            

            hull_coords = hull_get_coords(extr_hull)
            extr_mbg = prefix + '_mbg_' + str(index)

            mbg_make(extr_hull, hull_coords, extr_mbg)

            if export:
                lyr_name = 'mbg_' + str(index)
                v.out_ogr(input = extr_mbg, output = export, type_ = 'area',
                          output_layer = lyr_name,
                          flags = 'u', format_ = 'GPKG')

        ### NEW ###            
            rand = random_name()
            bound_cats = prefix + rand            
            v.category(input_ = extr_mbg, output = bound_cats, option = 'add',
                       type_ = 'boundary', quiet = True, stderr = nuldev) 
            v.edit(map_ = outmap_edit, tool = 'copy', bgmap = bound_cats,
                   type_ = 'boundary', cats = 1)

        g.rename(vector = (outmap_edit, outmap), overwrite = True)
    
    # postprocessing MBG polygons
    mbg_postprocess(outmap, 'centroid', outmap)
    
    # restore initial region
    g.region(region = 'TMP_REGION_V_MBG')
        
    
if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
    
    
