import subprocess
import numpy as np
import pandas as pd
from pyLPM import plots

#############################################################################################################

def call_program(program, parfile, usewine=False):
    if usewine == True:
        p = subprocess.Popen(['wine', program, parfile], stdout=subprocess.PIPE)
    else:
         p = subprocess.Popen([program, parfile], stdout=subprocess.PIPE)

    for line in p.stdout:    
        print(line.decode('utf-8'), end='')

def write_GeoEAS(df,dh,x,y,z,vars=[]):
    df.replace(float('nan'),-999,inplace=True)
    columns = []
    if dh != None:
        columns.append(dh)
    columns.append(x)
    columns.append(y)
    if z != None:
        columns.append(z)
    for var in vars:
        columns.append(var)
    data = ""
    data= data +'tmp_pygslib_file\n'
    data= data + str(len(columns))+'\n'
    for col in columns:
        data=data + col+'\n'
    values = df[columns].to_string(header=False, index=False)
    data= data + values+'\n'
    f = open('pyLPM/gslib90/tmp/tmp.dat', 'w')
    f.write(data)
    f.close()

def read_GeoEAS(file):
    f = open(file, 'r')
    col_names = []
    results = []
    
    for index, line in enumerate(f):
    	if index == 0:
    		continue
    	elif index == 1:
    		n_cols = int(line.split()[0])
    	elif index <= n_cols+1:
    		col_names.append(line[:-1])
    	else:
    		values = [float(i) for i in line.split()]
    		results.append(values)

    f.close()

    return pd.DataFrame(results, columns = col_names)

def col_number(file, col):
    f = open(file, 'r')
    col_names = []
    
    for index, line in enumerate(f):
    	if index == 0:
    		continue
    	elif index == 1:
    		n_cols = int(line)
    	elif index <= n_cols+1:
    		col_names.append(line[:-1])

    return col_names.index(col) + 1 if col is not None else 0

def write_varg_str(varg):
    if 'nugget' in varg:
        nst = len(varg) - 1
        nugget = varg['nugget']
    else:
        nst = len(varg)
        nugget = 0
    
    var_str = '{} {} \n'.format(nst, nugget)
    
    for struct in varg:
        if struct is not 'nugget':
            if struct is 'spherical':
                it = 1
            elif struct is 'exponetial':
                it = 2
            elif struct is 'gaussian':
                it = 3

            new_lines = '{} {} {} {} {} \n {} {} {}'.format(it, varg[struct]['cc'], varg[struct]['a1'], varg[struct]['a2'], varg[struct]['a3'], varg[struct]['r1'], varg[struct]['r2'], varg[struct]['r3'])

            var_str = var_str + new_lines
        
    return var_str

#############################################################################################################

def declus(df, x, y, z, var, tmin=-1.0e21, tmax=1.0e21, summary_file='pyLPM/gslib90/tmp/tmpsum.dat', output_file='pyLPM/gslib90/tmp/tmpfile.dat', x_anis=1, z_anis=1, n_cell=10, min_size=1, max_size=20, keep_min = True, number_offsets=4, usewine=False):

    write_GeoEAS(df=df,dh=None,x=x,y=y,z=z,vars=[var])
    
    decluspar = '''
                    Parameters for CELLDECLUS
                                  Parameters for DECLUS
                  *********************

START OF PARAMETERS:
{datafile}         -file with data
{x}   {y}   {z}   {var}               -  columns for X, Y, Z, and variable
{tmin}     {tmax}          -  trimming limits
{sum}                  -file for summary output
{out}                  -file for output with data & weights
{xanis}   {zanis}                   -Y and Z cell anisotropy (Ysize=size*Yanis)
{kmin}                           -0=look for minimum declustered mean (1=max)
{ncell}  {min}  {max}               -number of cell sizes, min size, max size
{noff}                           -number of origin offsets
'''
    map_dict = {
        'datafile':'pyLPM/gslib90/tmp/tmp.dat',
        'x':col_number('pyLPM/gslib90/tmp/tmp.dat', x),
        'y':col_number('pyLPM/gslib90/tmp/tmp.dat', y),
        'z':col_number('pyLPM/gslib90/tmp/tmp.dat', z),
        'var':col_number('pyLPM/gslib90/tmp/tmp.dat', var),
        'tmin':str(tmin),
        'tmax':str(tmax),
        'sum':summary_file,
        'out':output_file,
        'xanis':str(x_anis),
        'zanis':str(z_anis),
        'ncell':str(n_cell),
        'min':str(min_size),
        'max':str(max_size),
        'kmin': -1 if keep_min == True else 0,
        'noff':str(number_offsets)
    }

    formatted_str = decluspar.format(**map_dict)
    parfile = 'pyLPM/gslib90/tmp/partmp.par'
    f = open(parfile, 'w')
    f.write(formatted_str)
    f.close()
    program = "pyLPM/gslib90/declus.exe"

    call_program(program, parfile, usewine)

    df1 = read_GeoEAS(summary_file)
    plots.cell_declus_sum(df1['Cell Size'],df1['Declustered Mean'])
    df2 = read_GeoEAS(output_file)
    df['Declustering Weight'] = df2['Declustering Weight']

