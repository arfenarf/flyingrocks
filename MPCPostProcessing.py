import ephem
import pandas as pd
import numpy as np

# a simple framework for calculating the separation between the DES object's ra/dec and the
# matched object.  Returns an angle in radians in 'distance', which is appended as a new col
# in the table.
# this routine could be improved by doing transforms of more columns to
# numeric from their current string form.

responses = pd.read_csv('responsesFinal.csv', index_col=0)

def dist(dr, dd, mr, md):
    if mr.find('-') == 0:
        return 0
    a = ephem.Equatorial(dr, dd)
    b = ephem.Equatorial(mr, md)
    distance = ephem.separation(a.get(), b.get())
    return distance


responses['distance'] = responses.apply(lambda row: dist(row['ra'], row['dec'], row['mpcRA'], row['mpcDec']), axis=1)

pd.pivot_table(
        responses,
        index=['designation'],
        values=['distance'], aggfunc=[np.mean, len])  # data values in this column become their own column

responses.to_csv('responsesFinal.csv')
