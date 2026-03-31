# ⚖️ LegalEase AI  
### Smart Case File Management & Insights for Advocates

---

## 📌 Overview

LegalEase AI is an AI-powered legal assistant designed to help advocates efficiently manage and analyze case files. The system enables users to upload legal documents, extract key insights, generate summaries, and interact with case data using a conversational chatbot.

The platform leverages modern Artificial Intelligence techniques such as Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and vector databases to transform static legal documents into dynamic, interactive knowledge systems.

---

## 🚀 Features

LegalEase AI provides a comprehensive set of features designed to simplify legal workflows and enhance productivity for advocates.

### 📄 Smart Document Upload & Processing
Users can upload legal case files in PDF format, including both text-based and scanned documents. The system uses advanced document parsing techniques (via PyMuPDF) to extract and structure textual content. It then intelligently segments the document into smaller chunks for efficient processing and analysis.

---

### 🤖 AI-Powered Legal Chatbot
The platform includes an interactive chatbot that allows users to ask questions about their case files in natural language. Instead of manually searching through documents, users can simply type queries such as:
- “What is the summary of this case?”
- “What are the key legal arguments?”

The chatbot uses Retrieval-Augmented Generation (RAG) to provide accurate, context-aware answers based on the uploaded documents.

---

### 📊 Automatic Case Summarization
LegalEase AI automatically generates concise summaries of uploaded case files. These summaries highlight the most important aspects of the case, enabling advocates to quickly understand the core details without reading the entire document.

---

### 🔍 Intelligent Semantic Search
Unlike traditional keyword search, the system performs semantic search using vector embeddings. This allows users to find relevant information even if the exact words are not present in the query. The search is based on meaning and context rather than exact matches.

---

### 🔎 Cross-Case Search
Users can perform queries across multiple case files simultaneously. This feature is particularly useful for identifying patterns, comparing legal arguments, or retrieving information from previously uploaded cases.

---

### 🌐 Multilingual Support (22 Indian Languages)
The system supports voice and text queries in multiple Indian languages. Queries are automatically translated and processed, making the platform accessible to a wider audience and reducing language barriers in legal workflows.

---

### 🎤 Voice-Based Interaction
Users can interact with the system using voice input. Speech is converted into text using AI-based speech recognition, enabling hands-free interaction and improving accessibility.

---

### 📥 Export Chat History as PDF
Users can export their chat conversations with the AI as a PDF document. This is useful for:
- Documentation  
- Case preparation  
- Sharing insights with clients or colleagues  

---

### 🔥 Most Asked Questions Tracking
The system tracks frequently asked questions for each case. This helps users quickly revisit common queries and identify key areas of interest within a case.

---

### 📈 Analytics Dashboard
LegalEase AI provides a dashboard that visualizes:
- Case processing statistics  
- Document usage  
- Query trends  
- System performance metrics  

This enables users to gain insights into their workflow and optimize their usage of the platform.

---

### ⚡ Fast and Scalable Performance
The system is built using modern technologies such as FastAPI and vector databases, ensuring low latency and efficient handling of large documents. Even complex queries across multiple documents are processed quickly. 

---

## 🏗️ System Architecture

LegalEase AI follows a multi-layered architecture that separates concerns between user interaction, data processing, storage, and AI reasoning. This design ensures scalability, maintainability, and efficient performance.

---

### 🔷 Architecture Diagram

```
            ┌──────────────────────────────┐
            │         USER LAYER           │
            │  Lawyers / Clients / Admin   │
            └─────────────┬────────────────┘
                          │
                          ▼
            ┌──────────────────────────────┐
            │          UI LAYER            │
            │  Chat UI • Upload • Dashboard│
            └─────────────┬────────────────┘
                          │
                          ▼
            ┌──────────────────────────────┐
            │        API GATEWAY           │
            │ Auth • Routing • Validation  │
            └─────────────┬────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                                   ▼
┌──────────────────────┐          ┌────────────────────────┐
│ DOCUMENT PROCESSING  │          │   AI INTELLIGENCE      │
│ PDF Parsing (PyMuPDF)│          │ LLM (Gemini Flash)     │
│ Text Extraction      │          │ Query Processing       │
└─────────────┬────────┘          │ Reasoning Engine       │
              │                   └─────────────┬──────────┘
              ▼                                 │
┌──────────────────────────────┐                │
│      VECTOR DATABASE         │◄───────────────┘
│  (Supabase + pgvector)       │
│  Embeddings + Metadata       │
└─────────────┬────────────────┘
              │
              ▼
┌──────────────────────────────┐
│     DELIVERY LAYER           │
│ Chat Response • Insights     │
│ Dashboard Output             │
└──────────────────────────────┘
```

