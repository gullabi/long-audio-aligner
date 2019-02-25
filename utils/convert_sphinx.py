import os
import re
import sys
import json

SPHINX_LINE = re.compile('^\<s\> (.+) \</s\>( \(.+\)$)')

def main(f_transcript, f_fileid, basepath):
    segment_list = check_input(f_transcript, f_fileid)
    segments = put_files(segment_list, basepath)

    with open('test.json', 'w') as out:
        json.dump(segments, out, indent=2)

def check_input(f_transcript, f_fileid):
    transcripts = []
    for line in open(f_transcript).readlines():
        match = SPHINX_LINE.search(line)
        if not match:
            msg = 'line does not have CMU Sphinx format\n%s'%line
            raise IOError(msg)
        text, f_id = match.groups()
        transcripts.append((text, f_id[2:-1]))

    segment_list = []
    for i, line in enumerate(open(f_fileid).readlines()):
        if transcripts[i][1] not in line:
            msg = 'problem with sphinx format\n%s not in %s'\
                  %(transcripts[i][1], line)
            raise IOError(msg) 
        segment_list.append((transcripts[i][0],
                            transcripts[i][1],
                            line.strip()))

    if len(segment_list) != len(transcripts):
        msg = "size of transcripts vs file_ids is not the same"
        raise ValueError(msg)
    return segment_list

def put_files(segment_list, basepath):
    segments = {}
    for s in segment_list:
        target_path = os.path.abspath(os.path.join(basepath, s[2])+'.wav')
        if not os.path.isfile(target_path):
            msg = '%s does not exist'%target_path
            raise IOError(msg)
        if segments.get(s[1]):
            raise ValueError('%s not unique'%s[1])
        segments[s[1]] = {'words': s[0],
                          'segment_path': target_path}
    return segments

if __name__=="__main__":
    f_transcript = sys.argv[1]
    f_fileid = sys.argv[2]
    basepath = sys.argv[3]

    for p in [f_transcript, f_fileid, basepath]:
        if not os.path.exists(p):
            raise IOError('%s does not exist'%p)

    main(f_transcript, f_fileid, basepath)
