import os
import json

config_file = 'config.json'


class Config:
    def __init__(self):
        self.values = {
            'image_path': '',
            'video_path': '',
            'ffmpeg_path': '',
            'image_resx': 1920,
            'image_resy': 1080,
            'video_codec': 'prores',
            'video_format': 'mov',
            'frame_rate': 1,
            'frame_rate_accum': 0.5,
            'bit_rate': '20M',
            'colors': [
                {'alpha': 0.0, 'color': [0.2, 0.2, 1.0]},
                {'alpha': 0.5, 'color': [0.3, 0.6, 0.5]},
                {'alpha': 1.0, 'color': [1.0, 0.5, 0.2]}
            ],
            'rad_factor': 8.0,
            'rad_pow': 0.8,
            'rad_factor_accum': 2.3,
            'rad_pow_accum': 0.3,
            'rad_min': 0.02,
            'max_faces': 20,
            'faces_pow': 0.2,
            'histogram_resx': 200,
            'histogram_resy': 50,
            'histogram_max': 10000,
            'histogram_y_factor': 0.5,
            'objects_key': 1
        }
        if os.path.exists(config_file):
            with open(config_file, 'rt') as fp:
                values = json.load(fp)
                for key in values.keys():
                    if key in self.values:
                        self.values[key] = values[key]

    def get(self, key: str):
        if key in self.values:
            return self.values[key]
        return ''
    
    def getKey(self):
        key = self.values['objects_key']
        self.values['objects_key'] += 1
        return key
    
    def resetKey(self):
        self.values['objects_key'] = 1
