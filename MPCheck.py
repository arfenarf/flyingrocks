#!/usr/bin/env python

# Start of a script to call MPChecker
# Based on http://www.pythonforbeginners.com/cheatsheet/python-mechanize-cheat-sheet

import mechanize
from bs4 import BeautifulSoup
import sys
import ephem

br = mechanize.Browser()
br.set_handle_robots(False)
br.set_handle_equiv(False)
br.addheaders = [('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36')]
br.open('http://www.minorplanetcenter.net/cgi-bin/checkmp.cgi')
br.form = list(br.forms())[1]
#for control in br.form.controls:   # this finds all the controls
#    print control, control.type, control.name
# Next is where we enter values for the text controls: year, month, day, ra, dec, etc.
#
date_obs = sys.argv[-4]
time_obs = sys.argv[-3]
ra = sys.argv[-2]
dec = sys.argv[-1]
year = date_obs.split('/')[-3]
month = date_obs.split('/')[-2]
day = date_obs.split('/')[-1]
d = ephem.date(date_obs + ' '+time_obs)
d_frac = d-int(d)-0.5
dd = str(float(day)+d_frac)


br['year']='2013'
br['month'] = '09'
br['day'] = '24.22'
br['ra'] = '02 47 55.45'
br['decl'] = '+00 05 50.9'
br['oc'] = 'W84'
br['radius'] = '5'
br['limit'] = '24'
response = br.submit()
resp =  response.read()
br.back()   # go back

soup = BeautifulSoup(resp)
if soup.body.pre is not None:
    for line in soup.body.pre:
        print line
else:
    print 'Nobody home.'
