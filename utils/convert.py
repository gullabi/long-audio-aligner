import os
import json
from copy import deepcopy

FILE = 'test/parlament_processed_sessions_sh.json'
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
                    print('%s not found'%value['urls'][0][1])
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
    if os.path.isfile(uri):
        return uri
    else:
        return None

def get_new_key(ple_code, uri):
    no = os.path.basename(uri).split('.')[0]
    if not no:
        msg = 'smt wrong with uri %s'%uri
        raise ValueError(msg)
    return '_'.join([ple_code, no])

if __name__ == "__main__":
    main()
