#!/bin/sh

VECT=$1

if [ $(g.proj -j | grep "longlat") ]; then
    d.where -d -l --q > .coords.list 
    cat .coords.list | while read line; do 
	echo $line | sed -e 's/     /,/g' -e 's/ /,/g' | tr -d [[:alpha:]] >> .coords_koma.list 
    done
else
    d.where --q > .coords.list 
    cat .coords.list | while read line; do 
	echo $line | sed -e 's/     /,/g' -e 's/ /,/g' >> .coords_koma.list 
    done
fi

line_1st=$(cat .coords_koma.list | head -n1)
line_last=$(cat .coords_koma.list | tail -n1)

grep -v -- "${line_last}" .coords_koma.list > .coords.clean

line_count=$(cat .coords_koma.list | wc -l)
if [ $line_count -le "2" ]; then
    polygon_coords=$(cat .coords.clean | tr '\n' ','; echo "$line_last"","$line_1st"")
else
    polygon_coords=$(cat .coords.clean | tr '\n' ','; echo $line_last)
fi


# echo "color 255:255:150
# polygon" > .coords.graph
# cat .coords_koma.list >> .coords.graph
# cat .coords.graph | tr ',' ' ' > .graph.clean
# d.graph -m input=.graph.clean

# d.save move=1,2 > /dev/null 2>&1




list=$(v.edit $VECT tool=select polygon=$(echo $polygon_coords) --q)


#list=$(v.edit $VECT tool=select bbox=$(echo $polygon_coords) --q)
echo $list

#d.vect -i $1 cats=$list width=3 col=red

#v.edit $VECT tool=delete ids=$list --q



rm -f .coords* .graph.clean

##############################
#v.extract in=VECT_to_select type=line list=$list new=$1 out=??? --o

#v.edit VECT_to_select tool=merge cats=1-999999
