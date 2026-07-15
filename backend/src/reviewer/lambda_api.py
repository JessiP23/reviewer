from mangum import Mangum

from reviewer.main import app

handler = Mangum(app, lifespan="auto")

