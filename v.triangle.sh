#!/bin/sh

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
# COPYRIGHT:    (C) 2012, 2019 Alexander Muriy / GRASS Development Team
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

if [ -z "$GISBASE" ] ; then
    echo "You must be in GRASS GIS to run this program." 1>&2
    exit 1
fi

if [ "$1" != "@ARGS_PARSED@" ] ; then
    exec g.parser "$0" "$@"
fi


## set environment so that awk works properly in all languages ##
unset LC_ALL
export LC_NUMERIC=C


############################################################
cleanup()
{ 
    g.remove -f type=vect pat="V_TRIANGLE_*" --q
    rm -f $TMP1*
    
}
############################################################
## what to do in case of user break:
exitprocedure()
{
    echo "User break!"
    cleanup
    exit 1
}

## shell check for user break (signal list: trap -l)
trap "exitprocedure" 2 3 15

############################################################
## check for Triangle
if [ ! -x "$(which triangle)" ] ; then
    g.message -e "<Triangle> (http://www.cs.cmu.edu/~quake/triangle.html) required, please install it first."
    exit 1
fi

## check for awk
if [ ! -x "$(which awk)" ] ; then
    g.message -e "<awk> required, please install <awk> or <gawk> first."
    exit 1
fi

## check for sed
if [ ! -x "$(which sed)" ] ; then
    g.message -e "<sed> required, please install it first."
    exit 1
fi

############################################################
## setup temporary files

TMP1="$(g.tempfile pid=$$)"
if [ "$?" -ne 0 ] || [ -z "$TMP1" ] ; then
    g.message -e "ERROR: Unable to create temporary files."
    exit 1
fi

############################################################
# DO IT

## check for Triangle options

if [ -n "$GIS_OPT_MAX_AREA" ] && [ "$GIS_FLAG_A" -eq 0 ]; then
    g.message -e "Use <max_area> option with <"-a" flag>"   
    cleanup
    exit 1
fi

if [ -n "$GIS_OPT_STEINER_POINTS" ] && [ "$GIS_FLAG_S" -eq 0 ]; then
    g.message -e "Use <steiner_points> option with <"-s" flag>"   
    cleanup
    exit 1
fi

if [ -n "$GIS_OPT_MIN_ANGLE" ] && [ "$GIS_FLAG_Q" -eq 0 ]; then
    g.message -e "Use <min_angle> option with <"-q" flag>"   
    cleanup
    exit 1
fi

if [ -n "$GIS_OPT_LINES" ]; then
    if [ "$GIS_FLAG_C" -eq 1 ] && [ $GIS_FLAG_Q -eq 1 -o $GIS_FLAG_A -eq 1 ]; then
    	g.message -e "Flag <"-c"> is not compatible with flags <"-q"> or <"-a">"   
    	cleanup
    	exit 1
    fi
    
    if [ "$GIS_FLAG_I" -eq 1 ] && [ $GIS_FLAG_F -eq 1 ]; then
    	g.message -e "Choose one of these flags: <"-i"> or <"-s">"
    	cleanup
    	exit 1
    fi
    
    if [ $GIS_FLAG_C -eq 1 ]; then
    	FLAG_C="-q0"
    else
    	FLAG_C=""
    fi
    
    if [ "$GIS_FLAG_A" -eq 1 ]; then
    	if [ -n "$GIS_OPT_MAX_AREA" ]; then
    	    FLAG_A="-a${GIS_OPT_MAX_AREA}"
    	else	
    	    g.message -e "To use flag <"-a"> choose <max_area> option"   
    	    cleanup
    	    exit 1
    	fi
    else
    	FLAG_A=""
    fi
    
    if [ "$GIS_FLAG_D" -eq 1 ]; then
    	FLAG_D="-D"
    else
    	FLAG_D=""
    fi

    if [ "$GIS_FLAG_Q" -eq 1 ]; then
    	FLAG_Q="-q -Y"
    	if [ -n "$GIS_OPT_MIN_ANGLE" ]; then
    	    FLAG_Q="-q${GIS_OPT_MIN_ANGLE}"
    	fi
    fi
    
    if [ $GIS_FLAG_L -eq 1 ]; then
    	FLAG_L="-l"
    else
    	FLAG_L=""
    fi

    if [ "$GIS_FLAG_Y" -eq 1 ]; then
    	FLAG_Y="-Y"
    	if [ "$GIS_FLAG_Q" -eq 1 ]; then
    	    FLAG_Y=""
    	fi
    else
    	FLAG_Y=""
    fi

    if [ "$GIS_FLAG_S" -eq 1 ]; then
    	if [ -n "$GIS_OPT_STEINER_POINTS" ]; then
    	    FLAG_S="-S${GIS_OPT_STEINER_POINTS}"
    	else	
    	    g.message -e "To use flag <"-s"> choose <steiner_points> option"   
    	    cleanup
    	    exit 1
    	fi	
    else
    	FLAG_S=""
    fi

    if [ "$GIS_FLAG_I" -eq 1 ]; then
	FLAG_I="-i"
    else
	FLAG_I=""
    fi

    if [ "$GIS_FLAG_F" -eq 1 ]; then
	FLAG_F="-F"
    else
	FLAG_F=""
    fi
    
    TRIANGLE_CMD="triangle -Q -c -p "$FLAG_C" "$FLAG_A" "$FLAG_D" "$FLAG_Q" "$FLAG_L" "$FLAG_Y" "$FLAG_S" "$FLAG_I" "$FLAG_F""
    
