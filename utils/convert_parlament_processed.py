import os
import json

FILE = 'test/parlament_processed_sessions_sh.json'
BASE = '../parlament-scrape/audio'

def main():
    basepath = BASE
    sessions = json.load(open(FILE))
    for ple_code, session in sessions.items():
        for yaml, value in session.items():
            if len(value['urls']) > 1:
                print("%s multiple audio file, skipping"%value['urls'])
            else:
                uri = get_uri(value['urls'][0][1], basepath)
                if not uri:
                    print('%s not found'%value['urls'][0][1])
                value['urls'][0][1] = uri
    with open(FILE.replace('.json', '_local.json'), 'w') as out:
        json.dump(sessions, out, indent=4)

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

if __name__ == "__main__":
    main()
