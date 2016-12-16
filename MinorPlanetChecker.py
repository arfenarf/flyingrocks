from datetime import datetime
import ephem
import pandas as pd
import requests
import BeautifulSoup
import MPCRecord


# v 1.01 by KGW February 2016
# principally aimed at automating the MPC checker form, this takes a batch of observations and
# links, groups them by linkid, and then sends them off to the MPC in small sets
#
# improvements could be made in processing values as they return; providing more feedback as it runs;
# and making it easier to set parameters when called, rather than baking them into the code.

# setup -
# parameterize this if possible

limit = '24.0'
radius = '5'
# orbitfile = 'wsdiff_S82_lon_gt_minus2_orbit.csv' #not currently being used
obsfile = 'wsdiff_S82_lon_gt_minus2_obs.csv'
linkfile = 'wsdiff_S82_lon_gt_minus2_link.csv'

def retrievebatch(observations_in):

    # this function goes to the mpc and executes their mpcheck cgi script.
    # we could make some of the limits parameters of this function
    url = 'http://www.minorplanetcenter.net/cgi-bin/mpcheck.cgi'

    today = datetime.utcnow()
    year = str(today.year)
    month = str(today.strftime("%m"))
    day = str(round(today.day + (float(today.hour) / 24 + float(today.minute) / (24 * 60)), 2))

    payload = "TextArea=" + observations_in + "&day=" + day + "&decl=&limit=" + limit + "&month=" + month + \
              "&mot=h&needed=f&oc=W84&pdes=u&ps=n&ra=&radius=" + radius + "&sort=d&tmot=s&type=p&which=obs&year=" + year

    # cookies (and other headers) taken verbatim from my sniffing tool, probably more than needed
    headers = {
        'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        'origin': "http//www.minorplanetcenter.net",
        'upgrade-insecure-requests': "1",
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) \
        Chrome/48.0.2564.116 Safari/537.36",
        'content-type': "application/x-www-form-urlencoded",
        'referer': "http//www.minorplanetcenter.net/cgi-bin/checkmp.cgi",
        'accept-encoding': "gzip, deflate",
        'accept-language': "en-US,en;q=0.8",
        'cookie': "WT_FPC=id=68.56.146.120-2763983344.30502161lv=1456166666520ss=1456166666520; __utmt=1;\
         __utma=108877598.394446093.1456105075.1456105075.1456166667.2; __utmb=108877598.1.10.1456166667;\
          __utmc=108877598; __utmz=108877598.1456105075.1.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided)"
    }

    response = requests.request("POST", url, data=payload, headers=headers)

    souperoutput = BeautifulSoup.BeautifulSoup(response.text)
    return souperoutput


def parseresponses(souperinput, frame):
    outframe = frame
    resps = souperinput.findAll('pre')
    for index, item in enumerate(resps, start=0):
        if resps[index].text[0:6] == "Object":
            continue
        if index < len(resps) - 1:
            if resps[index + 1].text[0:6] == "Object":
                tmpid = resps[index].text[0:6]
                matches = resps[index + 1].text[204:]
                matches = matches.splitlines()
                # print matches
                matchframe = buildmatch(matches, tmpid)
                outframe = outframe.append(matchframe, ignore_index=True)
                continue
        # so if it all falls out, write a disappointed row
        else:
            tmpid = resps[index].text[0:6]
            matches = ["-" * 125]
            matchframe = buildmatch(matches, tmpid)
            outframe = outframe.append(matchframe, ignore_index=True)

    return outframe


def buildmatch(matches, recid):
    matchframe = pd.DataFrame({'matchtext': matches})

    matchframe['tmpid'] = recid
    matchframe['designation'] = matchframe.matchtext.str[0:25]
    matchframe['mpcRA'] = matchframe.matchtext.str[25:36]
    matchframe['mpcDec'] = matchframe.matchtext.str[36:47]
    matchframe['v'] = matchframe.matchtext.str[47:54]
    matchframe['offsetRA'] = matchframe.matchtext.str[54:61]
    matchframe['offsetDec'] = matchframe.matchtext.str[61:69]
    matchframe['motion_ra'] = matchframe.matchtext.str[69:76]
    matchframe['motion_dec'] = matchframe.matchtext.str[76:81]
    matchframe['orbit'] = matchframe.matchtext.str[81:87]
    matchframe['comment'] = matchframe.matchtext.str[87:]

    del matchframe['matchtext']
    return matchframe


# first we load our data
obss = pd.read_csv(obsfile, parse_dates=['date_obs', 'date_added'])
links = pd.read_csv(linkfile)

# and create a file with the linkid to help us establish batches for MPC.
lobss = pd.merge(links, obss, how='inner', on='objid')

# so we have a short record id to send MPC and tie this back together later
# I must have made this six times harder than it needed to be.

tmpids = pd.Series(lobss.index.values)
tmpids = tmpids.apply(lambda x: str(x))
lobss['tmpid'] = tmpids.str.pad(6, fillchar='0')

# group them by link id
lobs_grouped = lobss.groupby('id')

# set up some basic framework
responseframe = pd.DataFrame(
        columns=['tmpid', 'designation', 'mpcRA', 'mpcDec', 'v', 'offsetRA', 'offsetDec', 'motion_ra',
                 'motion_dec', 'orbit', 'comment'])

responses = responseframe
i = 1
for name, group in lobs_grouped:
    observations = ''
    tempgp = lobs_grouped.get_group(name)
    for ind, row in tempgp.iterrows():
        q = MPCRecord.MPCRecord(MPprovisional=row['tmpid'], obsdate=ephem.date(row['date_obs']),
                                ra_obs_J2000=row['ra'], dec_obs_J2000=row['dec'])
        observations = observations + q.record + '%0A'

    # here we superstitiously remove the trailing line-feed
    observations = observations[:-3]

    # go to mpc with the observations and retrieve a BeautifulSoup object with the responses embedded
    resoup = retrievebatch(observations)

    # parse out the responses into a DataFrame and append to the final output table
    responses = responses.append(parseresponses(resoup, responseframe), ignore_index=True)
    now = datetime.now()
    print "{0}: Batches retrieved: {1}. Total responses: {2}".format(("%s:%s:%s" % (now.hour, now.minute, now.second)),
                                                                     i, len(responses))
    i = i + 1

# now use that tmpid to merge some basic DES data back in
responses = pd.merge(responses, lobss, on='tmpid', how='left')
responsesFinal = responses.loc[:,
                 ['objid', 'id', 'ra', 'dec', 'mag', 'designation', 'mpcRA', 'mpcDec', 'v', 'offsetRA',
                  'offsetDec', 'motion_ra', 'motion_dec', 'orbit', 'comment']]
responsesFinal.to_csv('responsesFinal.csv')