def kt3d(df, dh, x, y, z, var, grid, variogram, min_samples, max_samples, max_oct, search_radius, search_ang = [0,0,0], discretization = [5,5,1], krig_type='OK', sk_mean = 0, tmin=-1.0e21, tmax=1.0e21, option='grid', debug_level=0, debug_file='pyLPM/gslib90/tmp/debug.out', output_file='pyLPM/gslib90/tmp/output.out',usewine=False):

    write_GeoEAS(df=df,dh=dh,x=x,y=y,z=z,vars=[var])

    kt3dpar = '''
                      Parameters for KT3D
                  *******************

START OF PARAMETERS:
{datafile}              -file with data
{dh}  {x}  {y}  {z}  {var}  0                 -   columns for DH,X,Y,Z,var,sec var
{tmin}   {tmax}                 -   trimming limits
{option}                                -option: 0=grid, 1=cross, 2=jackknife
{datafile}                          -file with jackknife data
{x}   {y}   {z}    {var}    0              -   columns for X,Y,Z,vr and sec var
{debug}                                -debugging level: 0,1,2,3
{debugout}                         -file for debugging output
{kt3dout}                         -file for kriged output
{nx}   {ox}    {sx}                  -nx,xmn,xsiz
{ny}   {oy}    {sy}                  -ny,ymn,ysiz
{nz}    {oz}    {sz}                  -nz,zmn,zsiz
{dx}    {dy}      {dz}                    -x,y and z block discretization
{min}    {max}                           -min, max data for kriging
{max_oct}                                -max per octant (0-> not used)
{r1}  {r2}  {r3}                 -maximum search radii
 {a1}   {a2}   {a3}                 -angles for search ellipsoid
{krig_type}     {mean}                      -0=SK,1=OK,2=non-st SK,3=exdrift
0 0 0 0 0 0 0 0 0                -drift: x,y,z,xx,yy,zz,xy,xz,zy
0                                -0, variable; 1, estimate trend
extdrift.dat                     -gridded file with drift/mean
4                                -  column number in gridded file
{varg}'''

    map_dict = {
        'datafile':'pyLPM/gslib90/tmp/tmp.dat',
        'dh': col_number('pyLPM/gslib90/tmp/tmp.dat', dh),
        'x': col_number('pyLPM/gslib90/tmp/tmp.dat', x),
        'y': col_number('pyLPM/gslib90/tmp/tmp.dat', y),
        'z':col_number('pyLPM/gslib90/tmp/tmp.dat', z),
        'var':col_number('pyLPM/gslib90/tmp/tmp.dat', var),
        'tmin':str(tmin),
        'tmax':str(tmax),
        'option': 0 if option is 'grid' else 1 if option is 'cross' else 2,
        'debug':debug_level,
        'debugout':debug_file,
        'kt3dout':output_file,
        'nx':grid['nx'],
        'ny':grid['ny'],
        'nz':grid['nz'],
        'ox':grid['ox'],
        'oy':grid['oy'],
        'oz':grid['oz'],
        'sx':grid['sx'],
        'sy':grid['sy'],
        'sz':grid['sz'],
        'dx':discretization[0],
        'dy':discretization[1],
        'dz':discretization[2],
        'min':min_samples,
        'max':max_samples,
        'max_oct':max_oct,
        'r1':search_radius[0],
        'r2':search_radius[1],
        'r3':search_radius[2],
        'a1':search_ang[0],
        'a2':search_ang[1],
        'a3':search_ang[2],
        'krig_type':0 if krig_type is 'SK' else 0,
        'mean':sk_mean,
        'varg':write_varg_str(variogram)
    }

    formatted_str = kt3dpar.format(**map_dict)
    parfile = 'pyLPM/gslib90/tmp/partmp.par'
    f = open(parfile, 'w')
    f.write(formatted_str)
    f.close()
    program = "pyLPM/gslib90/kt3d.exe"

    call_program(program, parfile, usewine)

    if option is 'grid':

        df1 = read_GeoEAS(output_file)
        return df1['Estimate'], df1['EstimationVariance']

    if option is 'cross' or option is 'jackknife':

        df1 = read_GeoEAS(output_file)
        print(df1.head())
        real, estimate, error = df1['True'], df1['Estimate'], df1['Error: est-true']
        plots.xval(real, estimate, error, x_axis='True', y_axis='False', pointsize=8, figsize=(500,900))

