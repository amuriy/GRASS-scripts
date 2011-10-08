#!/bin/sh

d.where --q > .coords.list 

cat .coords.list | while read line; do 
    echo $line | sed -e 's/     /,/g' -e 's/ /,/g' >> .coords_koma.list 
done

line_1st=$(cat .coords_koma.list | head -n1)
line_last=$(cat .coords_koma.list | tail -n1)

grep -v $line_last .coords_koma.list > .coords.clean


line_count=$(cat .coords_koma.list | wc -l)
if [ $line_count -le "2" ]; then
    polygon_coords=$(cat .coords.clean | tr '\n' ','; echo "$line_last"","$line_1st"")
else
    polygon_coords=$(cat .coords.clean | tr '\n' ','; echo $line_last)
fi


echo " ------------------------------ "
echo $polygon_coords


echo "color 255:255:150
polygon" > .coords.graph
cat .coords_koma.list >> .coords.graph
cat .coords.graph | tr ',' ' ' > .graph.clean
d.graph -m input=.graph.clean


rm -f .coords*


list=$(v.edit Mzymta_reki_merged_clean tool=select polygon=$(echo $polygon_coords) --q)


#list=$(v.edit Mzymta_reki_merged_clean tool=select bbox=$(echo $polygon_coords) --q)
echo " -------------------- "
echo $list
echo ""

d.save move=1,2 > /dev/null 2>&1

#v.extract in=paleorusla_Qe_voronoi type=line list=$list new=$1 out=paleorusla_Qe_voronoi_$1 --o

#v.edit paleorusla_Qe_voronoi_$1 tool=merge cats=1-999999
