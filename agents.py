import json
import re
import PyPDF2
import io
import google.generativeai as genai

class ClassifierAgent:
    def __init__(self, model):
        self.model = model
        
    def classify_document(self, file_content, file_name):
        """Classify document format and intent"""
        # Determine format based on file extension
        format_type = self._detect_format(file_name, file_content)
        
        # Use LLM to determine intent
        intent = self._detect_intent(file_content, format_type)
        
        return {
            "format": format_type,
            "intent": intent
        }
    
    def _detect_format(self, file_name, content):
        """Detect the format of the document"""
        if file_name.endswith('.json'):
            return "JSON"
        elif file_name.endswith('.pdf'):
            return "PDF"
        elif file_name.endswith('.txt') or self._looks_like_email(content):
            return "Email"
        else:
            # Default to text if can't determine
            return "Text"
    
    def _looks_like_email(self, content):
        """Check if content looks like an email"""
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
            
        # Simple check for email format (From, Subject, etc.)
        email_patterns = [r'From:\s', r'Subject:\s', r'Date:\s']
        return any(re.search(pattern, content) for pattern in email_patterns)
    
    def _detect_intent(self, content, format_type):
        """Use LLM to detect document intent"""
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
            
        prompt = f"""
        Analyze the following document and determine its intent. 
        Possible intents include: Invoice, RFQ (Request for Quote), Complaint, Regulation, etc.
        
        Document content (format: {format_type}):
        {content[:1500]}  # Limit content length
        
        Return only the intent as a single word or short phrase.
        """
        
        response = self.model.generate_content(prompt)
        intent = response.text.strip()
        
        # Normalize common intents
        intent_mapping = {
            "request for quote": "RFQ",
            "request for quotation": "RFQ",
            "rfq": "RFQ",
            "invoice": "Invoice",
            "complaint": "Complaint",
            "regulation": "Regulation"
        }
        
        return intent_mapping.get(intent.lower(), intent)


class JSONAgent:
    def __init__(self, model):
        self.model = model
        
    def process_json(self, json_content):
        """Process JSON document and extract relevant fields"""
        try:
            # Parse JSON content
            if isinstance(json_content, bytes):
                json_content = json_content.decode('utf-8')
                
            data = json.loads(json_content)
            
            # Extract fields based on document type
            if data.get("document_type") == "Request for Quote":
                return self._process_rfq(data)
            else:
                # Generic JSON processing
                return self._process_generic_json(data)
                
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "Invalid JSON format"
            }
    
    def _process_rfq(self, data):
        """Process Request for Quote JSON"""
        # Extract required fields
        fields = {
            "product": data.get("product"),
            "quantity": data.get("quantity"),
            "deadline": data.get("deadline")
        }
        
        # Check for missing fields
        anomalies = []
        if "budget_range" not in data:
            anomalies.append("Missing: budget_range")
            
        return {
            "status": "processed",
            "intent": "RFQ",
            "fields": fields,
            "anomalies": anomalies
        }
    
    def _process_generic_json(self, data):
        """Process generic JSON document"""
        # Use LLM to extract relevant fields
        prompt = f"""
        Extract the most important fields from this JSON document:
        {json.dumps(data, indent=2)}
        
        Return a JSON object with:
        1. The key fields and their values
        2. Any anomalies or missing fields that would be expected
        """
        
        response = self.model.generate_content(prompt)
        
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return {
                "status": "processed",
                "fields": data,
                "anomalies": ["Unable to determine expected fields"]
            }