# elif [ -z "$GIS_OPT_LINES" ] && [ "$GIS_FLAG_C" -eq 1 -o "$GIS_FLAG_Q" -eq 1 -o "$GIS_FLAG_A" -eq 1 -o "$GIS_FLAG_D" -eq 1 ]; then
# elif [ -z "$GIS_OPT_LINES" ] && [ "$GIS_FLAG_C" -eq 1 -o "$GIS_FLAG_A" -eq 1 -o "$GIS_FLAG_D" -eq 1 ]; then
#     g.message -e "To use flags <"-c">, <"-d">, <"-q">, <"-a"> choose <lines> option"
#     cleanup
#     exit 1
    
else
    TRIANGLE_CMD="triangle -Q -c"
fi

############################################################
## prepare vectors to Triangle input

v.out.ascii format=point in="$GIS_OPT_POINTS" | cut -d'|' -f1-3 | tr '|' ' ' > $TMP1.pts_cut

if [ -n "$GIS_OPT_LINES" ]; then
    v.split in=$GIS_OPT_LINES out=V_TRIANGLE_CUT_SEGM vertices=2 --q --o
    v.category in=V_TRIANGLE_CUT_SEGM out=V_TRIANGLE_CUT_SEGM_NOCATS opt=del --q --o
    v.category in=V_TRIANGLE_CUT_SEGM_NOCATS out=V_TRIANGLE_CUT_SEGM_NEWCATS opt=add --q --o

    v.to.points -t use=vertex in=V_TRIANGLE_CUT_SEGM_NEWCATS out=V_TRIANGLE_CUT_PTS --q --o

    v.out.ascii format=point in=V_TRIANGLE_CUT_PTS | tr '|' ' ' > $TMP1.lines_cut
fi

## make *.node file
 
awk -F' ' '{print $1,$2,$3,"0"}' $TMP1.pts_cut > $TMP1.pts_cut_0

if [ -n "$GIS_OPT_LINES" ]; then
    cat -n $TMP1.lines_cut $TMP1.pts_cut_0  > $TMP1.pts_lines_cut.node.BODY
	# cat -n $TMP1.lines_cut $TMP1.pts_cut_0
else
    # cat -n $TMP1.pts_cut_0
    cat -n $TMP1.pts_cut_0  > $TMP1.pts_lines_cut.node.BODY
fi

VERT_ALL=$(wc -l $TMP1.pts_lines_cut.node.BODY | awk '{print $1}')
echo "$VERT_ALL 2 1 1" > $TMP1.pts_lines_cut.node.HEADER

cat $TMP1.pts_lines_cut.node.HEADER $TMP1.pts_lines_cut.node.BODY > $TMP1.pts_lines_cut.node

## make *.poly file

