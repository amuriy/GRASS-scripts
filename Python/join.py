#! /usr/bin/python
############################################################################
#
# MODULE:       
# AUTHOR:       
# PURPOSE:      
# COPYRIGHT:    (c) 2017 
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################

#%Module
#% description: 
#% keyword: vector
#% keyword: area
#% keyword: join
#%End

#%option G_OPT_V_MAP
#% key: map
#% label: Name of vector polygon map for which to edit attributes
#% required : yes
#%end

#%option G_OPT_V_INPUT
#% key: query_map
#% label: Name of vector polygon map to be queried
#% required : yes
#%end

#%option
#% key: res
#% label: Region resolution for temp raster (or use default resolution)
#% type: string
#% required: no
#%end

#%option
#% key: query_column
#% type: string
#% label: Name of attribute column to be queried
#% description: 
#% required: yes
#%end


import sys
import atexit
import grass.script as grass

def cleanup():
    grass.run_command('g.remove', flags='f', type_ = 'raster',
                      name = 'raster_tmp', quiet = True)
    grass.run_command('g.remove', flags='f', type_ = 'vector',
                      pattern = 'vector_tmp*', quiet = True)

def main():
    res = options['res']
    poly1 = options['map']
    if "@" in poly1:
        poly1 = poly1.split("@")[0]
    poly2 = options['query_map']
    qcol = options['query_column']
    if not res:
        cur_region = grass.region()
        res = cur_region['nsres']
    
    grass.run_command('g.region', res = res, quiet = True)
    grass.run_command('v.to.rast', type_ = 'area',
                      input_ = poly2, output = 'raster_tmp',
                      use = 'attr', attribute_column = 'cat',
                      label_column = qcol,
                      quiet = True)

    p = grass.pipe_command('r.category', map = 'raster_tmp',
                           separator = '|', quiet = True)
    cats = []
    labels = []
    for line in p.stdout:
        cats.append(line.rstrip('\r\n').split('|')[0])
        labels.append(line.rstrip('\r\n').split('|')[1])
    p.wait()

    query_dict = dict(zip(cats,labels))

    grass.run_command('v.extract', input_ = poly1,
                      output = 'vector_tmp1',
                      type_ = 'centroid',
                      overwrite = True, quiet = True)
    grass.run_command('v.category', input_ = poly1,
                      output = 'vector_tmp2',
                      option = 'add', flags = 't',
                      type_ = 'boundary',
                      overwrite = True)
    # grass.run_command('v.extract', input_ = 'vector_tmp2',
    #                   output = 'vector_tmp3',
    #                   type_ = 'boundary',
    #                   overwrite = True)
    # grass.run_command('v.edit', map_ = 'vector_tmp3',
    #                   tool = 'delete',
    #                   type_ = 'centroid',
    #                   ids = 0-99999999,
    #                   overwrite = True)
    # grass.run_command('v.category', input_ = 'vector_tmp3',
    #                   output = 'vector_tmp4',
    #                   option = 'del',
    #                   type_ = 'boundary',
    #                   overwrite = True)    
    grass.run_command('v.db.addcolumn', map_ = 'vector_tmp1',
                      column = 'rast_cat int', quiet = True)
    grass.run_command('v.db.addcolumn', map_ = 'vector_tmp1',
                      column = qcol, quiet = True)
    grass.run_command('v.what.rast', map_ = 'vector_tmp1',
                      raster = 'raster_tmp',
                      column = 'rast_cat',
                      type_ = 'centroid',
                      overwrite = True, quiet = True)    

    for key,value in query_dict.items():
        grass.run_command('v.db.update', map_ = 'vector_tmp1',
                          col = qcol, value = value,
                          where = "rast_cat = %s" % key,
                          quiet = True)

    grass.run_command('v.db.dropcolumn', map_ = 'vector_tmp1',
                      column = 'rast_cat', quiet = True)

    grass.run_command('v.edit', map_ = 'vector_tmp1',
                      tool = 'copy', bgmap = 'vector_tmp2',
                      type_ = 'boundary', cats = 0-99999999)

    sys.exit(0)
    
    grass.run_command('g.rename', vector = ('vector_tmp1', poly1),
                      overwrite = True, quiet = True)


    
    # f = grass.vector_layer_db(poly1, 1)

    # table = f['table']
    # keycol = f['key']
    # database = f['database']
    # driver = f['driver']

    # sql = "ALTER TABLE %s RENAME TO %s" % ('vector_tmp1', poly1)
    # print sql
    # grass.write_command('db.execute', input_ = '-', database = database, driver = driver, stdin = sql)
    

if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
