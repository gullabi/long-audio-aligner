import os
import json
import logging
from copy import deepcopy
from subprocess import call, check_output, DEVNULL
from retrying import retry

FILE = 'test/parlament_processed_sessions.json'
BASE = '../parlament-scrape/audio'

def main():
    basepath = BASE
    sessions = json.load(open(FILE))
    interventions = {}
    for ple_code, session in sessions.items():
        for yaml, value in session.items():
            if len(value['urls']) > 1:
                print("%s multiple audio file, skipping"%value['urls'])
            else:
                uri = get_uri(value['urls'][0][1], basepath)
                if not uri:
                    print('%s still not found'%value['urls'][0][1])
                value['urls'][0][1] = uri
                value['source'] = yaml
                new_value = deepcopy(value)
                new_key = get_new_key(ple_code, yaml)
                if interventions.get(new_key):
                    raise KeyError('%s already exists'%new_key)
                new_value['ple_code'] = ple_code
                interventions[new_key] = new_value

    with open(FILE.replace('.json', '_local02.json'), 'w') as out:
        json.dump(interventions, out, indent=4)

def get_uri(url, basepath):
    basename = os.path.basename(url)
    uri = os.path.abspath(os.path.join(basepath,
                                       basename[0],
                                       basename[1],
                                       basename))
    if not os.path.isfile(uri):
        logging.info('attempting to download %s'%url)
        curl_download(url, uri)
    if os.path.isfile(uri):
        return uri
    else:
        return None

@retry(stop_max_attempt_number=3, wait_fixed=1000)
def curl_download(uri, filepath):
    msg = 'checking %s'%uri
    logging.info(msg)
    # check the http headers
    status, uri = get_status_code(uri)
    if status == 302:
        # redirect uri should have been extracted to the uri variable
        status, uri = get_status_code(uri)
    if status != 200:
        error = 'the resource in the url %s cannot be reached'\
                              ' with status %i.'%(uri,status)
        logging.error(error)
        if status == 401:
            return None
        else:
            raise ConnectionError(error)

    # create file
    with open(filepath,'w') as fout:
        cmd = ['curl','-g',uri]
        logging.info("downloading %s"%uri)
        call(cmd, stdout=fout, stderr=DEVNULL) #seems dangerous but 404s are
                                               #caught by the get_status_code
def get_status_code(url):
    cmd = ['curl','-I',url]
    header = check_output(cmd, stderr=DEVNULL)
    header_list = header.split(b'\n')
    code = int(header_list[0].split()[1])
    uri = url
    if code == 302:
        for h in header_list:
            if h.startswith(b'Location: '):
                uri = h.strip().decode('ascii')[10:]
                if 'http' not in uri:
                    code = 401
    return code, uri

def get_new_key(ple_code, uri):
    no = os.path.basename(uri).split('.')[0]
    if not no:
        msg = 'smt wrong with uri %s'%uri
        raise ValueError(msg)
    return '_'.join([ple_code, no])

if __name__ == "__main__":
    main()