if [ -n "$GIS_OPT_LINES" ]; then
    echo "0 2 1 1" > $TMP1.pts_lines_cut.poly
    
    LINES_VERT=$(wc -l $TMP1.lines_cut | awk '{print $1}')
    LINES_SEGM=$(($LINES_VERT/2))
    
    echo "$LINES_SEGM 1" >> $TMP1.pts_lines_cut.poly

    cat -n $TMP1.lines_cut  > $TMP1.lines_cut_NUMB

    # cat $TMP1.lines_cut_NUMB
    
    awk '{if (NR%2==1) print $1}' $TMP1.lines_cut_NUMB > $TMP1.lines_cut.1
    awk '{if (NR%2==0) print $1}' $TMP1.lines_cut_NUMB > $TMP1.lines_cut.2

    awk '{print $5}' $TMP1.lines_cut_NUMB | sort -n | uniq > $TMP1.lines_cut.uniq

    paste -d' ' $TMP1.lines_cut.1 $TMP1.lines_cut.2 $TMP1.lines_cut.uniq \
	| cat -n >> $TMP1.pts_lines_cut.poly
    
    echo "0" >> $TMP1.pts_lines_cut.poly
fi


############################################################
## let's triangulate

$TRIANGLE_CMD $TMP1.pts_lines_cut.poly

############################################################
## back from Triangle to GRASS

sed -e '$d' -n -e '2,$p' $TMP1.pts_lines_cut.1.node > $TMP1.pts_lines_cut.1.node.clean

sed -e '$d' -n -e '2,$p' $TMP1.pts_lines_cut.1.ele | awk '{print $1,$2,$3,$4,$2}' > $TMP1.pts_lines_cut.1.ele.clean


awk 'BEGIN{OFS="\n"} {print $2,$3,$4,$5}' \
    $TMP1.pts_lines_cut.1.ele.clean > $TMP1.pts_lines_cut.1.ele.clean.COL

# awk '{i=$1;$1=x} NR==FNR{A[i]=$0;next} A[i]{print i,A[i]$0}' \
#     $TMP1.pts_lines_cut.1.node.clean \
#     $TMP1.pts_lines_cut.1.ele.clean.COL > $TMP1.pts_lines_cut.1.ele.clean.COL.XYZ

awk '{i=$1;$1=x} NR==FNR{A[i]=$0;next} A[i]{print i,A[i]$0}' \
    $TMP1.pts_lines_cut.1.node.clean \
    $TMP1.pts_lines_cut.1.ele.clean.COL \
    | awk '{print $2,$3,$4}' > $TMP1.pts_lines_cut.1.ele.clean.COL.XYZ

echo "B 4" > $TMP1.TIN_to_GRASS

awk 'NR % 4 == 0 {print; print "B 4"; next} {print}' $TMP1.pts_lines_cut.1.ele.clean.COL.XYZ >> $TMP1.TIN_to_GRASS

B="B 4"
EOF="$(sed -n '$p' $TMP1.TIN_to_GRASS)"

if [ "$EOF" = "$B" ]; then
    sed '$d' $TMP1.TIN_to_GRASS > $TMP1.TIN_to_GRASS.clean
fi

## import "raw" TIN in GRASS
v.in.ascii -z -n in=$TMP1.TIN_to_GRASS.clean out=V_TRIANGLE_TIN format=standard sep=' '  --o --q

## cleanup and make areas
v.clean in=V_TRIANGLE_TIN out=V_TRIANGLE_TIN_CLEAN tool=bpol,rmdupl  --o --q
v.centroids in=V_TRIANGLE_TIN_CLEAN out="$GIS_OPT_TIN" --o --q
 
##
## ?? there must be a little hack to make centroids with the right heights ??
##

############################################################
## save Triangle working files if needed
if [ -n "$GIS_OPT_SAVE" ]; then
    if [ -d "$GIS_OPT_SAVE" ]; then
	SAVE_NAME=""$GIS_OPT_POINTS"_"$GIS_OPT_LINES""
	cp $TMP1.pts_lines_cut.node "$GIS_OPT_SAVE"/"$SAVE_NAME".node
	cp $TMP1.pts_lines_cut.poly "$GIS_OPT_SAVE"/"$SAVE_NAME".poly
	cp $TMP1.pts_lines_cut.1.node "$GIS_OPT_SAVE"/"$SAVE_NAME".1.node
	cp $TMP1.pts_lines_cut.1.poly "$GIS_OPT_SAVE"/"$SAVE_NAME".1.poly
	cp $TMP1.pts_lines_cut.1.ele "$GIS_OPT_SAVE"/"$SAVE_NAME".1.ele
    else
	g.message -e ""$GIS_OPT_SAVE" is not a directory or not exists"
	cleanup
	exit 1
    fi
fi

############################################################

cleanup

exit 0
