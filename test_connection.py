import os
import sys
import logging
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('connection_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    try:
        # Load MongoDB URI from environment
        load_dotenv()
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test the connection
        client.admin.command('ping')
        
        # Get database and collection references
        db = client["healthbot"]
        test_collection = db["connection_test"]
        
        # Test write operation
        test_doc = {
            "test_id": "connection_test",
            "timestamp": datetime.utcnow(),
            "status": "testing"
        }
        insert_result = test_collection.insert_one(test_doc)
        
        # Test read operation
        read_result = test_collection.find_one({"test_id": "connection_test"})
        
        # Test update operation
        update_result = test_collection.update_one(
            {"test_id": "connection_test"},
            {"$set": {"status": "completed"}}
        )
        
        # Clean up test document
        test_collection.delete_one({"test_id": "connection_test"})
        
        logger.info("✅ MongoDB connection and operations test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection test failed: {str(e)}")
        return False

def test_openrouter_connection():
    """Test OpenRouter API connection"""
    try:
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            logger.error("❌ OpenRouter API key not found in environment variables")
            return False
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "HealthBot"
        }
        
        # Test API endpoint
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("✅ OpenRouter API connection test passed")
            return True
        else:
            logger.error(f"❌ OpenRouter API test failed with status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ OpenRouter API connection test failed: {str(e)}")
        return False

def test_file_permissions():
    """Test file permissions for logs and static files"""
    try:
        # Test log file writing
        with open('app.log', 'a') as f:
            f.write(f"Test log entry - {datetime.now()}\n")
            
        # Test static directory access
        if not os.path.exists('static'):
            os.makedirs('static')
            
        if not os.path.exists('templates'):
            os.makedirs('templates')
            
        logger.info("✅ File permissions test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ File permissions test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all connection tests"""
    logger.info("🔄 Starting connection tests...")
    
    results = {
        "mongodb": test_mongodb_connection(),
        "openrouter": test_openrouter_connection(),
        "file_permissions": test_file_permissions()
    }
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test}: {status}")
    
    return all(results.values())

if __name__ == "__main__":
    success = run_all_tests()
    if success:
        logger.info("🎉 All connection tests passed!")
        sys.exit(0)
    else:
        logger.error("⚠️ Some tests failed. Please check the logs for details.")
        sys.exit(1) 