class EmailAgent:
    def __init__(self, model):
        self.model = model
        
    def process_email(self, email_content):
        """Process email content and extract metadata"""
        if isinstance(email_content, bytes):
            email_content = email_content.decode('utf-8', errors='ignore')
            
        # Extract basic email metadata
        sender = self._extract_sender(email_content)
        urgency = self._determine_urgency(email_content)
        entities = self._extract_entities(email_content)
        
        return {
            "sender": sender,
            "urgency": urgency,
            "entities": entities
        }
    
    def _extract_sender(self, content):
        """Extract sender from email content"""
        sender_match = re.search(r'From:\s*([^\n]+)', content)
        if sender_match:
            return sender_match.group(1).strip()
        return "Unknown"
    
    def _determine_urgency(self, content):
        """Determine urgency level from email content"""
        # Check for urgency keywords in subject and body
        urgency_keywords = {
            "HIGH": ["urgent", "critical", "immediate", "asap", "emergency"],
            "MEDIUM": ["important", "attention", "priority", "needed"],
            "LOW": ["fyi", "update", "information"]
        }
        
        content_lower = content.lower()
        
        # Check for explicit urgency indicators
        for level, keywords in urgency_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return level
                
        # Default to MEDIUM if no indicators found
        return "MEDIUM"
    
    def _extract_entities(self, content):
        """Extract key entities from email content using LLM"""
        prompt = f"""
        Extract key entities from this email in a structured format:
        {content}
        
        Analyze the content carefully and extract ALL of the following that apply:
        - sender_name: The name of the person sending the email
        - sender_company: The company the sender represents
        - product_name: Any products mentioned
        - quantity: Any quantities mentioned (as numbers)
        - issue_description: Description of any problems or issues
        - deadline: Any mentioned deadlines or dates
        - urgency_indicators: Words indicating urgency (like 'urgent', 'asap', etc.)
        - requested_action: What action is being requested
        
        Return ONLY a valid JSON object with these fields. If a field is not applicable, use null or omit it.
        """
        
        # Make multiple attempts to get valid JSON
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = self.model.generate_content(prompt)
                # Try to extract JSON from the response
                text = response.text.strip()
                # Handle potential markdown code blocks
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                entities = json.loads(text)
                return entities
            except json.JSONDecodeError:
                # If we're on the last attempt, return a fallback
                if attempt == max_attempts - 1:
                    # Create a simple structured response as fallback
                    return self._create_fallback_entities(content)
                # Otherwise try again with a more explicit prompt
                prompt += "\n\nIMPORTANT: Return ONLY a valid JSON object with no additional text."
        
        # This should never be reached due to the fallback, but just in case
        return {"error": "Could not extract structured entities"}
    
    def _create_fallback_entities(self, content):
        """Create a fallback structured response when LLM fails to return valid JSON"""
        # Extract basic information using regex patterns
        entities = {}
        
        # Try to find sender
        sender_match = re.search(r'From:\s*([^\n]+)', content)
        if sender_match:
            entities["sender"] = sender_match.group(1).strip()
        
        # Try to find subject
        subject_match = re.search(r'Subject:\s*([^\n]+)', content)
        if subject_match:
            entities["subject"] = subject_match.group(1).strip()
            
        # Try to find any numbers that might be quantities
        quantity_matches = re.findall(r'\b(\d+)\s*(units|pieces|items)\b', content, re.IGNORECASE)
        if quantity_matches:
            entities["quantities"] = [f"{num} {unit}" for num, unit in quantity_matches]
        
        # Try to find dates
        date_matches = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', content)
        if date_matches:
            entities["dates"] = date_matches
        
        # Add the first 100 chars of content as a summary
        entities["content_preview"] = content[:100] + "..." if len(content) > 100 else content
        
        return entities


class PDFAgent:
    def __init__(self, model):
        self.model = model
        
    def process_pdf(self, pdf_content):
        """Process PDF content and extract information"""
        # Convert PDF to text
        text_content = self._pdf_to_text(pdf_content)
        
        # Extract information using LLM
        sender = self._extract_sender(text_content)
        urgency = "MEDIUM"  # Default urgency for invoices/documents
        entities = self._extract_entities(text_content)
        
        return {
            "sender": sender,
            "urgency": urgency,
            "entities": entities
        }
    
    def _pdf_to_text(self, pdf_content):
        """Convert PDF content to text"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
                
            return text
        except Exception as e:
            return f"Error extracting PDF text: {str(e)}"
    
    def _extract_sender(self, text_content):
        """Extract sender information from PDF text"""
        # Look for vendor or sender information
        vendor_match = re.search(r'Vendor:\s*([^\n]+)', text_content)
        if vendor_match:
            return vendor_match.group(1).strip()
            
        # Try other common patterns
        from_match = re.search(r'From:\s*([^\n]+)', text_content)
        if from_match:
            return from_match.group(1).strip()
            
        return "Unknown"
    
    def _extract_entities(self, text_content):
        """Extract key entities from PDF text using LLM"""
        prompt = f"""
        Extract key information from this document text in a structured format:
        {text_content[:2000]}  # Increased content length for better context
        
        Analyze the content carefully and extract ALL of the following that apply:
        - invoice_number: Any invoice or reference numbers
        - vendor_name: The company issuing the document
        - client_name: The company receiving the document
        - total_amount: The total monetary amount (as a number without currency symbols)
        - line_items: Array of items with quantities and prices
        - payment_terms: Payment terms if mentioned
        - issue_date: When the document was issued
        - due_date: When payment or action is due
        
        Return ONLY a valid JSON object with these fields. If a field is not applicable, use null or omit it.
        """
        
        # Make multiple attempts to get valid JSON
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = self.model.generate_content(prompt)
                # Try to extract JSON from the response
                text = response.text.strip()
                # Handle potential markdown code blocks
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                entities = json.loads(text)
                return entities
            except json.JSONDecodeError:
                # If we're on the last attempt, return a fallback
                if attempt == max_attempts - 1:
                    return self._create_fallback_entities(text_content)
                # Otherwise try again with a more explicit prompt
                prompt += "\n\nIMPORTANT: Return ONLY a valid JSON object with no additional text."
        
        return {"error": "Could not extract structured entities"}
        
    def _create_fallback_entities(self, text_content):
        """Create a fallback structured response when LLM fails to return valid JSON"""
        entities = {}
        
        # Try to find invoice number
        invoice_match = re.search(r'Invoice\s*#?\s*([\w\-]+)', text_content)
        if invoice_match:
            entities["invoice_number"] = invoice_match.group(1).strip()
        
        # Try to find vendor
        vendor_match = re.search(r'Vendor:\s*([^\n]+)', text_content)
        if vendor_match:
            entities["vendor"] = vendor_match.group(1).strip()
        
        # Try to find total amount
        total_match = re.search(r'Total\s*(?:Due|Amount)?:\s*\$?(\d[\d,.]*)', text_content)
        if total_match:
            entities["total_amount"] = total_match.group(1).strip()
        
        # Add the first 100 chars of content as a summary
        entities["content_preview"] = text_content[:100] + "..." if len(text_content) > 100 else text_content
        
        return entities