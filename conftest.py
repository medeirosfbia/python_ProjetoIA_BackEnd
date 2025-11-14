import pytest
from dotenv import load_dotenv
from app import app

load_dotenv()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client