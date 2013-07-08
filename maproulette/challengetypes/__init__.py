import glob
import os
filepath = os.path.realpath(__file__)
dirname = os.path.dirname(filepath)
files = glob.glob(os.path.join(os.path.join(dirname, "*.py")))
files = [os.path.basename(f) for f in files] 
files.remove('__init__.py')
files = [os.path.join(dirname, f) for f in files]
for f in files:
    execfile(f)
