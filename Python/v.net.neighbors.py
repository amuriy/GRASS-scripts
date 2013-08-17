#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:       v.net.neighbors
# AUTHOR(S):    Alexander Muriy
#               (Institute of Environmental Geoscience, Moscow, Russia)  
#               e-mail: amuriy AT gmail DOT com 
#
# PURPOSE:      Finds neighbor nodes for every node in the net and uploads
#               their category numbers to attribute table of net (layer 2). 
#               Optionally print neighbors' categories or dumps them to text file.
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
#%  description: Finds neighbor nodes for every node in the net and uploads their category numbers to attribute table of net (layer 2). Optionally print neighbors' categories or dumps them to text file.
#%  keywords: display, graphics, vector, symbology
#%End
#%Option
#%  key: input
#%  type: string
#%  required: yes
#%  key_desc: name
#%  description: Input net vector map
#%  gisprompt: old,vector,vector
#%End
#%Option
#%  key: dump
#%  type: string
#%  required: no
#%  key_desc: name
#%  description: Text file to dump neighbors' categories
#%  gisprompt: new_file,file,output
#%End
#%Flag
#%  key: i
#%  description: Use only nodes on lines' intersections
#%End
#%Flag
#%  key: p
#%  description: Just print neighbors' categories for every node
#%End
############################################################################

import sys,os
import shutil
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
    nuldev = file(os.devnull, 'w')
    grass.run_command('g.mremove', vect = 'v_net_neighbors_*', flags = 'f',
                      quiet = True, stderr = nuldev)
    
def main():
    global tmp, nuldev
    nuldev = file(os.devnull, 'w')

    ## setup temporary files
    tmp = grass.tempfile()
    tmpf = 'v_net_neighbors'

    inmap = options['input']
    outfile = options['dump']

    # check if input file exists
    if not grass.find_file(inmap, element = 'vector')['file']:
        grass.fatal(_("<%s> does not exist.") % inmap)

    # check for table in net vector map
    try:
        f = grass.vector_db(inmap)[1]
    except KeyError:
        grass.run_command('v.db.addtable', _map = inmap, layer = 2,
                          quiet = True, stderr = nuldev)
        
    ## extract temp nodes and lines
    nodes = tmpf + '_nodes'
    lines = tmpf + '_lines'

    grass.run_command('v.extract', input = inmap, output = nodes, layer = 2, 
                      _type = 'point', flags = 't', quiet = True, stderr = nuldev)
    grass.run_command('v.extract', input = inmap, output = lines,  
                      _type = 'line', flags = 't', quiet = True, stderr = nuldev)

    ## filter nodes on line intersections if with '-i' flag 
    if flags['i']:
        p = grass.pipe_command('v.net', _input = inmap, operation = 'nreport',
                               quiet = True, stderr = nuldev)
        c  = p.communicate()[0].strip().split('\n')
        filt = [elem for elem in c if ',' in elem]

        fnodes = []
        
        for x in filt:
            spl = x.split(' ')
            fnodes.append(spl[0])

        fnodes_str = ','.join(fnodes)
        
        nsel = tmpf + '_nsel'
        grass.run_command('v.extract', _input = nodes, _list = fnodes_str, 
                          output = nsel, layer = 2, _type = 'point',
                          quiet = True, stderr = nuldev)

        grass.run_command('g.rename', vect = (nsel,nodes), overwrite = True, 
                          quiet = True, stderr = nuldev)
        
        
    if not flags['p']:
        grass.run_command('v.db.addcol', _map = inmap, layer = 2, 
                          columns = 'neigh_node varchar(255)', 
                          quiet = True, stderr = nuldev)

    ## main cycle (extract every node and make 2 selects)
    out_dict = {}

    p = grass.pipe_command('v.category', _input = nodes, opt = 'print', layer = 2, 
                           _type = 'point', quiet = True, stderr = nuldev)
    c = p.communicate()[0].strip().split('\n')
    for cat in c:
        icat = int(cat)

        nnode = nodes + cat
        grass.run_command('v.extract', _input = nodes, _list = cat, 
                          output = nnode, layer = 2, _type = 'point',
                          flags = 't', quiet = True, stderr = nuldev)

        linode = nnode + '_lines'
        grass.run_command('v.select', ain = lines, _bin = nnode, 
                          blayer = 2, output = linode, 
                          operator = 'overlap', quiet = True, stderr = nuldev)
        
        linode_pts = linode + '_pts'
        grass.run_command('v.select', ain = nodes, alayer = 2, 
                          _bin = linode, output = linode_pts, 
                          operator = 'overlap', quiet = True, stderr = nuldev)
        
        pcat = grass.pipe_command('v.category', _input = linode_pts, layer = 2,
                                  opt = 'print', quiet = True, stderr = nuldev)
        ccat = pcat.communicate()[0].strip().split('\n')
        ccat.remove(cat)
        
        ncat_list = []
        ncat_list.append(ccat)

        str_db = ','.join(map(str, ncat_list))
        str_db1 = str_db.replace("[", "").replace("]", "").replace("'", "").replace(" ", "")

        out_dict[icat] = str_db1
        
        if not flags['p']:
            grass.run_command('v.db.update', _map = inmap, layer = 2, 
                              column = 'neigh_node', value = '%s' % (str_db1), 
                              where = "cat = %d" % (icat), 
                              quiet = True, stderr = nuldev )
        
    ## output to stdout / file
    tmp3 = tmp + '.out'
    outf2 = file(tmp3, 'w')
    for key in sorted(out_dict.iterkeys()):
        val = out_dict[key]
        print >> outf2, "%s %s" % (key,val)
    outf2.close()
    
    if flags['p']:
        with open(tmp3, 'rb') as f:
            print f.read()

    if outfile:
        shutil.copyfile(tmp3, outfile)
                

    return 0


if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
