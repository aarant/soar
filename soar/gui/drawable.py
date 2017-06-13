class Drawable:
    """ A base drawable class designed for use with Tk """
    def __init__(self, **options):
        self.options = options
        if 'tags' in options:
            self.tags = options['tags']
        else:
            self.tags = 'all'

    def draw(self, canvas):
        raise NotImplementedError

    def delete(self, canvas):
        canvas.delete(self.tags)
