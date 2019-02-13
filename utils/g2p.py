import json
import re
import subprocess

class G2P(object):
    '''
    Poor person's grapheme to phoneme decoder using espeak.

    Currently hardcoded for catalan, and is not efficient, i.e. not 
    suggested for large processes
    '''
    def __init__(self):
        self.e2c = json.load(open('utils/espeak2cmu.json'))
        self.re_stress = re.compile('ˈ|ˌ')
        self.cmd = "espeak -vca '%s' --ipa=3 -q"

    def decode(self, string):
        process = subprocess.Popen((self.cmd%string).split(),
                                   stdout=subprocess.PIPE)
        b = process.stdout.read()
        raw_result = b.decode('utf8').strip()

        # remove stress
        raw_result = self.re_stress.sub('', raw_result)

        # adhoc espeak cleaning for catalan
        raw_result = raw_result.replace('aɪ','a_j').replace(' ','_')
        ipa_phonemes = raw_result.split('_')
        cmu_phonemes = [self.e2c[phoneme] for phoneme in ipa_phonemes]
        return ' '.join(cmu_phonemes)
