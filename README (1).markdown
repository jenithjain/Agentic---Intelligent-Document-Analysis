# Agentic - Intelligent Document Processing System

## Overview
Agentic intelligent Document Processing System is a sophisticated document processing system that leverages AI to intelligently classify, analyze, and extract information from various document types including emails, PDFs, JSON files, and plain text. The system uses Google's Generative AI (Gemini) for advanced text analysis and maintains document history using Redis for efficient data persistence.

## Features
- **Multi-format Document Support**
  - JSON (RFQ, Generic)
  - Emails
  - PDF Documents
  - Plain Text
- **Intelligent Classification**
  - Automatic format detection
  - Intent analysis (RFQ, Invoice, Complaint, Regulation)
  - Content-based classification fallback
- **Advanced Entity Extraction**
  - Sender information
  - Urgency assessment
  - Key entities (products, quantities, deadlines)
  - Document-specific metadata
- **Persistent Storage**
  - Redis-based document storage
  - Structured data persistence
  - Historical document tracking
  - Efficient retrieval system

## Architecture
### Core Components
1. **Classifier Agent** (`agents.py`)
   - Document format detection
   - Intent classification
   - AI-powered content analysis
2. **Specialized Agents**
   - **JSON Agent**: Processes RFQs and generic JSON documents
   - **Email Agent**: Extracts metadata, urgency, and entities from emails
   - **PDF Agent**: Converts and analyzes PDF documents
3. **Memory System** (`memory.py`)
   - Redis integration for data persistence
   - Document data storage and retrieval
   - Historical tracking capabilities

## Technical Implementation
### Document Processing Pipeline
1. **Format Detection**
   - File extension analysis
   - Content-based format verification
   - Fallback mechanisms
2. **Intent Classification**
   - AI-powered intent analysis
   - Pattern matching
   - Context understanding
3. **Entity Extraction**
   - LLM-based entity recognition
   - Regex fallback mechanisms
   - Structured data extraction

### Data Storage
- Document metadata storage
- JSON serialization for complex data
- Timestamp tracking
- Efficient retrieval mechanisms

## Sample Inputs
Agentic can process various document formats and extract relevant information based on the document type. Below are examples of supported documents:

### Invoice (Plain Text)
**Input:**
```
Invoice #INV-2024-789
Vendor: Tech Solutions Ltd.
Client: Data Systems Inc.
Date: 2024-05-30
Items:
- AI Server Rack: 10 units @ $12,500
- Cooling System: 10 units @ $3,200
Total Due: $157,000
Payment Terms: Net 30
```
**Processing:**
The system classifies this as an invoice and extracts key entities such as invoice number, vendor, client, total amount, and payment terms.

### Request for Quote (JSON)
**Input:**
```json
{
  "document_type": "Request for Quote",
  "product": "AI Server Cluster",
  "quantity": 25,
  "deadline": "2024-06-15",
  "contact_email": "procurement@techcorp.com"
}
```
**Processing:**
Identified as an RFQ document, the system extracts the product, quantity, deadline, and contact information.

### Regulation Update (Plain Text)
**Input:**
```
Subject: New Regulatory Compliance Update - GDPR Extension 2025
The European Commission has issued a new amendment to GDPR applicable from July 1, 2025. Companies must now:
- Log all cross-border data transfers explicitly
- Provide AI usage explanations to end users
- Maintain zero-retention policy on biometric data
Failure to comply will result in penalties up to €20 million or 4% of global turnover.
Refer to: Regulation (EU) 2025/1011
```
**Processing:**
Classified as a regulation document, the system analyzes the content to identify key compliance requirements and relevant dates.

## Dependencies
- Google Generative AI (Gemini)
- Redis
- PyPDF2
- JSON processing libraries

## Future Enhancements
1. Additional document format support
2. Enhanced entity extraction capabilities
3. Advanced analytics and reporting
4. Machine learning model fine-tuning
5. Scalability improvements

## License
This project is proprietary and confidential.

## Contact
For any queries or support, please reach out to the development team.

**Note:** This README provides an overview of the Agentic system. For detailed implementation and deployment instructions, please refer to the internal documentation.