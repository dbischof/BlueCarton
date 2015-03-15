from collections import defaultdict
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

MAX_KEY_CACHE_AGE = 60 * 5
DATA_CACHE_AGE = 60 * 60

# Community Canvas main page
class CanvasMP(webapp.RequestHandler):
  def get(self):
    import os                                 # Lazy-load only when needed
    from google.appengine.ext.webapp import template
    
    if not self.request.uri.endswith('/'):
      self.redirect(self.request.uri + '/')
      return
  
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, None))
    

# Community Canvas Web Service
class CanvasWS(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/xml'
    self.response.out.write('<?xml version="1.0"?>')
    
    # Get max key
    maxKey = memcache.get("maxKey")
    
    #temp
    if maxKey:
	  self.response.out.write('<!-- before: %i -->' % maxKey)
	
    if maxKey is None:
      squares = CanvasSquare.all().order('-updateKey')
      squares = squares.fetch(1)
      if len(squares) is 1:
        maxKey = squares[0].updateKey
      else:
        maxKey = 0
      memcache.add("maxKey", maxKey, MAX_KEY_CACHE_AGE)
    
    # temp
    if maxKey:
	  self.response.out.write('<!-- after: %i -->' % maxKey)
    
    
    
    # Update value
    id = self.request.get('id')
    if id is not '':
      id = int(id)
      color = int(self.request.get('color'))
      
      #squares = CanvasSquare.all().filter('id =', id)
      #square = squares.get()
      
      key = "square_%i" % id
      #square = CanvasSquare.get_by_key_name(key)
      #if square is None:
      #  square = CanvasSquare(key_name=key, id=id)
      #
      #square.color = color
      
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
      if updateKey is '' or int(updateKey) is not maxKey:
      
        squaresCache = defaultdict(int)
        
        squares = CanvasSquare.all()
        if updateKey is not '':
          squares.filter('updateKey >', int(updateKey))
      
        for square in squares:
          self.response.out.write('<square id="%s" color="%s"/>' % (square.id, square.color))
          #self.response.out.write('<square id="%s" color="%s" key="%s"/>' % (square.id, square.color, square.updateKey))
          
          squaresCache[square.id] = square.color
        
        memcache.add("squares", squaresCache, DATA_CACHE_AGE)
    
      self.response.out.write('</squares>')


# Community Canavs data store
class CanvasSquare(db.Model):
  id = db.IntegerProperty(required=True)
  color = db.IntegerProperty(required=True, default=0)
  updateKey = db.IntegerProperty(required=True, default=1)


def main():
  application = webapp.WSGIApplication(
                                       [('/canvas', CanvasMP),
                                        ('/canvas/', CanvasMP),
                                        ('/canvas/ws', CanvasWS)],
                                       debug=False)
  run_wsgi_app(application)

if __name__ == "__main__":
  main()