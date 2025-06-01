import redis
import json
from datetime import datetime

class RedisMemory:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)
        
    def store_document_data(self, conversation_id, source, format_type, intent, extracted_data):
        """Store document processing data in Redis"""
        data = {
            "source": source,
            "format": format_type,
            "intent": intent,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "extracted_data": json.dumps(extracted_data)
        }
        
        key = f"doc:{conversation_id}"
        self.redis_client.hmset(key, {k: json.dumps(v) if isinstance(v, dict) else v for k, v in data.items()})
        
    def get_document_data(self, conversation_id):
        """Retrieve document data from Redis"""
        key = f"doc:{conversation_id}"
        data = self.redis_client.hgetall(key)
        
        if not data:
            return None
            
        # Convert bytes to strings and parse JSON fields
        result = {}
        for k, v in data.items():
            k_str = k.decode('utf-8') if isinstance(k, bytes) else k
            v_str = v.decode('utf-8') if isinstance(v, bytes) else v
            
            # Parse JSON fields
            if k_str == "extracted_data":
                try:
                    result[k_str] = json.loads(v_str)
                except json.JSONDecodeError:
                    result[k_str] = v_str
            else:
                result[k_str] = v_str
                
        return result
        
    def list_all_documents(self):
        """List all document keys in Redis"""
        keys = self.redis_client.keys("doc:*")
        return [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]