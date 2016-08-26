#!/usr/bin/env python
# -*- coding: utf-8 -*-
# nominatim_search.py

import sys,urllib,json

# city = sys.argv[1]
# city = 'Абакан'

for city in 'Ельня','Надым','Каневская':

    params = urllib.urlencode({'city': city, 'format':'json', 'addressdetails':1})
    f = urllib.urlopen("http://nominatim.openstreetmap.org/search?%s" % params )
    t = json.loads(f.read())
    
    for el in t:
        region = el['address']['state'] 
        print region
        break

    
    
    
    
