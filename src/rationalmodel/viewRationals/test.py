import freetype
from madcad.rendering import show
from madcad.text import triangulation, character_primitives

face = freetype.Face('c:/python310/Lib/site-packages/madcad/NotoMono-Regular.ttf')
face.set_char_size(1024)
face.load_char('&')
show([ triangulation(character_primitives(face)) ])
