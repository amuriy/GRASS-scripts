#!/usr/bin/env python

import sys
from vtk import vtkGenericDataObjectReader, vtkPLYWriter

infile = sys.argv[1]
outfile = sys.argv[2]

reader = vtkGenericDataObjectReader()
reader.SetFileName(infile)
reader.Update()
writer = vtkPLYWriter()
writer.SetInputConnection(reader.GetOutputPort())
writer.SetFileName(outfile)
writer.Write()