---

### 🔍 Architecture Explanation

The system is divided into multiple layers, each responsible for a specific part of the workflow.

#### **1. User Layer**
This layer consists of end users such as advocates, administrators, and clients. Users interact with the system by uploading documents, asking queries, and viewing insights.

---

#### **2. UI Layer**
The frontend is built using React and Next.js, providing an interactive interface for document upload, chat interaction, and analytics visualization. This layer handles all user interactions and communicates with backend APIs.

---

#### **3. API Gateway**
The gateway layer acts as the central entry point for all requests. It manages authentication, request validation, and routing to appropriate backend services. It also ensures secure communication between frontend and backend components.

---

#### **4. Document Processing Layer**
This layer processes uploaded legal documents using PyMuPDF. It extracts textual content from PDFs, including scanned documents, and prepares the data for further analysis by splitting it into manageable chunks.

---

#### **5. Vector Database Layer**
The processed text is converted into embeddings and stored in a vector database (pgvector with Supabase PostgreSQL). This enables semantic search by comparing the similarity between user queries and stored document chunks.

---

#### **6. AI Intelligence Layer**
This is the core of the system, where the Large Language Model (Gemini 2.5 Flash) operates. It performs:
- Query understanding  
- Context retrieval (RAG)  
- Response generation  

By combining retrieved document context with the user query, the model generates accurate and context-aware answers.

---

#### **7. Delivery Layer**
The final output is delivered to the user through the chat interface and dashboard. This includes summaries, insights, and answers to queries.

---

### ⚙️ Key Architectural Advantages

- **Scalability**: Modular layers allow independent scaling  
- **Accuracy**: RAG ensures responses are grounded in real data  
- **Performance**: Vector search enables fast retrieval  
- **Security**: API gateway enforces authentication and validation  

---

## 🧠 How It Works

1. User uploads a case file (PDF)  
2. Document is parsed using PyMuPDF  
3. Text is split into smaller chunks  
4. Each chunk is converted into embeddings  
5. Embeddings are stored in a vector database (pgvector)  
6. User submits a query  
7. Relevant chunks are retrieved using similarity search  
8. Retrieved context is passed to the LLM (RAG pipeline)  
9. LLM generates an accurate, context-aware response  

---

## 🏗️ Architecture

The system follows a layered architecture:

- **Frontend**: React, Next.js, Tailwind CSS, Shadcn UI  
- **Backend**: Python, FastAPI  
- **AI Model**: Gemini 2.5 Flash  
- **Embeddings**: Gemini embedding-001  
- **Database**: Supabase PostgreSQL with pgvector  
- **Storage**: Supabase Storage  
- **Voice Processing**: Gemini Multimodal Audio  

---

## 📥 Inputs

- Case file PDFs (structured and scanned)  
- Voice queries (22 Indian languages)  
- Text-based legal questions  

---

## 📤 Outputs

- Case summaries  
- Key legal insights  
- Important highlights  
- Intelligent search results  
- AI-generated answers to queries  

---

## 🔍 Core Technologies

### 🔹 Retrieval-Augmented Generation (RAG)
Enhances LLM responses by retrieving relevant document chunks and injecting them into the model context for accurate answers.

### 🔹 Vector Embeddings
Converts text into numerical representations for semantic similarity search.

### 🔹 Natural Language Processing (NLP)
Used for summarization, translation, and query understanding.

---

## 🔐 Security

- Supabase Authentication (email/password + OAuth)  
- Role-based access control  
- Secure session management  
- Encrypted data storage  

---

## ⚙️ Installation

```bash
git clone https://github.com/chins6/legalease-ai.git
cd legalease-ai
npm install
npm run dev
```

---

## 🌍 Deployment

The application can be deployed using Vercel for frontend hosting and Supabase for backend services.

---

## 👥 Team

- Aditya H Shah  
- Devananda A  
- Gunin Sharma  
- Chinmayi Suresh  
- Madhava B S  
- Mridul Vinaik  

---

## 📌 Future Scope

- Legal case outcome prediction  
- Advanced analytics dashboard  
- Integration with court databases  
- Offline processing capabilities  

---

## 📜 License

This project is developed for academic purposes.
