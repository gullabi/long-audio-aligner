import json
import os
import subprocess
from math import floor

def segment_cue(audio, cue, audio_tool='ffmpeg'):
        seek = floor(cue['start'])
        start = cue['start'] - seek
        end = cue['end']
        duration = end - cue['start']
        cue['segment'] = '_'.join([audio.split('.')[0], str(cue['start']), str(cue['end'])])
        cue['segment_path'] = os.path.join('./', cue['segment'])+'.wav'
        args = [audio_tool, '-hide_banner', '-loglevel', 'panic',\
                '-ss', str(seek), '-i', audio, '-ss', str(start), \
                '-t', str(duration), '-ac', '1', '-ar', '16000', cue['segment_path']]
        if os.path.isfile(cue['segment_path']):
            print("%s already exists skipping"%cue['segment'])
        else:
            print(' '.join(args))
            subprocess.call(args)   
            if not os.path.isfile(cue['segment_path']):
                raise IOError("File not created from ffmpeg(avconv) operation"
                              " %s"%cue['segment_path'])

aligned = json.load(open('../tmp/c3d9d2a15a76a9fbb591_align.json'))
diffs = []
for i, element in enumerate(aligned):
    if i < len(aligned)-1:
        next_element = aligned[i+1]
        if element.get('end') and next_element.get('start'):
            diffs.append((float(next_element['start'])-float(element['end'])))

start_index = [i for i, a in enumerate(aligned) if a.get('start')][0]
cropped_aligned = aligned[start_index:]
sentences = []
sentence = {'words': '', 'start':cropped_aligned[0]['start']}
for i, element in enumerate(cropped_aligned):
    if i < len(cropped_aligned)-1:
        sentence['words'] += element['word']+' '
        next_element = cropped_aligned[i+1]
        if element.get('end') and next_element.get('start'):
            if (float(next_element['start'])-float(element['end'])) > 0.099:
                sentence['end'] = element['end']
                sentences.append(sentence)
                sentence = {'words': '', 'start':next_element['start']}
    else:
        sentence['words'] += element['word']
        sentence['end'] = element['end']
        sentences.append(sentence)

for s in sentences:
    if (float(s['end']) - float(s['start'])) > 15.:
        print('smt')
    print(s)
    segment_cue('c3d9d2a15a76a9fbb591.mp3', s)
