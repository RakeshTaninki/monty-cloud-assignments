from mangum import Mangum

from src.main import app

lambda_handler = Mangum(app)
