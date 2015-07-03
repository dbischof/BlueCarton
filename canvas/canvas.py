from collections import defaultdict
from google.appengine.api import memcache
from google.appengine.ext import db

import webapp2

MAX_KEY_CACHE_AGE = 60 * 5
DATA_CACHE_AGE = 60 * 60

# Community Canvas main page
class CanvasMP(webapp2.RequestHandler):
  def get(self):
    import os                                 # Lazy-load only when needed
    from google.appengine.ext.webapp import template
    
    if not self.request.uri.endswith('/'):
      self.redirect(self.request.uri + '/')
      return
  
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, None))
    

# Community Canvas Web Service
class CanvasWS(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/xml'
    self.response.out.write('<?xml version="1.0"?>')

    squares = memcache.get("squares")
    if squares:
      # cache hit
      maxKey = memcache.get("maxKey")
      if not maxKey:
        # cache miss
        squares = None
    
    if not squares:
      #cache miss
      squares = defaultdict(int)
      maxKey = 0
      
      storedSquares = CanvasSquare.all()
      for square in storedSquares:
        squares[square.id] = square.color
        if square.updateKey > maxKey:
          maxKey = square.updateKey
      
      memcache.add("squares", squares, DATA_CACHE_AGE)
      memcache.add("maxKey", maxKey, MAX_KEY_CACHE_AGE)
    
    # Update value
    id = self.request.get('id')
    if id is not '':
      id = int(id)
      color = int(self.request.get('color'))
      
      key = "square_%i" % id
      
      squares[id] = color
      memcache.set("squares", squares, DATA_CACHE_AGE)
      
      # Don't waste a datastore read, just override it
      square = CanvasSquare(key_name=key, id=id, color=color)
      
      newMaxKey = maxKey + 1
      if newMaxKey > maxKey:
        square.updateKey = newMaxKey
        square.put()
      else:                                   # Integer rollover
        square.put()
        newMaxKey = 1
        squares = CanvasSquare.all()
        for square in squares:
          square.updateKey = newMaxKey
          square.put()
      
      self.response.out.write('<success/>')
      memcache.set("maxKey", newMaxKey, MAX_KEY_CACHE_AGE)
    
    # Get current values
    else:    
      self.response.out.write('<squares key="%s">' % maxKey)
      
      updateKey = self.request.get('key')
      if updateKey is '' or int(updateKey) != maxKey:
        #todo: filter by updateKey; might not be needed as bandwidth use looks ok

        for id, color in squares.items():
          self.response.out.write('<square id="%s" color="%s"/>' % (id, color))
      
      self.response.out.write('</squares>')


# Community Canavs data store
class CanvasSquare(db.Model):
  id = db.IntegerProperty(required=True)
  color = db.IntegerProperty(required=True, default=0)
  updateKey = db.IntegerProperty(required=True, default=1)


app = webapp2.WSGIApplication(
                              [('/canvas', CanvasMP),
                               ('/canvas/', CanvasMP),
                               ('/canvas/ws', CanvasWS)],
                              debug=False
                             )
